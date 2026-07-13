"""Deterministic pipeline test on a synthetic backend frame — no network.

Verifies against hand-computed expectations: universe filters and exclusion
log, all four gates, sector-relative percentiles, equal-weight composite,
tie-breaking, pick selection, shortfall flagging, and schema completeness.

Run:  python -m tests.test_pipeline
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

from screener.config import load_v0
from screener.pipeline.gates import apply_gates
from screener.pipeline.observation import apply_observation
from screener.pipeline.output import finalize_frame
from screener.pipeline.picks import apply_picks
from screener.pipeline.ranks import apply_ranks, compute_factor_raws
from screener.pipeline.universe import build_universe
from screener.schema import BACKEND_COLUMNS, FULL_COLUMNS


def synthetic_frame() -> pd.DataFrame:
    base = {
        "company_name": "Test Co", "exchange": "NASDAQ",
        "security_type_ok": True, "is_fpi": False, "is_lp": False,
        "is_reit": False, "is_pre_revenue_biotech": False,
        "months_since_listing": 60, "quarters_filed": 20,
        "price": 50.0, "market_cap_usd": 1e9, "adv_3m_median_usd": 5e6,
        "mom_12_1": 0.10,
        "ebit_ttm_usd": 100e6, "ebitda_ttm_usd": 150e6, "net_debt_usd": 200e6,
        "total_assets_usd": 1e9, "asset_growth_yoy": 0.05,
        "cbop_ttm_usd": 90e6, "net_payout_ttm_usd": 30e6, "revenue_ttm_usd": 800e6,
        "announced_target": False, "staleness_days": 45,
        "obs_n_insider_buyers_90d": 0, "obs_insider_net_buy_usd_90d": 0.0,
        "insider_od_buyers_90d": 0, "insider_od_buy_usd_90d": 0.0,
        "obs_si_pct_float": None, "obs_days_to_cover": None,
        "obs_sue_srw": None, "obs_lm_neg_share": None,
        "obs_lm_neg_share_qoq_delta": None, "obs_hiring_velocity_qoq": None,
    }
    rows = []

    def add(ticker, cik, sector, **overrides):
        row = dict(base, ticker=ticker, cik=cik, figi=f"BBG-{ticker}",
                   sector=sector)
        row.update(overrides)
        rows.append(row)

    # -- universe-filter victims --------------------------------------------
    add("XCAP", 1, "Industrials", market_cap_usd=5e9)          # cap band
    add("XADV", 2, "Industrials", adv_3m_median_usd=5e5)       # liquidity
    add("XFIN", 3, "Financials")                               # sector excl.
    add("XNEW", 4, "Industrials", months_since_listing=6)      # seasoning
    add("XDUP", 5, "Industrials", adv_3m_median_usd=1e7)       # dup class kept
    add("XDU2", 5, "Industrials", adv_3m_median_usd=2e6)       # dup class dropped
    # -- gate victims ---------------------------------------------------------
    add("GEBIT", 6, "Industrials", ebit_ttm_usd=-10e6)         # gate 1
    add("GLEV", 7, "Industrials", net_debt_usd=600e6)          # gate 2 (4x)
    add("GTGT", 8, "Industrials", announced_target=True)       # gate 3
    add("GMOM", 9, "Industrials", mom_12_1=-0.60)              # gate 4 (bottom decile)
    # -- survivors: 2 sectors, known factor ordering --------------------------
    # Industrials: A dominates B on all three factors
    add("SVA", 10, "Industrials", cbop_ttm_usd=200e6, ebit_ttm_usd=180e6,
        asset_growth_yoy=0.01, ebitda_ttm_usd=220e6,
        insider_od_buyers_90d=3, insider_od_buy_usd_90d=250e3,
        obs_n_insider_buyers_90d=3, obs_insider_net_buy_usd_90d=250e3)
    add("SVB", 11, "Industrials", cbop_ttm_usd=50e6, ebit_ttm_usd=60e6,
        asset_growth_yoy=0.30, ebitda_ttm_usd=90e6)
    # Tech: C and D identical composite -> tie-break on CBOP pctile (also
    # identical) -> FIGI lexicographic decides
    add("SVC", 12, "Information Technology")
    add("SVD", 13, "Information Technology")
    add("SVE", 14, "Information Technology", cbop_ttm_usd=None)  # null factor
    return pd.DataFrame(rows)[BACKEND_COLUMNS]


def main() -> None:
    cfg = load_v0()
    raw = synthetic_frame()

    universe, log = build_universe(raw, cfg)
    gone = set(log["ticker"])
    assert gone == {"XCAP", "XADV", "XFIN", "XNEW", "XDU2"}, gone
    reasons = dict(zip(log["ticker"], log["excluded_by"]))
    assert reasons["XCAP"] == "market_cap_band"
    assert reasons["XFIN"] == "sector:financials"
    assert reasons["XDU2"] == "duplicate_share_class"
    assert "XDUP" in set(universe["ticker"]), "most liquid share class must survive"

    df = apply_gates(universe, cfg)
    by = df.set_index("ticker")
    assert not by.loc["GEBIT", "gate_ebit_pass"]
    assert not by.loc["GLEV", "gate_leverage_pass"]
    assert not by.loc["GTGT", "gate_target_pass"]
    assert not by.loc["GMOM", "gate_momentum_pass"]
    survivors = set(df[df["gates_all_pass"]]["ticker"])
    assert survivors == {"XDUP", "SVA", "SVB", "SVC", "SVD", "SVE"}, survivors

    df = compute_factor_raws(df)
    df = apply_ranks(df, cfg)
    by = df.set_index("ticker")
    # SVA beats SVB on every factor within Industrials
    assert by.loc["SVA", "composite"] > by.loc["SVB", "composite"]
    # identical inputs -> identical composite for the tech twins
    assert abs(by.loc["SVC", "composite"] - by.loc["SVD", "composite"]) < 1e-12
    # null factor -> null composite, never patched
    assert pd.isna(by.loc["SVE", "composite"])
    # non-survivors carry no rank
    assert pd.isna(by.loc["GEBIT", "composite"])

    df = apply_observation(df, cfg)
    by = df.set_index("ticker")
    # SVA: 3 officer/director buyers, $250K >= (2, $100K) -> primary flag true
    assert by.loc["SVA", "obs_insider_cluster_primary"] == True  # noqa: E712
    assert by.loc["SVB", "obs_insider_cluster_primary"] == False  # noqa: E712
    assert (by.loc["SVA", "obs_net_payout_yield_ttm"] - 0.03) < 1e-12

    df = apply_picks(df, cfg)
    picked = df[df["pick"]].set_index("ticker")
    # 5 eligible survivors (SVE has null composite) and pick target is 5
    assert len(picked) == 5 and df["pick_shortfall"].all() == False  # noqa: E712
    assert "SVE" not in picked.index
    # FIGI tie-break: BBG-SVC < BBG-SVD lexicographically
    assert picked.loc["SVC", "pick_rank"] < picked.loc["SVD", "pick_rank"]

    df["benchmark_at_run"] = 123.45
    full = finalize_frame(df, dt.date(2026, 7, 12), "testsha", "synthetic", "test")
    assert list(full.columns) == FULL_COLUMNS
    assert full["ret_12m"].isna().all(), "outcomes must be null at run time"

    print("all pipeline assertions passed "
          f"({len(raw)} synthetic names -> {len(picked)} picks)")


if __name__ == "__main__":
    main()
