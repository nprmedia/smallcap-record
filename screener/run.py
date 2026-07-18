"""Run the v0 screener end-to-end.

    python -m screener.run --backend free
    python -m screener.run --backend free --as-of 2026-07-12
    python -m screener.run --backend sharadar          # from August

Every methodology parameter comes from config/v0.yaml. Off-cadence dates are
allowed for testing and are labeled run_kind=test; only the four §7 cadence
dates (next-business-day rolled) produce run_kind=official. Test runs write
to a -test suffixed folder (see README fence).

run_day.py at the repo root wraps execute() with stamping, staging, and a
confirm-before-commit gate for official run days.
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


def execute(backend_name: str, as_of: dt.date, force_test: bool = False):
    """Full pipeline: fetch -> universe -> gates -> ranks -> observation ->
    picks -> artifacts on disk. Returns (full_frame, meta, paths)."""
    load_dotenv(ROOT / ".env")
    v0 = load_v0()
    backends_cfg = load_backends()
    version = config_version()
    kind = "test" if force_test else run_kind_for(as_of, v0)

    print(f"run {as_of} | backend={backend_name} | config_version={version} | {kind}")

    backend = get_backend(backend_name, v0, backends_cfg)
    raw = backend.fetch(as_of)
    print(f"candidates fetched: {len(raw)}")

    universe, exclusion_log = build_universe(raw, v0)
    print(f"universe after filters: {len(universe)} (excluded {len(exclusion_log)})")

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
        "backend_disclosures": getattr(backend, "disclosures", []),
        **getattr(backend, "extra_meta", {}),
    }
    paths = write_run(full, exclusion_log, as_of, meta)
    return full, meta, paths


def print_summary(full, meta: dict, paths: dict) -> None:
    picks = full[full["pick"] == True]  # noqa: E712
    print(f"\ngate passers: {meta['counts']['gate_passers']} | picks: {len(picks)}"
          + (" (SHORTFALL — fewer passers than pick target)"
             if meta["pick_shortfall"] else ""))
    for _, p in picks.sort_values("pick_rank").iterrows():
        print(f"  #{int(p['pick_rank'])} {p['ticker']:6s} {p['sector']:25s} "
              f"composite={p['composite']:.3f}")
    print(f"\nwrote:\n  {paths['full']}  (LOCAL ONLY)\n  {paths['log']}  (LOCAL ONLY)"
          f"\n  {paths['public']}\n  {paths['meta']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="smallcap-record v0 screener")
    parser.add_argument("--backend", choices=["free", "sharadar"], required=True)
    parser.add_argument("--as-of", type=dt.date.fromisoformat,
                        default=dt.date.today())
    args = parser.parse_args()
    full, meta, paths = execute(args.backend, args.as_of)
    print_summary(full, meta, paths)
    print("next: python scripts/stamp_run.py runs/" + paths["dir"].name)


if __name__ == "__main__":
    main()
