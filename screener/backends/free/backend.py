"""Free/testing backend: EDGAR fundamentals + Tiingo prices + OpenFIGI ids,
over the hand-curated sample universe in config/backends.yaml.

This backend exists to exercise the pipeline before the Sharadar
subscription starts (Aug 2026). Its known gaps — all disclosed per run:
- short interest, call tone, hiring velocity: no free source -> null
- GICS sector: hand-assigned in backends.yaml (no free GICS license)
- FPI / LP / common-stock flags: hand-curated for the sample list
- announced_target: EDGAR filing-forms heuristic, not a deal feed
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

from ..base import Backend
from .edgar import Edgar
from .figi import map_figis
from .http import CachedSession, edgar_user_agent
from .tiingo import Tiingo

INSIDER_WINDOW_DAYS = 90  # from the pre-registered field definitions (§4)


class FreeBackend(Backend):
    name = "free"

    def __init__(self, v0: dict, backends_cfg: dict):
        self.v0 = v0
        self.cfg = backends_cfg["free"]
        cache_cfg = backends_cfg.get("cache", {})
        edgar_session = CachedSession(
            cache_cfg, user_agent=edgar_user_agent(),
            max_per_sec=float(self.cfg["edgar"].get("max_requests_per_sec", 6)))
        plain_session = CachedSession(cache_cfg, user_agent="smallcap-record/0.1")
        self.edgar = Edgar(edgar_session, self.cfg["edgar"])
        self.tiingo = Tiingo(plain_session, self.cfg["tiingo"])
        self.openfigi_session = plain_session
        # the primary insider test's window is pre-registered in v0.yaml
        window = v0["observation_layer"]["primary_cluster_test"]["window_days"]
        self.insider_window = int(float(window))

    def fetch(self, as_of: dt.date) -> pd.DataFrame:
        sample = self.cfg["sample_universe"]
        tickers = [row["ticker"].upper() for row in sample]
        sectors = {row["ticker"].upper(): row["sector"] for row in sample}

        directory = self.edgar.ticker_directory()
        figis = map_figis(self.openfigi_session, self.cfg["openfigi"], tickers)

        rows = []
        for ticker in tickers:
            print(f"  fetching {ticker} ...")
            listing = directory.get(ticker)
            row = {
                "ticker": ticker,
                "company_name": listing["name"] if listing else None,
                "cik": listing["cik"] if listing else None,
                "figi": figis[ticker],
                "exchange": listing["exchange"] if listing else None,
                "sector": sectors[ticker],
                # hand-curated sample list: common stock, no FPIs/LPs
                "security_type_ok": True,
                "is_fpi": False,
                "is_lp": False,
                "is_reit": sectors[ticker] == "Real Estate",
                # no free source for these three observation signals:
                "obs_si_pct_float": None,
                "obs_days_to_cover": None,
                "obs_lm_neg_share": None,
                "obs_lm_neg_share_qoq_delta": None,
                "obs_hiring_velocity_qoq": None,
            }
            row.update(self.tiingo.metrics(ticker, as_of))

            if listing:
                cik = listing["cik"]
                row.update(self.edgar.fundamentals(cik, as_of))
                row.update(self.edgar.seasoning(cik, as_of))
                row["announced_target"] = self.edgar.announced_target(cik, as_of)
                row.update(self.edgar.insider_activity(
                    cik, as_of, self.insider_window))
            else:
                print(f"  [warn] {ticker}: not in EDGAR ticker directory")

            shares = row.get("shares_outstanding")
            price = row.get("price")
            row["market_cap_usd"] = shares * price if shares and price else None

            revenue = row.get("revenue_ttm_usd")
            row["is_pre_revenue_biotech"] = (
                sectors[ticker] == "Health Care" and (revenue is None or revenue <= 0))
            rows.append(row)

        df = pd.DataFrame(rows)
        return self.validate(df)

    def benchmark_level(self, as_of: dt.date) -> float | None:
        ticker = self.v0["data"]["benchmark_series"]["ticker"]
        return self.tiingo.level(ticker, as_of)
