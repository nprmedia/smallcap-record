"""Sharadar backend (Nasdaq Data Link SFA bundle) — the pinned primary source.

STATUS: written against Sharadar's public documentation but UNVERIFIED —
the subscription starts ~Aug 2026. Before the first real run, verify:
  1. SF1 field names/signs used below (ebit, ebitda, debt, cashnequsd,
     assets, ncfdiv, ncfcommon, revenue) against the actual schema.
  2. SF2 10b5-1 plan-trade indicator: if SF2 carries no plan flag, insider
     fields must fall back to EDGAR Form 4 parsing (free backend code) to
     honor the pre-registered plan-trade exclusion.
  3. CBOP accruals: SF1 has no cash-flow-statement working-capital lines, so
     accruals here use balance-sheet deltas (ΔAR + ΔInv − ΔAP − ΔDefRev).
     config pre-registers accruals_method: cash_flow_statement — either
     source those lines from EDGAR on top of Sharadar, or amend via §9.
  4. EVENTS eventcodes for announced acquisitions (gate 3).
  5. Sharadar's sector scheme vs GICS (config says gics_sector) — map or
     document the deviation.

Dimension is as-reported (ARQ / ART) per the source pin — never
most-recent-reported, so restatements cannot leak backward.
"""
from __future__ import annotations

import datetime as dt
import os

import pandas as pd
import requests

from .base import Backend

ARQ_FIELDS = "ticker,calendardate,datekey,reportperiod,assets,receivables,inventory,payables,deferredrev,debtusd,cashnequsd,investmentsc,ebit,ebitda,revenueusd,ncfdiv,ncfcommon,epsdil,sharesbas"


class SharadarBackend(Backend):
    name = "sharadar"

    def __init__(self, v0: dict, backends_cfg: dict):
        self.v0 = v0
        self.base_url = backends_cfg["sharadar"]["base_url"]
        self.api_key = os.environ.get("NASDAQ_DATA_LINK_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "NASDAQ_DATA_LINK_API_KEY missing from .env — the Sharadar "
                "backend needs the subscription (starts Aug 2026). "
                "Use --backend free until then.")
        self.session = requests.Session()

    # ---- raw table access ----------------------------------------------------
    def _table(self, table: str, **params) -> pd.DataFrame:
        """Fetch a datatable, following cursors. Raises loudly on failure so a
        field-name mismatch in August is impossible to miss."""
        frames, cursor = [], None
        while True:
            q = {"api_key": self.api_key, **params}
            if cursor:
                q["qopts.cursor_id"] = cursor
            resp = self.session.get(f"{self.base_url}/{table}.json", params=q,
                                    timeout=120)
            resp.raise_for_status()
            body = resp.json()["datatable"]
            cols = [c["name"] for c in body["columns"]]
            frames.append(pd.DataFrame(body["data"], columns=cols))
            cursor = resp.json().get("meta", {}).get("next_cursor_id")
            if not cursor:
                return pd.concat(frames, ignore_index=True)

    # ---- contract ------------------------------------------------------------
    def fetch(self, as_of: dt.date) -> pd.DataFrame:
        tickers = self._table(
            "SHARADAR/TICKERS", table="SF1",
            **{"qopts.columns": "ticker,name,exchange,category,sector,industry,"
                                "location,firstpricedate,isdelisted,secfilings,"
                                "permaticker,cusips"})
        tickers = tickers[tickers["isdelisted"] == "N"]

        # TODO(Aug 2026): implement the full assembly against live tables:
        #   - ARQ/ART fundamentals per ARQ_FIELDS (point-in-time via datekey <= as_of)
        #   - SEP adjusted closes -> mom_12_1; close*volume -> adv_3m_median
        #   - DAILY -> marketcap as cross-check
        #   - SF2 -> insider fields (mind the plan-flag caveat above)
        #   - EVENTS -> announced_target
        # The free backend is the working reference implementation of the
        # contract; mirror its output exactly.
        raise NotImplementedError(
            "Sharadar backend is scaffolded but unverified — the subscription "
            "starts in August. Run with --backend free until then. "
            f"(Connectivity OK: {len(tickers)} tickers visible in metadata.)")

    def benchmark_level(self, as_of: dt.date) -> float | None:
        sfp = self._table("SHARADAR/SFP",
                          ticker=self.v0["data"]["benchmark_series"]["ticker"],
                          **{"date.lte": as_of.isoformat(),
                             "qopts.columns": "ticker,date,closeadj"})
        if sfp.empty:
            return None
        return float(sfp.sort_values("date").iloc[-1]["closeadj"])
