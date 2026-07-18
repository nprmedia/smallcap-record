"""Run artifact writing per METHODOLOGY.md §5 and repo conventions (CLAUDE.md).

runs/YYYY-MM-DD/
  full_screen.csv        one row per universe name, all columns — LOCAL ONLY
                         (gitignored; its SHA-256 is OTS-stamped, receipt committed)
  full_universe_log.csv  exclusion log with raw reasons — LOCAL ONLY (gitignored)
  public_screen.csv      redacted, derived/non-proprietary columns — committed
  run_meta.json          run provenance, counts, disclosures — committed
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib

import pandas as pd

from ..config import ROOT
from ..schema import FULL_COLUMNS, PUBLIC_COLUMNS


def run_dir(run_date: dt.date, run_kind: str) -> pathlib.Path:
    # test runs are fenced from the official record by a -test folder suffix
    # (see README): infrastructure validation only, never track-record material
    suffix = "-test" if run_kind == "test" else ""
    d = ROOT / "runs" / (run_date.isoformat() + suffix)
    d.mkdir(parents=True, exist_ok=True)
    return d


def finalize_frame(df: pd.DataFrame, run_date: dt.date, config_version: str,
                   backend_name: str, run_kind: str) -> pd.DataFrame:
    """Stamp identity columns, add outcome placeholders, order per schema."""
    out = df.copy()
    out["run_date"] = run_date.isoformat()
    out["config_version"] = config_version
    out["data_backend"] = backend_name
    out["run_kind"] = run_kind
    out["price_at_run"] = out["price"]
    # outcome fields are filled at the 6m/12m horizons, never at run time
    for col in ["ret_6m", "ret_12m", "excess_6m", "excess_12m", "hit_12m",
                "return_basis"]:
        out[col] = pd.NA
    missing = [c for c in FULL_COLUMNS if c not in out.columns]
    if missing:
        raise ValueError(f"schema columns missing from pipeline output: {missing}")
    # deterministic row order: sector, then ticker
    return out[FULL_COLUMNS].sort_values(["sector", "ticker"]).reset_index(drop=True)


def sha256_of(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_run(full: pd.DataFrame, exclusion_log: pd.DataFrame,
              run_date: dt.date, meta: dict) -> dict:
    d = run_dir(run_date, meta["run_kind"])

    full_path = d / "full_screen.csv"
    full.to_csv(full_path, index=False)

    log_path = d / "full_universe_log.csv"
    exclusion_log.to_csv(log_path, index=False)

    public_path = d / "public_screen.csv"
    full[PUBLIC_COLUMNS].to_csv(public_path, index=False)

    # the full CSV never leaves this machine; its hash proves its integrity
    meta = dict(meta)
    meta["artifacts"] = {
        "full_screen_csv_sha256": sha256_of(full_path),
        "full_universe_log_csv_sha256": sha256_of(log_path),
        "public_screen_csv_sha256": sha256_of(public_path),
    }
    meta_path = d / "run_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")

    return {"dir": d, "full": full_path, "log": log_path,
            "public": public_path, "meta": meta_path}
