"""The single command for official run days.

    python run_day.py                # official run, today must be a §7 cadence date
    python run_day.py --test         # identical flow, fenced -test folder, run_kind=test

Sequence: full pipeline for today -> full/public CSVs per repo conventions ->
OTS-stamp every new artifact -> upgrade all prior pending receipts -> stage
ONLY the public artifacts and receipts -> plain-language summary -> stop and
require an explicit 'yes' before committing and pushing.

Guarantees: never deletes anything; never stages full_*.csv (their receipts
are the public proof); refuses to produce an official run on a non-cadence
date; on anything but 'yes', unstages what it staged and leaves every file
on disk untouched.

--as-of is accepted only together with --test (for rehearsals); official
runs always use today's date.
"""
from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from screener.config import ROOT, load_v0
from screener.run import execute, print_summary, run_kind_for
from scripts.stamp_run import OTS_EXE, ots_env, stamp_dir, upgrade_all


def git(*args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True, check=True)
    return proc.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="official run-day command")
    parser.add_argument("--test", action="store_true",
                        help="rehearsal: identical flow, -test folder, run_kind=test")
    parser.add_argument("--as-of", type=dt.date.fromisoformat, default=None,
                        help="rehearsal date (allowed only with --test)")
    parser.add_argument("--backend", choices=["free", "sharadar"], default="free")
    args = parser.parse_args()

    if args.as_of and not args.test:
        sys.exit("--as-of is only allowed with --test; official runs use today")
    as_of = args.as_of or dt.date.today()

    if not args.test and run_kind_for(as_of, load_v0()) != "official":
        sys.exit(f"{as_of} is not a §7 cadence date (Mar/May/Aug/Nov 20, "
                 "business-day rolled). Use --test for a rehearsal.")
    if not OTS_EXE.exists():
        sys.exit(f"ots client not found at {OTS_EXE} — aborting before any work")

    # 1) pipeline + artifacts
    full, meta, paths = execute(args.backend, as_of, force_test=args.test)

    # 2) timestamp: stamp new artifacts, upgrade every prior receipt
    print("\nstamping artifacts and upgrading prior receipts ...")
    env = ots_env()
    stamp_dir(paths["dir"], env)
    upgrade_all(env)

    # 3) stage ONLY public artifacts and receipts (full_*.csv never staged;
    #    .gitignore also blocks it as a second line of defense)
    staged = [paths["public"], paths["meta"]]
    staged += sorted(paths["dir"].glob("*.ots"))
    rel = [str(p.relative_to(ROOT)) for p in staged]
    git("add", "--", *rel)
    git("add", "-u", "--", "*.ots")   # previously committed receipts that upgraded
    staged_now = git("diff", "--cached", "--name-only").splitlines()

    # 4) plain-language summary
    print_summary(full, meta, paths)
    counts = meta["counts"]
    kind = meta["run_kind"]
    print(f"\n{'=' * 60}")
    print(f"ABOUT TO COMMIT ({kind} run):")
    print(f"  run date:      {meta['run_date']}")
    print(f"  universe:      {counts['universe']} names "
          f"({counts['candidates']} candidates screened)")
    print(f"  gate passers:  {counts['gate_passers']}")
    print(f"  picks:         {counts['picks']}"
          + ("  ** SHORTFALL disclosed **" if meta["pick_shortfall"] else ""))
    print("  files staged:")
    for f in staged_now:
        print(f"    {f}")
    print("  full_screen.csv / full_universe_log.csv stay local; their OTS "
          "receipts above are the public proof.")
    print("=" * 60)

    # 5) explicit consent gate
    answer = input("\nType yes to commit and push (anything else aborts): ").strip().lower()
    if answer != "yes":
        git("reset", "--", *rel)
        git("reset", "--", "*.ots")
        print("aborted: nothing committed, nothing pushed. All files remain "
              "on disk; re-run when ready.")
        return

    label = "Official" if kind == "official" else "Test"
    git("commit", "-m", f"{label} run {meta['run_date']}: artifacts + receipts")
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    git("push", "origin", branch)
    print(f"committed and pushed to origin/{branch}: "
          f"{git('log', '--oneline', '-1')}")


if __name__ == "__main__":
    main()
