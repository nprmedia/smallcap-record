# Running the v0 screener

Every methodology parameter lives in `config/v0.yaml` (pre-registered; §9
protocol to change). `config/backends.yaml` holds operational plumbing only —
endpoints, rate limits, and the free-backend sample ticker list.

## One-time setup

```
pip install --user -r requirements.txt
copy .env.example .env      # then fill in keys
```

Keys in `.env` (never committed):
- `TIINGO_API_KEY` — free at tiingo.com; powers prices for the free backend.
- `NASDAQ_DATA_LINK_API_KEY` — Sharadar, from August.
- `EDGAR_USER_AGENT` — already prefilled; SEC just wants a contact address.

## A run

```
python -m screener.run --backend free                 # test backend, today
python -m screener.run --backend free --as-of 2026-08-20
python -m screener.run --backend sharadar             # from August
```

Output lands in `runs/YYYY-MM-DD/`:

| file | visibility |
|---|---|
| `full_screen.csv` | local only (gitignored) — all columns, licensed raw values |
| `full_universe_log.csv` | local only — why each candidate was excluded |
| `public_screen.csv` | committed — identifiers, sector percentiles, composite, picks, outcomes |
| `run_meta.json` | committed — provenance, counts, disclosures, artifact SHA-256 hashes |

Dates matching the §7 cadence (Mar/May/Aug/Nov 20, rolled to the next
business day) are labeled `run_kind=official`; anything else is `test`.

## After every run

```
python scripts/stamp_run.py runs/YYYY-MM-DD
```

stamps the new artifacts with OpenTimestamps and upgrades all prior receipts;
commit the `.ots` files plus the public artifacts.

## Sanity check without network

```
python -m tests.test_pipeline
```

runs the whole pipeline on a synthetic universe with hand-computed expected
results (filters, gates, ranks, tie-breaks, picks, schema).

## Before the first Sharadar run (August)

Work through the TODO list at the top of `screener/backends/sharadar.py` —
field names are written against documentation and unverified, and the CBOP
accrual method needs a decision (SF1 lacks cash-flow-statement working-capital
lines; the pre-registered method is cash_flow_statement).
