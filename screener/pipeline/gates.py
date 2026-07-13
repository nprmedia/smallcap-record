"""The four disqualifying gates per config `gates:` block (METHODOLOGY.md §3).

Gates disqualify, ranks select. A null input fails its gate — a name we
cannot verify does not pass. Gate order follows the config: EBIT > 0 first
makes the leverage gate well-defined.

Free-backend caveat: `announced_target` is an EDGAR-filings heuristic
(merger proxy / tender-offer forms in the last year), disclosed in run_meta.
"""
from __future__ import annotations

import pandas as pd

from ..config import num


def apply_gates(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    g = cfg["gates"]
    out = df.copy()

    # Gate 1: trailing-twelve-month EBIT > 0
    if g["ebit_ttm_positive"]:
        out["gate_ebit_pass"] = out["ebit_ttm_usd"].gt(0).fillna(False)
    else:
        out["gate_ebit_pass"] = True

    # Gate 2: net debt / EBITDA ≤ ceiling (only meaningful with EBITDA > 0;
    # non-positive EBITDA fails — leverage is unmeasurable, not "fine")
    ceiling = num(g["net_debt_to_ebitda_max"])
    out["net_debt_to_ebitda"] = out["net_debt_usd"] / out["ebitda_ttm_usd"]
    measurable = out["ebitda_ttm_usd"].gt(0).fillna(False)
    out.loc[~measurable, "net_debt_to_ebitda"] = pd.NA
    out["gate_leverage_pass"] = (
        measurable & out["net_debt_to_ebitda"].le(ceiling).fillna(False)
    )

    # Gate 3: no announced acquisition of the company pending
    if g["exclude_announced_targets"]:
        out["gate_target_pass"] = ~out["announced_target"].fillna(False).astype(bool)
    else:
        out["gate_target_pass"] = True

    # Gate 4: 12-1 momentum above the universe p-th percentile ("no falling
    # knives"). Percentile computed across the whole universe, nulls fail.
    pctl = num(g["momentum_12_1_min_universe_percentile"]) / 100.0
    out["mom_12_1_universe_pctile"] = out["mom_12_1"].rank(pct=True)
    threshold = out["mom_12_1"].quantile(pctl)
    out["gate_momentum_pass"] = out["mom_12_1"].gt(threshold).fillna(False)

    out["gates_all_pass"] = (
        out["gate_ebit_pass"] & out["gate_leverage_pass"]
        & out["gate_target_pass"] & out["gate_momentum_pass"]
    )
    return out
