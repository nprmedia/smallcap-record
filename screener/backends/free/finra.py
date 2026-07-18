"""FINRA consolidated short interest (free, anonymous, twice-monthly).

Feeds the two pre-registered gate-destination observation signals
(config observation_layer: si_pct_float, days_to_cover). Point-in-time
discipline: uses the latest settlement date at or before as_of, never a
later one; settlement dates come from FINRA's partition listing, not a
hardcoded calendar.

Free-source deviations, surfaced to run_meta by the backend:
- free float is not published by FINRA/EDGAR, so si_pct_float is computed
  against shares outstanding (dei EntityCommonStockSharesOutstanding) —
  a disclosed denominator deviation, applied uniformly.
- days_to_cover is short interest / 3-month median daily share volume,
  matching the universe's median-ADV convention (not FINRA's own
  average-volume days-to-cover field).
"""
from __future__ import annotations

import datetime as dt


class Finra:
    def __init__(self, session, cfg: dict):
        self.http = session
        self.data_url = cfg["data_url"]
        self.partitions_url = cfg["partitions_url"]

    def latest_settlement(self, as_of: dt.date) -> dt.date | None:
        body = self.http.get_json(self.partitions_url)
        if not body:
            return None
        dates = sorted(
            dt.date.fromisoformat(p["partitions"][0])
            for p in body.get("availablePartitions", []) if p.get("partitions"))
        eligible = [d for d in dates if d <= as_of]
        return eligible[-1] if eligible else None

    def short_interest(self, tickers: list[str], as_of: dt.date
                       ) -> tuple[dict[str, float], dt.date | None]:
        """ticker -> short position (shares) at the latest settlement <= as_of."""
        settlement = self.latest_settlement(as_of)
        if settlement is None:
            return {}, None
        rows = self.http.post_json(self.data_url, {
            "limit": max(5000, len(tickers) * 2),
            "compareFilters": [{"fieldName": "settlementDate",
                                "fieldValue": settlement.isoformat(),
                                "compareType": "EQUAL"}],
            "domainFilters": [{"fieldName": "symbolCode", "values": tickers}],
        })
        if not isinstance(rows, list):
            return {}, settlement
        out = {}
        for r in rows:
            symbol = r.get("symbolCode")
            quantity = r.get("currentShortPositionQuantity")
            if symbol and quantity is not None:
                out[symbol.upper()] = float(quantity)
        return out, settlement
