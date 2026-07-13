"""Pick selection per config `cadence.picks` (METHODOLOGY.md §7).

Top N by composite among gate-passers. Fixed N, purely mechanical, no
override. Ties break deterministically per config: higher CBOP sector
percentile, then lexicographic FIGI — any reader can regenerate the pick
list from config plus data with zero judgment calls. If fewer than N names
pass all gates, all passers are taken and pick_shortfall marks every row.
"""
from __future__ import annotations

import pandas as pd

from ..config import num

TIE_BREAK_COLUMNS = {
    "cbop_sector_percentile_desc": ("rank_cbop_a_sector_pctile", False),
    "figi_lexicographic": ("figi", True),
}


def apply_picks(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    p = cfg["cadence"]["picks"]
    assert p["selection"] == "top_composite_among_gate_passers"
    assert p["override"] == "none"
    n = int(num(p["n"]))

    out = df.copy()
    eligible = out[(out["gates_all_pass"] == True) & out["composite"].notna()]  # noqa: E712

    sort_cols, ascendings = ["composite"], [False]
    for rule in cfg["cadence"]["tie_break"]:
        col, asc = TIE_BREAK_COLUMNS[rule]
        sort_cols.append(col)
        ascendings.append(asc)
    ordered = eligible.sort_values(sort_cols, ascending=ascendings, kind="mergesort")

    picked = ordered.head(n)
    out["pick"] = out.index.isin(picked.index)
    out["pick_rank"] = pd.NA
    out.loc[picked.index, "pick_rank"] = range(1, len(picked) + 1)
    out["pick_shortfall"] = len(picked) < n
    return out
