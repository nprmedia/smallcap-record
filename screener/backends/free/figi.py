"""OpenFIGI ticker -> FIGI mapping (keyless; conservative batching).

FIGI is the primary identity key (METHODOLOGY.md §5). We prefer the
share-class FIGI (stable across venues), then the composite, then the
venue-level FIGI. A name OpenFIGI cannot map gets the deterministic
placeholder NOFIGI-<ticker> so row keys and tie-breaks still work; the
run_meta discloses any placeholders.
"""
from __future__ import annotations

import time


def map_figis(session, cfg: dict, tickers: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    batch_size = int(cfg.get("batch_size", 5))
    batches = [tickers[i:i + batch_size] for i in range(0, len(tickers), batch_size)]
    for i, batch in enumerate(batches):
        jobs = [{"idType": "TICKER", "idValue": t, "exchCode": "US"} for t in batch]
        result = session.post_json(cfg["mapping_url"], jobs)
        if isinstance(result, list):
            for ticker, job_result in zip(batch, result):
                data = (job_result or {}).get("data") or []
                if data:
                    rec = data[0]
                    out[ticker] = (rec.get("shareClassFIGI")
                                   or rec.get("compositeFIGI") or rec.get("figi"))
        if i < len(batches) - 1:
            time.sleep(2.5)   # keyless limit is 25 requests/minute
    for t in tickers:
        out.setdefault(t, f"NOFIGI-{t}")
    return out
