"""Tiingo daily prices (free tier) — price level, 12-1 momentum, 3-month
median dollar volume, and the IJR benchmark level.

Requires TIINGO_API_KEY in .env. Without it every price-derived field is
null, which the universe filter then excludes as unverifiable — the run
still completes and says so, it never invents prices.

Momentum is computed on dividend/split-adjusted closes; dollar volume on
unadjusted close × volume (what actually traded).
"""
from __future__ import annotations

import datetime as dt
import os

TRADING_DAYS_12M = 252
TRADING_DAYS_1M = 21
TRADING_DAYS_3M = 63


class Tiingo:
    def __init__(self, session, cfg: dict):
        self.http = session
        self.cfg = cfg
        self.token = os.environ.get("TIINGO_API_KEY") or None
        self._warned = False

    def available(self) -> bool:
        if not self.token and not self._warned:
            print("  [warn] TIINGO_API_KEY not set — all price fields will be null")
            self._warned = True
        return bool(self.token)

    def history(self, ticker: str, as_of: dt.date) -> list[dict] | None:
        if not self.available():
            return None
        start = as_of - dt.timedelta(days=460)  # ~13 months of trading days
        rows = self.http.get_json(
            self.cfg["prices_url"].format(ticker=ticker.lower()),
            params={"startDate": start.isoformat(), "endDate": as_of.isoformat(),
                    "token": self.token, "format": "json"})
        if not isinstance(rows, list) or not rows:
            return None
        return [r for r in rows if r.get("date", "")[:10] <= as_of.isoformat()]

    def metrics(self, ticker: str, as_of: dt.date) -> dict:
        out = {"price": None, "mom_12_1": None, "adv_3m_median_usd": None,
               "volume_3m_median_shares": None}
        rows = self.history(ticker, as_of)
        if not rows:
            return out
        out["price"] = float(rows[-1]["close"])

        adj = [float(r["adjClose"]) for r in rows]
        if len(adj) >= TRADING_DAYS_12M + 1:
            p_1m_ago = adj[-(TRADING_DAYS_1M + 1)]
            p_12m_ago = adj[-(TRADING_DAYS_12M + 1)]
            if p_12m_ago > 0:
                out["mom_12_1"] = p_1m_ago / p_12m_ago - 1.0

        recent = rows[-TRADING_DAYS_3M:]
        if len(recent) >= TRADING_DAYS_3M // 2:
            out["adv_3m_median_usd"] = _median(
                float(r["close"]) * float(r["volume"]) for r in recent)
            # share-volume median, same window/convention as the ADV filter;
            # used as the days-to-cover denominator
            out["volume_3m_median_shares"] = _median(
                float(r["volume"]) for r in recent)
        return out

    def level(self, ticker: str, as_of: dt.date) -> float | None:
        """Latest dividend-adjusted close on or before as_of (benchmark use)."""
        rows = self.history(ticker, as_of)
        return float(rows[-1]["adjClose"]) if rows else None


def _median(values) -> float | None:
    ordered = sorted(values)
    if not ordered:
        return None
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2
