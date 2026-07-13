"""Observation layer per config `observation_layer:` block (METHODOLOGY.md §4).

Six candidate signals recorded for every universe name at every run — raw
continuous values, never binarized flags. None affect picks until graduated
under §8. Backends that cannot supply a signal deliver null; the pipeline
records the null honestly.

The one derived boolean, obs_insider_cluster_primary, is the pre-registered
headline test (≥2 distinct officer/director non-plan buyers, ≥$100K
aggregate, trailing 90 days) — its parameters come from config, and the raw
fields stored alongside permit sensitivity analyses.
"""
from __future__ import annotations

import pandas as pd

from ..config import num


def apply_observation(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    obs = cfg["observation_layer"]
    out = df.copy()

    # net payout yield: completed buybacks + dividends − issuance, over market cap
    out["obs_net_payout_yield_ttm"] = out["net_payout_ttm_usd"] / out["market_cap_usd"]

    # pre-registered primary insider-cluster test
    t = obs["primary_cluster_test"]
    min_buyers = num(t["min_distinct_buyers"])
    min_usd = num(t["min_aggregate_usd"])
    buyers = out["insider_od_buyers_90d"]
    dollars = out["insider_od_buy_usd_90d"]
    flag = buyers.ge(min_buyers) & dollars.ge(min_usd)
    # null inputs -> null flag (unknown, not False)
    flag = flag.where(buyers.notna() & dollars.notna(), pd.NA)
    out["obs_insider_cluster_primary"] = flag

    # reserved column — never a pick input in v0
    out["qual_score"] = pd.NA
    return out
