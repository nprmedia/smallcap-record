"""Universe construction per config `universe:` block (METHODOLOGY.md §2).

Every filter reads its threshold from config. Names failing a filter are
dropped and logged with a reason; names missing the data a filter needs are
also dropped ("missing_data:<field>") — the universe never contains a name
we could not verify. The exclusion log is written alongside the run so any
reader can see exactly why each candidate fell out.
"""
from __future__ import annotations

import pandas as pd

from ..config import num

SECTOR_EXCLUSION_MAP = {
    "financials": "Financials",
    "reits": "Real Estate",
}
FLAG_EXCLUSION_MAP = {
    "pre_revenue_biotech": "is_pre_revenue_biotech",
    "foreign_private_issuers": "is_fpi",
    "limited_partnerships": "is_lp",
}


def build_universe(raw: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (universe, exclusion_log). `raw` is the backend contract frame."""
    u = cfg["universe"]
    df = raw.copy()
    log: list[dict] = []

    def drop(mask: pd.Series, reason: str) -> None:
        nonlocal df
        for _, row in df[mask].iterrows():
            log.append({"ticker": row["ticker"], "cik": row["cik"],
                        "excluded_by": reason})
        df = df[~mask]

    # security type (common stock only)
    drop(df["security_type_ok"] == False, "not_common_stock")  # noqa: E712

    # exchange listing
    exchanges = [e.upper() for e in u["exchanges"]]
    drop(~df["exchange"].str.upper().isin(exchanges), "exchange")

    # market cap band
    lo, hi = num(u["market_cap_usd"]["min"]), num(u["market_cap_usd"]["max"])
    drop(df["market_cap_usd"].isna(), "missing_data:market_cap_usd")
    drop((df["market_cap_usd"] < lo) | (df["market_cap_usd"] > hi), "market_cap_band")

    # liquidity: 3-month median dollar volume
    adv_min = num(u["adv_3m_median_usd_min"])
    drop(df["adv_3m_median_usd"].isna(), "missing_data:adv_3m_median_usd")
    drop(df["adv_3m_median_usd"] < adv_min, "adv_below_min")

    # sector exclusions (financials, REITs) — REITs also caught by flag
    for token in u["exclude_sectors"]:
        sector_name = SECTOR_EXCLUSION_MAP[token]
        drop(df["sector"] == sector_name, f"sector:{token}")
    drop(df["is_reit"] == True, "flag:reit")  # noqa: E712

    # other exclusions (pre-revenue biotech, FPIs, LPs)
    for token in u["exclude_other"]:
        flag = FLAG_EXCLUSION_MAP[token]
        drop(df[flag] == True, f"flag:{token}")  # noqa: E712

    # seasoning
    drop(df["months_since_listing"].isna(), "missing_data:months_since_listing")
    drop(df["months_since_listing"] < num(u["min_months_since_listing_or_combination"]),
         "seasoning_months")
    drop(df["quarters_filed"].isna(), "missing_data:quarters_filed")
    drop(df["quarters_filed"] < num(u["min_quarters_filed"]), "seasoning_quarters")

    # one share class per issuer: keep the most liquid class
    if int(num(u["share_classes_per_issuer"])) == 1:
        ranked = df.sort_values("adv_3m_median_usd", ascending=False)
        dupes = ranked.duplicated(subset="cik", keep="first")
        drop(df.index.isin(ranked[dupes].index), "duplicate_share_class")

    return df.reset_index(drop=True), pd.DataFrame(log, columns=["ticker", "cik", "excluded_by"])
