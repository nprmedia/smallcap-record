"""Sector-relative ranks and composite per config `ranks:` block (METHODOLOGY.md §3).

Ranks are computed among gate survivors only, within GICS sector, as
percentiles in [0, 1] where higher is always better (low_is_good factors are
inverted by ranking descending). The composite is the equal-weighted mean and
requires all three factors present — a name with an incomputable factor gets
a null composite and cannot be picked; it is counted in run_meta, never
silently patched.
"""
from __future__ import annotations

import pandas as pd

# factor name in config -> column carrying the raw value
FACTOR_RAW = {
    "cbop_a": "cbop_a",
    "ebit_ev": "ebit_ev",
    "asset_growth_yoy": "asset_growth_yoy",
}
# factor name in config -> output percentile column (schema.py)
FACTOR_PCTILE = {
    "cbop_a": "rank_cbop_a_sector_pctile",
    "ebit_ev": "rank_ebit_ev_sector_pctile",
    "asset_growth_yoy": "rank_neg_asset_growth_sector_pctile",
}


def compute_factor_raws(df: pd.DataFrame) -> pd.DataFrame:
    """Derive the three factor raw values from backend fundamentals."""
    out = df.copy()
    out["cbop_a"] = out["cbop_ttm_usd"] / out["total_assets_usd"]
    out["enterprise_value_usd"] = out["market_cap_usd"] + out["net_debt_usd"]
    # EV ≤ 0 (net cash exceeding market cap) makes EBIT/EV meaningless — null it
    ev = out["enterprise_value_usd"]
    out["ebit_ev"] = (out["ebit_ttm_usd"] / ev).where(ev > 0)
    # asset_growth_yoy arrives from the backend
    return out


def apply_ranks(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    r = cfg["ranks"]
    assert r["weights"] == "equal", "v0 pre-registers equal weights only"
    out = df.copy()

    survivors = out["gates_all_pass"] == True  # noqa: E712
    pctile_cols = []
    for factor in r["factors"]:
        name, direction = factor["name"], factor["direction"]
        raw_col, pct_col = FACTOR_RAW[name], FACTOR_PCTILE[name]
        pctile_cols.append(pct_col)
        ascending = direction == "high_is_good"  # low_is_good ranks descending
        out[pct_col] = (
            out.loc[survivors]
            .groupby("sector")[raw_col]
            .rank(method="average", pct=True, ascending=ascending)
        )

    # equal-weighted composite; all factors required (skipna=False)
    out["composite"] = out[pctile_cols].mean(axis=1, skipna=False)
    return out
