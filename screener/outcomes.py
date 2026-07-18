"""Fixed-horizon outcome scoring per METHODOLOGY.md §5 (corporate actions)
and §6 (success metric).

    python -m screener.outcomes runs/2025-06-13-test
    python -m screener.outcomes runs/2025-06-13-test --horizon 12

For every name in the run folder's public_screen.csv, computes forward total
returns (dividend-adjusted) at the two config horizons, benchmark excess vs
the pinned IJR series over the same windows, and the four pre-registered
statistics over the picks. No managed exits — every pick is scored at the
horizon regardless of interim developments.

Corporate actions cannot be auto-classified from free price data (a series
that stops could be a takeover or a fraud halt), so classification is a
disclosed input: an optional corporate_actions.csv in the run folder with
columns  ticker, action, effective_date[, value_per_share]  where action is
one of  acquisition | delist_for_cause | spinoff | halt.  The §5 rules:
  acquisition       value at deal close, then rolled forward at the
                    benchmark return to the horizon
  delist_for_cause  final observable value; −100% if no observable exit
  spinoff           combined-entity value as-if-held (dividend-adjusted
                    parent series approximates this; a value_per_share
                    override wins if provided)
  halt              last trade, stale-flagged in return_basis
A series that ends early with no classification gets return_basis
early_end_unclassified and a loud warning — it must be classified by hand.

Outputs (append-only schema; new files, no existing column redefined):
  outcomes_6m.csv, outcomes_12m.csv, outcomes_summary.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import statistics

import pandas as pd

from .config import ROOT, load_backends, load_v0, num
from .gitinfo import config_version

# calendar tolerance: a series is "ended early" if its last observation sits
# more than this many days before the horizon date (covers holiday gaps)
EARLY_END_GRACE_DAYS = 14

ACTION_BASIS = {
    "acquisition": "acquisition_rolled_at_benchmark",
    "delist_for_cause": "delist_final_value",
    "spinoff": "spinoff_combined_as_held",
    "halt": "halt_last_trade_stale",
}


def add_months(d: dt.date, months: int) -> dt.date:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
                      else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return dt.date(year, month, day)


class TiingoSeries:
    """Adjusted-close series provider backed by Tiingo (cached)."""

    def __init__(self):
        from .backends.free.http import CachedSession
        from .config import load_backends
        cfg = load_backends()
        self.session = CachedSession(cfg.get("cache", {}),
                                     user_agent="smallcap-record/0.1")
        self.url = cfg["free"]["tiingo"]["prices_url"]
        import os
        self.token = os.environ.get("TIINGO_API_KEY")
        if not self.token:
            raise RuntimeError("TIINGO_API_KEY missing from .env")

    def series(self, ticker: str, start: dt.date, end: dt.date
               ) -> list[tuple[dt.date, float]]:
        rows = self.session.get_json(
            self.url.format(ticker=ticker.lower()),
            params={"startDate": start.isoformat(), "endDate": end.isoformat(),
                    "token": self.token, "format": "json"})
        if not isinstance(rows, list):
            return []
        return [(dt.date.fromisoformat(r["date"][:10]), float(r["adjClose"]))
                for r in rows]


def last_at_or_before(series: list[tuple[dt.date, float]], target: dt.date
                      ) -> tuple[dt.date, float] | tuple[None, None]:
    best = (None, None)
    for date, value in series:
        if date <= target:
            best = (date, value)
    return best


def score_name(ticker: str, run_date: dt.date, horizon_end: dt.date,
               stock_series, bench_series, action_row: dict | None
               ) -> dict:
    """One name, one horizon. Returns ret, bench_ret, excess, return_basis."""
    out = {"ret": None, "bench_ret": None, "excess": None, "return_basis": None}

    b0_date, b0 = last_at_or_before(bench_series, run_date)
    bh_date, bh = last_at_or_before(bench_series, horizon_end)
    if b0 and bh:
        out["bench_ret"] = bh / b0 - 1.0

    p0_date, p0 = last_at_or_before(stock_series, run_date)
    if p0 is None:
        out["return_basis"] = "no_start_price"
        return out
    last_date, last_px = stock_series[-1] if stock_series else (None, None)

    action = (action_row or {}).get("action")
    if action == "delist_for_cause":
        # §5: final observable value; if no observable exit exists, −100%
        _, exit_px = last_at_or_before(stock_series, horizon_end)
        if exit_px is None or last_date == p0_date:
            out["ret"] = -1.0
            out["return_basis"] = "delist_no_exit_minus_100"
        else:
            out["ret"] = exit_px / p0 - 1.0
            out["return_basis"] = ACTION_BASIS["delist_for_cause"]
    elif action == "acquisition":
        # §5: value at deal close, proceeds rolled at the benchmark return
        close_date = action_row["effective_date"]
        if action_row.get("value_per_share"):
            deal_value = float(action_row["value_per_share"])
        else:
            _, deal_value = last_at_or_before(stock_series, close_date)
        if deal_value is None:
            out["return_basis"] = "acquisition_missing_value"
            return out
        bc_date, bc = last_at_or_before(bench_series, close_date)
        _, bh2 = last_at_or_before(bench_series, horizon_end)
        roll = (bh2 / bc) if (bc and bh2) else 1.0
        out["ret"] = (deal_value * roll) / p0 - 1.0
        out["return_basis"] = ACTION_BASIS["acquisition"]
    elif action in ("spinoff", "halt"):
        override = action_row.get("value_per_share")
        _, px = last_at_or_before(stock_series, horizon_end)
        value = float(override) if override else px
        if value is None:
            out["return_basis"] = f"{action}_missing_value"
            return out
        out["ret"] = value / p0 - 1.0
        out["return_basis"] = ACTION_BASIS[action]
    else:
        ph_date, ph = last_at_or_before(stock_series, horizon_end)
        if ph is None:
            out["return_basis"] = "no_horizon_price"
            return out
        out["ret"] = ph / p0 - 1.0
        if ph_date and (horizon_end - ph_date).days > EARLY_END_GRACE_DAYS:
            # series stopped and nobody classified why — do not guess
            out["return_basis"] = "early_end_unclassified"
            print(f"  [WARN] {ticker}: price series ends {ph_date}, "
                  f"{(horizon_end - ph_date).days} days before horizon "
                  f"{horizon_end} — classify in corporate_actions.csv")
        else:
            out["return_basis"] = "regular"

    if out["ret"] is not None and out["bench_ret"] is not None:
        out["excess"] = out["ret"] - out["bench_ret"]
    return out


def preregistered_stats(excess: list[float], stats_wanted: list[str],
                        include_hit_rate: bool) -> dict:
    """The four §6 statistics — all report together, no cherry-picking."""
    out = {"n_picks_scored": len(excess)}
    wins = [e for e in excess if e > 0]
    losses = [e for e in excess if e < 0]
    for name in stats_wanted:
        if name == "hit_rate":
            # hit is defined as excess_12m > 0; at 6m it is not a "hit"
            if include_hit_rate:
                out["hit_rate"] = len(wins) / len(excess) if excess else None
        elif name == "slugging":
            out["slugging"] = (
                (sum(wins) / len(wins)) / abs(sum(losses) / len(losses))
                if wins and losses else None)
        elif name == "mean_excess":
            out["mean_excess"] = sum(excess) / len(excess) if excess else None
        elif name == "median_excess":
            out["median_excess"] = statistics.median(excess) if excess else None
    return out


def load_actions(run_dir: pathlib.Path) -> dict[str, dict]:
    path = run_dir / "corporate_actions.csv"
    if not path.exists():
        return {}
    actions = {}
    for _, row in pd.read_csv(path).iterrows():
        rec = row.to_dict()
        if rec["action"] not in ACTION_BASIS:
            raise ValueError(f"unknown corporate action {rec['action']!r} "
                             f"(expected one of {sorted(ACTION_BASIS)})")
        rec["effective_date"] = dt.date.fromisoformat(str(rec["effective_date"]))
        actions[str(rec["ticker"]).upper()] = rec
    return actions


def compute_outcomes(run_dir: pathlib.Path, horizons: list[int],
                     provider=None) -> dict:
    cfg = load_v0()
    m = cfg["success_metric"]
    bench_ticker = cfg["data"]["benchmark_series"]["ticker"]
    hit_def = m["hit_definition"]
    assert hit_def == "excess_12m_gt_0", f"unexpected hit definition {hit_def!r}"
    primary = int(num(m["horizon_primary_months"]))

    public = pd.read_csv(run_dir / "public_screen.csv")
    run_date = dt.date.fromisoformat(public["run_date"].iloc[0])
    actions = load_actions(run_dir)
    provider = provider or TiingoSeries()
    version = config_version()

    max_end = add_months(run_date, max(horizons))
    fetch_start = run_date - dt.timedelta(days=10)
    bench_series = provider.series(bench_ticker, fetch_start, max_end)
    if not bench_series:
        raise RuntimeError(f"no benchmark ({bench_ticker}) prices — cannot score")

    summary = {"run_date": run_date.isoformat(), "scored_on": dt.date.today().isoformat(),
               "outcome_config_version": version, "horizons": {}}
    for horizon in horizons:
        horizon_end = add_months(run_date, horizon)
        if horizon_end > dt.date.today():
            print(f"  [skip] {horizon}m horizon ends {horizon_end}, in the future")
            continue
        rows = []
        for _, name in public.iterrows():
            ticker = name["ticker"]
            stock_series = provider.series(ticker, fetch_start, horizon_end)
            scored = score_name(ticker, run_date, horizon_end, stock_series,
                                bench_series, actions.get(ticker))
            row = {
                "figi": name["figi"], "run_date": name["run_date"],
                "cik": name["cik"], "ticker": ticker, "sector": name["sector"],
                "pick": name["pick"], "pick_rank": name.get("pick_rank"),
                "horizon_months": horizon,
                "horizon_end_date": horizon_end.isoformat(),
                f"ret_{horizon}m": scored["ret"],
                f"bench_ret_{horizon}m": scored["bench_ret"],
                f"excess_{horizon}m": scored["excess"],
                "return_basis": scored["return_basis"],
                "outcome_config_version": version,
            }
            if horizon == primary:
                row[f"hit_{horizon}m"] = (
                    scored["excess"] > 0 if scored["excess"] is not None else None)
            rows.append(row)
        frame = pd.DataFrame(rows)
        out_path = run_dir / f"outcomes_{horizon}m.csv"
        frame.to_csv(out_path, index=False)

        pick_excess = [r[f"excess_{horizon}m"] for r in rows
                       if r["pick"] and r[f"excess_{horizon}m"] is not None]
        summary["horizons"][f"{horizon}m"] = preregistered_stats(
            pick_excess, m["preregistered_stats"],
            include_hit_rate=(horizon == primary))
        print(f"wrote {out_path.name}: {len(frame)} names, "
              f"{len(pick_excess)} picks scored")

    (run_dir / "outcomes_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="fixed-horizon outcome scoring")
    parser.add_argument("run_folder", help="e.g. runs/2025-06-13-test")
    parser.add_argument("--horizon", choices=["6", "12", "both"], default="both")
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")

    cfg = load_v0()["success_metric"]
    all_h = [int(num(cfg["horizon_recorded_months"])),
             int(num(cfg["horizon_primary_months"]))]
    horizons = all_h if args.horizon == "both" else [int(args.horizon)]

    run_dir = ROOT / args.run_folder
    if not (run_dir / "public_screen.csv").exists():
        raise SystemExit(f"no public_screen.csv in {run_dir}")
    summary = compute_outcomes(run_dir, horizons)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
