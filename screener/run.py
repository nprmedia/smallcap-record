"""Run the v0 screener end-to-end.

    python -m screener.run --backend free
    python -m screener.run --backend free --as-of 2026-07-12
    python -m screener.run --backend sharadar          # from August

Every methodology parameter comes from config/v0.yaml. Off-cadence dates are
allowed for testing and are labeled run_kind=test; only the four §7 cadence
dates (next-business-day rolled) produce run_kind=official.
"""
from __future__ import annotations

import argparse
import datetime as dt

from dotenv import load_dotenv

from .backends import get_backend
from .config import ROOT, load_backends, load_v0
from .gitinfo import config_version
from .pipeline.gates import apply_gates
from .pipeline.observation import apply_observation
from .pipeline.output import finalize_frame, write_run
from .pipeline.picks import apply_picks
from .pipeline.ranks import apply_ranks, compute_factor_raws
from .pipeline.universe import build_universe

FREE_BACKEND_DISCLOSURES = [
    "short interest, call tone, and hiring velocity have no free source -> null",
    "GICS sectors hand-assigned in config/backends.yaml (no free GICS license)",
    "announced_target is an EDGAR merger-proxy/tender-form heuristic, not a deal feed",
    "months_since_listing proxied from earliest EDGAR filing date",
    "total debt = sum of reported XBRL debt tags (filer tag variance possible)",
]


def roll_to_business_day(d: dt.date) -> dt.date:
    while d.weekday() >= 5:   # Sat/Sun -> next Monday; holidays not modeled
        d += dt.timedelta(days=1)
    return d


def run_kind_for(as_of: dt.date, cfg: dict) -> str:
    for mmdd in cfg["cadence"]["run_dates"]:
        month, day = (int(x) for x in str(mmdd).split("-"))
        if as_of == roll_to_business_day(dt.date(as_of.year, month, day)):
            return "official"
    return "test"


def main() -> None:
    parser = argparse.ArgumentParser(description="smallcap-record v0 screener")
    parser.add_argument("--backend", choices=["free", "sharadar"], required=True)
    parser.add_argument("--as-of", type=dt.date.fromisoformat,
                        default=dt.date.today())
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    v0 = load_v0()
    backends_cfg = load_backends()
    version = config_version()
    as_of = args.as_of
    kind = run_kind_for(as_of, v0)

    print(f"run {as_of} | backend={args.backend} | config_version={version} | {kind}")

    backend = get_backend(args.backend, v0, backends_cfg)
    raw = backend.fetch(as_of)
    print(f"candidates fetched: {len(raw)}")

    universe, exclusion_log = build_universe(raw, v0)
    print(f"universe after filters: {len(universe)} "
          f"(excluded {len(exclusion_log)})")

    df = apply_gates(universe, v0)
    df = compute_factor_raws(df)
    df = apply_ranks(df, v0)
    df = apply_observation(df, v0)
    df = apply_picks(df, v0)

    benchmark = backend.benchmark_level(as_of)
    df["benchmark_at_run"] = benchmark

    full = finalize_frame(df, as_of, version, backend.name, kind)

    survivors = int(full["gates_all_pass"].sum())
    picks = full[full["pick"] == True]  # noqa: E712
    meta = {
        "run_date": as_of.isoformat(),
        "run_kind": kind,
        "config_version": version,
        "data_backend": backend.name,
        "counts": {
            "candidates": len(raw),
            "universe": len(universe),
            "gate_passers": survivors,
            "composite_null_among_passers": int(
                full[full["gates_all_pass"] & full["composite"].isna()].shape[0]),
            "picks": len(picks),
        },
        "pick_shortfall": bool(full["pick_shortfall"].any()),
        "benchmark_level_ijr_adj": benchmark,
        "figi_placeholders": sorted(
            full.loc[full["figi"].str.startswith("NOFIGI"), "ticker"].tolist()),
        "backend_disclosures": (
            FREE_BACKEND_DISCLOSURES if backend.name == "free" else []),
    }
    paths = write_run(full, exclusion_log, as_of, meta)

    print(f"\ngate passers: {survivors} | picks: {len(picks)}"
          + (" (SHORTFALL — fewer passers than pick target)"
             if meta["pick_shortfall"] else ""))
    for _, p in picks.sort_values("pick_rank").iterrows():
        print(f"  #{int(p['pick_rank'])} {p['ticker']:6s} {p['sector']:25s} "
              f"composite={p['composite']:.3f}")
    print(f"\nwrote:\n  {paths['full']}  (LOCAL ONLY)\n  {paths['log']}  (LOCAL ONLY)"
          f"\n  {paths['public']}\n  {paths['meta']}")
    print("next: python scripts/stamp_run.py runs/" + paths["dir"].name)


if __name__ == "__main__":
    main()
