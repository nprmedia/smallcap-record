"""OpenTimestamps helper: stamp a run's artifacts and upgrade all prior receipts.

    python scripts/stamp_run.py runs/2026-07-13-test

Per repo convention (CLAUDE.md / METHODOLOGY.md §10): every run, stamp the
new artifacts and upgrade previous receipts, then commit the .ots files.
run_day.py imports stamp_dir()/upgrade_all() for the same flow.

Windows quirk handled here: python-bitcoinlib looks for an OpenSSL library
literally named ssl.dll, which doesn't exist on this machine, so we copy
libcrypto.dll into a temp dir under that name and prepend it to PATH.
The ots client also lives outside PATH (pip --user install).
"""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
OTS_EXE = pathlib.Path(os.environ["APPDATA"]) / "Python" / "Python313" / "Scripts" / "ots.exe"
LIBCRYPTO = pathlib.Path(r"C:\Windows\System32\libcrypto.dll")


def ots_env() -> dict:
    env = dict(os.environ)
    shim = pathlib.Path(tempfile.gettempdir()) / "ots-ssl-shim"
    shim.mkdir(exist_ok=True)
    target = shim / "ssl.dll"
    if not target.exists() and LIBCRYPTO.exists():
        shutil.copyfile(LIBCRYPTO, target)
    env["PATH"] = f"{shim};{env['PATH']}"
    return env


def run_ots(args: list[str], env: dict, quiet: bool = False) -> int:
    if not quiet:
        print(f"$ ots {' '.join(args)}")
    proc = subprocess.run([str(OTS_EXE), *args], env=env, cwd=REPO,
                          capture_output=True, text=True)
    output = (proc.stdout + proc.stderr).strip()
    if output and not quiet:
        print("  " + output.replace("\n", "\n  "))
    return proc.returncode


def stamp_dir(run_dir: pathlib.Path, env: dict) -> list[pathlib.Path]:
    """Stamp every unstamped .csv/.json artifact in a run folder.
    Returns the receipts now covering the folder. Never deletes anything."""
    receipts = []
    for artifact in sorted(run_dir.iterdir()):
        if artifact.suffix not in (".csv", ".json"):
            continue
        receipt = artifact.with_suffix(artifact.suffix + ".ots")
        if not receipt.exists():
            run_ots(["stamp", str(artifact.relative_to(REPO))], env)
        elif artifact.stat().st_mtime > receipt.stat().st_mtime:
            print(f"  [WARN] {artifact.name} changed AFTER it was stamped — "
                  "its receipt is stale. If the old version was never "
                  "committed, delete the .ots and rerun to re-stamp.")
        if receipt.exists():
            receipts.append(receipt)
    return receipts


def upgrade_all(env: dict) -> None:
    """Upgrade every receipt in the repo (idempotent; pending ones complete
    once their stamp lands in a Bitcoin block). Leaves .ots.bak files, which
    are gitignored."""
    for receipt in sorted(REPO.rglob("*.ots")):
        if "data_cache" in receipt.parts:
            continue
        run_ots(["upgrade", str(receipt.relative_to(REPO))], env)


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: python scripts/stamp_run.py runs/YYYY-MM-DD[-test]")
    run_dir = REPO / sys.argv[1]
    if not run_dir.is_dir():
        sys.exit(f"not a directory: {run_dir}")
    if not OTS_EXE.exists():
        sys.exit(f"ots client not found at {OTS_EXE}")
    env = ots_env()
    stamp_dir(run_dir, env)
    upgrade_all(env)
    print("\ndone — commit the new/updated .ots receipts "
          "(full_*.csv stays local; its receipt is the public proof)")


if __name__ == "__main__":
    main()
