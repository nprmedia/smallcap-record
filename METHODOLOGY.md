# Methodology — Pre-Registration

*Pre-registered July 2026, before the first run. This document changes only through the amendment protocol in §9. The OpenTimestamps receipt committed alongside it proves this text predates every outcome in the record.*

---

## 1. What this record is

A public, timestamped record of a systematic small/mid-cap equity research process: quarterly mechanical picks, pre-registered candidate signals, and fixed-horizon outcomes tracked against a benchmark — including the misses. Credibility is intended to live in the timeline, not the picks: forward calls made before outcomes were known, evaluated by rules written before the first run.

Scope note: this is a research journal, not a portfolio track record. It is not GIPS-compliant and makes no marketed performance claim. At this record's breadth (~20 picks/year), the return series cannot statistically separate skill from luck for years; the near-term value of the record is the quality of reasoning and the honesty of the follow-through, and this document says so up front.

## 2. Universe

US common stock, NYSE/Nasdaq listed only. Market cap $300M–$3B. 3-month median dollar volume ≥ $1M/day. Excluded: financials, REITs, pre-revenue biotech, foreign private issuers (no Section 16 filings — the insider signal depends on Form 4s), and limited partnerships. Minimum seasoning: ≥13 months since listing or business combination and ≥4 quarters of filings. One share class per issuer (most liquid class retained). Utilities are retained; their sector-specific distortions are handled by within-sector ranking (§3).

## 3. Decision core

Two stages: gates disqualify, ranks select.

**Gates (all must pass):**
1. EBIT (trailing twelve months) > 0
2. Net debt / EBITDA ≤ 3× — *the 3× is lender convention, not a derived threshold*
3. No announced acquisition of the company pending
4. 12-1 price momentum above the universe 10th percentile — *no falling knives; disclosed cost: this gate excludes the sharpest rebounders after market panics*

**Ranks (survivors only):** within-GICS-sector percentile ranks, equal-weighted one-third each:
- **CBOP/A** — cash-based operating profitability scaled by assets (operating profit excluding the accrual component; accruals computed via the cash-flow-statement method)
- **EBIT/EV** — operating profit per dollar of enterprise value. *Disclosed: the published valuation-metric horse race crowned the EBITDA variant; EBIT is chosen on reasoning (depreciation proxies maintenance capex), not head-to-head evidence, and the difference is second-order*
- **−Asset growth** — year-over-year total asset growth, inverted

Equal weights are the deliberate default: no principled derivation exists for any specific weight vector, and precise weights would be false precision. Ranking is within sector because cross-universe ranking would permanently overweight structurally cheap sectors; the evidence locates predictive power in within-industry comparisons.

## 4. Observation layer

Six candidate signals recorded for every name in the universe at every run — raw continuous values, never binarized flags. None affect picks until graduated under §8. Each destination (gate vs. rank) is pre-committed now so no signal can later be role-shopped into whichever slot flatters its results.

| Signal | Fields recorded | Hypothesis (pre-registered) | Destination if graduated |
|---|---|---|---|
| Insider cluster buying | n_distinct_buyers_90d, insider_net_buy_usd_90d (10b5-1 plan trades excluded) | Non-routine purchases with personal cash reveal private positive information, largest where analyst coverage is thinnest (+) | Rank |
| Short interest | si_pct_float, days_to_cover | Short sellers are informed and pay to hold the position; elevated short interest reveals negative information not yet in price (−) | Gate |
| Net payout yield | net_payout_yield_ttm (completed buybacks + dividends − issuance, cash-flow-statement sourced) | Completed capital return signals management's undervaluation belief and disciplines empire-building (+) | Rank |
| Earnings surprise (SUE) | sue_srw — seasonal-random-walk surprise scaled by its volatility; null until ~8 quarters computable | Prices underreact to earnings news where information diffuses slowly (+). *Negative-leaning prior disclosed: recent literature finds this drift dead-to-dying in modern US data; a null result here would confirm it* | Rank |
| Earnings-call tone | lm_neg_share (Loughran-McDonald negative-word share of management remarks) + QoQ change | Management language leaks deterioration before the numbers do; rising abnormal negativity is the signal (−) | Gate |
| Hiring velocity | hiring_velocity_qoq — job-posting count QoQ change, vertical names only, null elsewhere | In route-density service businesses, technician hiring leads booked revenue by 1–2 quarters (+). *Pre-registered adversary: the labor-investment literature finds firm hiring rate predicts returns negatively; this record adjudicates the conflict on its own data* | Rank |

**Primary insider test, pre-registered:** ≥2 distinct officer/director non-plan buyers, ≥$100K aggregate, trailing 90 days. Raw storage permits sensitivity analyses; this definition is the headline test and cannot be swapped after the fact.

**Disclosed leak:** the Form 4 10b5-1 checkbox does not apply to plans adopted before February 27, 2023; residual legacy-plan trades can pass the plan-trade filter. Magnitude unknown, expected to decay to zero.

## 5. Data, schema, and what is published

One row per name per run — picks are a boolean column; non-picks are the control group that makes §8 testable. Append-only: new columns may be added, existing columns are never redefined. Identity: FIGI + CIK + ticker + config_version (the git SHA of the ruleset that produced the row).

**Source pins.** Fundamentals and prices: Sharadar (Nasdaq Data Link), **as-reported dimension** — never most-recent-reported, so every value is as-known-at-run-date and restatements cannot leak backward. Fallback if the bundle exceeds budget at checkout: SEC EDGAR XBRL (as-filed) + Tiingo prices. Benchmark series: IJR dividend-adjusted close, proxying the S&P SmallCap 600 at a disclosed ~6bp/yr expense drag.

**Publication policy.** Vendor licensing prohibits republishing raw data fields. Each run therefore produces two files: a full CSV kept local, whose SHA-256 hash is OpenTimestamps-stamped and whose receipt is committed publicly, and a redacted public CSV (identifiers, sector percentiles, composite, pick and outcome fields — derived and non-proprietary values only). The complete record's integrity is provable without republishing licensed data.

**Corporate actions, pre-written:** any acquisition of a pick (cash or stock) — position valued at deal close, proceeds rolled forward at the benchmark return to the fixed horizon. Delisting for cause — final observable value plus distributions; if no observable exit exists, −100%, disclosed. Spin-offs — combined-entity value, as-if-held. Trading halts — last trade, stale-flagged. In a record covering acquisitive small caps, acquisitions of picks are the base case, and these rules exist before the first one happens.

## 6. Success metric

Fixed-horizon evaluation: every pick is scored at 12 months (primary) and 6 months (recorded) regardless of interim developments. No managed exits — exits would destroy attribution.

- **Benchmark:** S&P SmallCap 600, total return, via the IJR series.
- **Hit definition:** 12-month excess return > 0.
- **Pre-registered statistics:** hit rate, slugging (average win / average loss), mean excess return, median excess return. All four report together; no headline cherry-picking.
- **No formal risk adjustment** (beta or factor-neutral alpha): a legibility choice for a fundamental audience, stated as such.

**Benchmark disclosures:** (1) Size mismatch — the S&P 600's addition range starts at $1.2B market cap, so the $300M–$1.2B slice of this universe sits below the benchmark's intake floor; the index is chosen anyway because its profitability screen mirrors this record's own gates, making it the like-for-like and harder comparator, where the Russell 2000 (~40% unprofitable constituents in recent counts) would structurally flatter a profitability-gated strategy. (2) Regime — the S&P 600's long-run edge over the Russell 2000 reversed in the most recent 3–5 year window; the harder benchmark is chosen with that known.

## 7. Cadence and picks

Runs on **March 20, May 20, August 20, November 20** (next business day if weekend/holiday), placed ~5 days after the dominant SEC filing deadlines. Full runs only — no interim rows. Disclosed staleness: non-accelerated filers' annual reports (due 90 days after fiscal year-end) miss the March run and enter May; a `staleness_days` column reports data age per name at every run, since filer-tier heterogeneity inside the universe is structural.

**Picks: top 5 by composite among gate-passers.** Fixed N, purely mechanical, no discretionary override in v0 — a veto exercised selectively is retroactive curation, and a pick that blows up is record material. If fewer than five names pass all gates, all passers are taken and the shortfall disclosed. Ties break deterministically (higher CBOP sector percentile, then lexicographic FIGI): any reader can regenerate the pick list from config plus data with zero judgment calls. Qualitative judgment lives in the accompanying write-ups and the observation layer — not in the pick rule — until something graduates under §8.

## 8. Signal graduation and demotion

A signal moves from observation into the decision core only when three legs hold:

**(a) External evidence** — presence in the Chen-Zimmermann open-source replication corpus or ≥2 independent Tier 1–3 published studies, **and** no dedicated post-publication study documenting the signal's decay or disappearance.

**(b) Internal forward evidence** — measured on non-overlapping 12-month windows only (overlapping windows manufacture apparent evidence and never count):
- *Fast track* — signals with live external support (insider clusters, short interest, net payout): hypothesized sign in ≥2 non-overlapping windows. Disclosed honestly: two sign-agreements occur by chance 25% of the time; the internal leg is a consistency check and veto, not proof — the inferential weight sits on leg (a). Earliest possible graduation: ~24 months from first run.
- *Slow track* — signals with contested or absent external support (SUE, call tone, hiring velocity): hypothesized sign in 4 of 4 non-overlapping windows (6.25% chance rate) plus pooled economic materiality — roughly five years.
- *Event-style signals* additionally require ≥100 distinct flagged names cumulatively.

**Primary tests, pre-committed:** rank candidates — sign of the sector-neutralized top-minus-bottom-quintile forward excess spread per window (pooled Spearman IC and overlap-corrected statistics reported as supplementary disclosure only, never as the criterion). Gate candidates — sign of flagged-cohort mean excess versus universe per window.

**Demotion:** core factors are demoted only on mechanism break or data-integrity failure — never on trailing underperformance alone. Neither side of the factor-timing debate supports performance-chasing exits, and a rule that fires on drawdowns would have exited the value factor at its 2020 bottom.

**Review:** once per year at a fixed run, all six signals evaluated together, with the six-test family-wise context disclosed alongside any graduation.

## 9. Change protocol

Any change to the decision core, gates, universe, success metric, or this document: (1) config_version bump — the new git SHA appears in every subsequent row; (2) a written memo in the repo explaining what changed and why; (3) the prior composite shadow-tracked for ≥12 months after the change, so the record never silently forks. The pre-registered hypothesis texts and primary tests in §4 and §8 are never edited — superseded language is struck through and dated, not deleted.

## 10. Timestamping and verification

Every run's artifacts (and this document) are hashed and stamped via OpenTimestamps, anchoring existence-by-date in Bitcoin; receipts are committed to this repository and upgraded at the following run. Git commit dates alone are not tamper-evident — the OTS receipts are the proof layer. Independent verification requires a local Bitcoin node and is deliberately the skeptical reader's job; everything needed is in the repo.

## 11. Evidence basis (selected)

Universe/coverage: analyst-coverage and delisting-bias literature. Decision core: Ball, Gerakos, Linnainmaa & Nikolaev 2016 JFE (cash-based operating profitability, accruals subsumption); Ball et al. 2015 JFE; Gray & Vogel 2012 JPM and Loughran & Wellman 2011 JFQA (enterprise multiple); Cooper, Gulen & Schill 2008 JF (asset growth); Hong, Lim & Stein 2000 JF (momentum gate; loser continuation in low-coverage small caps); Asness, Porter & Stevens 2000 (within-industry ranking); Green, Hand & Soliman 2011 (accruals decay). Observation layer: Cohen, Malloy & Pomorski 2012 JF (opportunistic insiders); short-interest/days-to-cover literature; Boudoukh, Michaely, Richardson & Roberts 2007 JF (payout yield); Loughran & McDonald 2011 JF (tone dictionary); Martineau 2022 (PEAD disappearance — the disclosed negative prior); Belo et al. 2014 JPE (the hiring-velocity adversary). Graduation/inference: Chen & Zimmermann 2022 CFR (replication corpus); Boudoukh, Richardson & Whitelaw 2008 RFS (overlapping-window inference); Novy-Marx & Velikov 2016 RFS (rebalance frequency); Asness et al. 2017 JPM vs. Arnott et al. 2016 (factor-timing dispute, both conflict-flagged). Benchmark: Meketa independent small-cap benchmark study; SPDJI research (conflict-flagged); delisting conventions per Beaver, McNichols & Price.
