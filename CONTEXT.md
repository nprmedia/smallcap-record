# CONTEXT.md
*Living document. Update as research progresses — move findings from Active to Settled, close questions when resolved, park inactive threads. Claude reads this before answering to avoid re-deriving established findings and to know what's genuinely open.*

---

## Active Research Questions
*Questions currently being investigated. Claude should treat these as open — challenge, probe, and surface gaps.*

<!-- RESEARCH ENTRY TEMPLATE — duplicate per question

### [Research Question]
- **Scope:** What exactly is being asked — and what is explicitly out of scope for this question
- **Why it matters:** The decision or purpose this research feeds into
- **Working hypothesis:** Current best guess, if any — [UNDER REVIEW]
- **Established so far:** What's been confirmed well enough to build on
- **Key tensions / open debates:** Where the evidence conflicts or the field disagrees
- **Gaps identified:** What isn't known, what's been poorly studied
- **Next:** What needs to be investigated to advance this question

-->

### [Research Question]
- **Scope:** 
- **Why it matters:** 
- **Working hypothesis:** 
- **Established so far:** 
- **Key tensions / open debates:** 
- **Gaps identified:** 
- **Next:** 

---

## Settled Findings
*Conclusions established well enough to treat as [ESTABLISHED] inputs to other questions. Claude should build on these, not re-litigate them — unless explicitly asked.*

| Finding | Confidence | Source basis | Date settled |

|Universe: US common stock, NYSE/Nasdaq only, $300M–$3B mkt cap, 3-mo median ADV ≥ $1M, ex-financials/REITs/pre-revenue-biotech/FPIs/LPs, ≥13 months since listing or business combination and ≥4 quarters of filings, one share class per issuer|ESTABLISHED|Coverage/dispersion literature; Section 16 FPI exemption (Form 4 dependency); delisting-bias handling|2026-07-02|

|Decision core: gates {EBIT_ttm > 0; net debt/EBITDA ≤ 3x (convention, disclosed); no announced acquisition target; 12-1 momentum > universe p10} → within-GICS-sector percentile ranks {CBOP/A, EBIT/EV, −asset growth} equal-weighted 1/3; CBOP accrual component via cash-flow-statement method|ESTABLISHED|Ball-Gerakos-Linnainmaa-Nikolaev 2016 JFE; Gray-Vogel 2012 + Loughran-Wellman 2011 (enterprise multiple family; EBIT variant is [INT], disclosed); Cooper-Gulen-Schill 2008; Hong-Lim-Stein 2000 (gate); Asness-Porter-Stevens 2000 (within-sector)|2026-07-02|

| Roster substitution log: GP/A + standalone accruals → CBOP/A | ESTABLISHED | Ball et al. 2015 (OP > GP); Ball et al. 2016 (CBOP subsumes accruals); Green-Hand-Soliman 2011 (standalone decay) | 2026-07-02 |

| Utilities retained in universe, resolved by within-sector ranking | Config-ratified [INT] | APS 2000 within-industry pricing | 2026-07-02 |

| Observation layer: {n_insider_buyers_90d + insider_net_buy_usd_90d (10b5-1 plan trades excluded; pre-2023 legacy-plan leak disclosed); si_pct_float + days_to_cover; net_payout_yield_ttm; sue_srw (nulls until computable); lm_neg_share + ΔQoQ; hiring_velocity_qoq (vertical only)} — raw continuous values, universe-wide; destinations pre-committed (gates: SI, tone; ranks: insider, payout, SUE, hiring); primary cluster test pre-registered: ≥2 distinct non-plan officer/director buyers, ≥$100K aggregate, 90d | ESTABLISHED  | Cohen-Malloy-Pomorski 2012 JF; SEC 10b5-1 amendments (Form 4/5 checkbox eff. Apr 2023, pre-Feb-2023 plan carve-out); short-interest/days-to-cover literature; Boudoukh et al. 2007; Loughran-McDonald 2011 | 2026-07-02 |

| Per-signal hypothesis texts logged with two label corrections: SUE [CONTESTED, leaning dead in modern US — Martineau]; hiring velocity contested-sign, labor-investment (−) adversary pre-registered against demand-led (+) thesis (Belo et al. 2014 vs. postings-informativeness work) | ESTABLISHED  | Session texts, 2026-07-02 | 2026-07-02 |

| Schema v0: row = (figi, run_date); identity figi+cik+ticker+config_version (git SHA); gate raws; sector-relative ranks + composite; obs__×6 raw; qual__score reserved; pick fields; outcome fields incl. return_basis; corp actions: value-at-event → benchmark-roll to horizon, no-observable-exit → −100% disclosed | ESTABLISHED  | Beaver-McNichols-Price delisting convention; Shumway imputation noted as historical-gap tool; session engineering | 2026-07-02 |

| Source pin: Sharadar SFA bundle @ dimension = as-reported, conditional ≤$100/mo at checkout (fallback EDGAR XBRL + Tiingo $30/mo, Apr-2026 pricing); benchmark series = IJR dividend-adjusted, ~6bp/yr drag disclosed (choice ratifies in D5); OTS stamp-per-run, upgrade-next-run, receipts committed | ESTABLISHED (config-ratified; Sharadar price UNVERIFIED pending checkout) | NDL SFA bundle listing; Tiingo public pricing; iShares prospectus 0.06% ER; OTS docs (free calendars, upgrade mechanics, alpha-format caveat) | 2026-07-02 |

| Success metric: 12m primary + 6m recorded, fixed horizon, no managed exits; benchmark = S&P 600 via IJR div-adjusted (D4 pin); hit = excess_12m > 0; pre-registered: hit rate, slugging, mean excess, median excess; no formal risk adjustment; breadth caveat + non-GIPS scope note disclosed | ESTABLISHED  | Meketa independent 22-yr study (~200bp excess, quality-tilt fit criterion); Jankovskis 2002 + Chen-Noronha-Singal 2006 (reconstitution drag); SPDJI research (COI-flagged); Mauboussin hit/slugging convention | 2026-07-03 |

| Labels logged: S&P 600 long-run premium ESTABLISHED (independent corroboration), trailing 3-yr/12-m sign REVERSED (low-quality rally regime) — reversal strengthens costly-signal logic; intake range updated to $1.2B–$8.0B (quarterly review, additions only); post-banding reconstitution drag OPEN; size mismatch ($300M–$1.2B slice below intake floor) disclosed not resolved | ESTABLISHED  | Session research pass, 2026-07-03 | 07-032026-07-03 |

| Graduation: legs — (a) external: CZ-corpus presence or ≥2 independent Tier 1–3 studies AND no documented-decay study; (b) internal: fast track {insider, SI, payout} ≥2 non-overlapping 12m windows sign-agreement (25% chance rate disclosed as consistency check, inferential weight on leg a), slow track {SUE, tone, hiring} ≥4/4 windows + pooled economic materiality (~5 yrs); event signals +≥100 distinct flagged names cumulative; (c) pre-written mechanism (D3 texts); primary tests: sector-neutral Q5−Q1 forward-excess sign (ranks), flagged-cohort mean excess sign (gates); pooled Spearman IC + NW-family stats supplementary only; earliest graduation ~24 months | ESTABLISHED  | Chen-Zimmermann 2022 CFR + openassetpricing corpus (98% reproduction, in-sample scope noted); HXZ 2020 vs JKP replication dispute [CONTESTED, absorbed by internal leg]; Boudoukh-Richardson-Whitelaw 2008 RFS (overlap inference); Britten-Jones-Neuberger-Nolte 2011 (supplementary corrections) | 2026-07-03 |

| Demotion: mechanism-break or data-integrity failure only, never trailing performance — no constituency in either factor-timing camp (anti-timing: hold, don't time; pro-timing: cheap factor is a buy); both camps COI-flagged; pro-timing evidence rests on persistent-regressor inference per BRW critique; any core change: config bump + memo + ≥12m shadow-track; review annual, all six jointly, family-wise disclosed | ESTABLISHED  | Asness-Chandra-Ilmanen-Israel 2017 JPM; Arnott-Beck-Kalesnik 2016 series; value-winter episode; session synthesis | 2026-07-03 |

| Cadence: quarterly runs Mar 20 / May 20 / Aug 20 / Nov 20, next-business-day roll; full runs only, no interim rows; picks = top-5 by composite among gate-passers, fixed N, no discretionary override, shortfall → all passers disclosed, tie-break = CBOP sector percentile then lexicographic figi; staleness_days logged per name; graduation windows non-overlapping 12m per D6 | ESTABLISHED  | Novy-Marx-Velikov 2016 RFS (frequency reduction as standard institutional mitigation, AQR quarterly-momentum example; <50%/mo-turnover anomalies retain significant net spreads; DFA consulting COI flagged); banding noted inapplicable (no standing portfolio); 2026 SEC filing calendars (10-K 60/75/90d, 10-Q 40/40/45d by tier) | 2026-07-03 |

| Labels logged: filer tier keys on public float at Q2-end with asymmetric entry/exit ($75M entry / $60M exit accelerated; $700M / $560M large-accelerated) plus SRC revenue carve-out — market cap does not determine tier, so the universe structurally contains 90-day filers; Mar 20 run carries stale non-accelerated annuals by design, disclosed; formation-lag conventions (FF July embargo, rdq designs) dominated structurally by run-time as-reported collection [INT] | ESTABLISHED  | SEC rules via 2026 law-firm calendars; session resea rch pass 2026-07-03 | 2026-07-03 |

| | [ESTABLISHED / HIGH CONFIDENCE / WORKING ASSUMPTION] | | |

---

## Active Debates
*Genuinely unresolved questions where the evidence is mixed or expert opinion is divided. Claude should represent both sides accurately and not force a resolution.*

| Question | Position A | Position B | State of evidence |
|----------|------------|------------|-------------------|
| | | | |

---

## Parked Questions
*Questions paused mid-investigation. Retain progress so research can resume without backtracking.*

- **[Question]** — Paused at: [where it was left] · Resume with: [next step]

---

## Out of Scope
*What this project is explicitly not investigating. Prevents drift.*

- 
