"""Run-output schema per METHODOLOGY.md §5.

One row per universe name per run. Row key: (figi, run_date).
Identity: figi + cik + ticker + config_version.
Schema policy is append-only: new columns may be added in later config
versions; existing columns are never renamed or redefined.

FULL_COLUMNS -> full_*.csv, kept local (vendor-licensed raw values), its
SHA-256 is OpenTimestamps-stamped and the receipt committed.
PUBLIC_COLUMNS -> public_*.csv, committed: identifiers, sector percentiles,
composite, pick and outcome fields — derived, non-proprietary values only,
plus staleness_days which §7 promises per name at every run.
"""

FULL_COLUMNS = [
    # --- identity / row key ---
    "figi", "run_date", "cik", "ticker", "company_name", "exchange", "sector",
    "config_version", "data_backend", "run_kind",
    # --- universe / data quality ---
    "market_cap_usd", "adv_3m_median_usd", "months_since_listing",
    "quarters_filed", "staleness_days",
    # --- gate raws and results (§3, order per config) ---
    "ebit_ttm_usd", "ebitda_ttm_usd", "net_debt_usd", "net_debt_to_ebitda",
    "announced_target", "mom_12_1", "mom_12_1_universe_pctile",
    "gate_ebit_pass", "gate_leverage_pass", "gate_target_pass",
    "gate_momentum_pass", "gates_all_pass",
    # --- rank raws, sector percentiles, composite (§3; survivors only) ---
    "total_assets_usd", "asset_growth_yoy", "cbop_ttm_usd", "cbop_a",
    "enterprise_value_usd", "ebit_ev",
    "rank_cbop_a_sector_pctile", "rank_ebit_ev_sector_pctile",
    "rank_neg_asset_growth_sector_pctile", "composite",
    # --- observation layer (§4): raw continuous values, never binarized;
    #     obs_insider_cluster_primary is the single pre-registered headline
    #     test (≥2 distinct officer/director non-plan buyers, ≥$100K, 90d) ---
    "obs_n_insider_buyers_90d", "obs_insider_net_buy_usd_90d",
    "insider_od_buyers_90d", "insider_od_buy_usd_90d",
    "obs_insider_cluster_primary",
    "obs_si_pct_float", "obs_days_to_cover", "obs_net_payout_yield_ttm",
    "obs_sue_srw", "obs_lm_neg_share", "obs_lm_neg_share_qoq_delta",
    "obs_hiring_velocity_qoq",
    # --- reserved for qualitative overlay (never a pick input in v0) ---
    "qual_score",
    # --- picks (§7) ---
    "pick", "pick_rank", "pick_shortfall",
    # --- outcomes (§6): null at run time, filled at the 6m/12m horizons ---
    "price_at_run", "benchmark_at_run",
    "ret_6m", "ret_12m", "excess_6m", "excess_12m", "hit_12m", "return_basis",
]

PUBLIC_COLUMNS = [
    "figi", "run_date", "cik", "ticker", "company_name", "exchange", "sector",
    "config_version", "data_backend", "run_kind",
    "staleness_days",
    "rank_cbop_a_sector_pctile", "rank_ebit_ev_sector_pctile",
    "rank_neg_asset_growth_sector_pctile", "composite",
    "pick", "pick_rank", "pick_shortfall",
    "excess_6m", "excess_12m", "hit_12m", "return_basis",
]

# Contract every data backend must satisfy: fetch(as_of) returns one row per
# candidate security with exactly these columns (values may be null where a
# source cannot supply them — the pipeline treats null honestly, it never
# fabricates). This contract is what makes backends interchangeable.
BACKEND_COLUMNS = [
    "ticker", "company_name", "cik", "figi", "exchange", "sector",
    "security_type_ok", "is_fpi", "is_lp", "is_reit", "is_pre_revenue_biotech",
    "months_since_listing", "quarters_filed",
    "price", "market_cap_usd", "adv_3m_median_usd", "mom_12_1",
    "ebit_ttm_usd", "ebitda_ttm_usd", "net_debt_usd",
    "total_assets_usd", "asset_growth_yoy", "cbop_ttm_usd",
    "net_payout_ttm_usd", "revenue_ttm_usd",
    "announced_target", "staleness_days",
    "obs_n_insider_buyers_90d", "obs_insider_net_buy_usd_90d",
    "insider_od_buyers_90d", "insider_od_buy_usd_90d",
    "obs_si_pct_float", "obs_days_to_cover",
    "obs_sue_srw", "obs_lm_neg_share", "obs_lm_neg_share_qoq_delta",
    "obs_hiring_velocity_qoq",
]
