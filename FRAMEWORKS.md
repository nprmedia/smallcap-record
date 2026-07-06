# FRAMEWORKS.md
*Reference for how to evaluate evidence, structure comparisons, and select the right analysis pattern. Claude applies these without being prompted.*

---

## Evidence Quality Hierarchy

Apply when weighting claims against each other. Higher tiers override lower tiers when they conflict — unless the higher-tier study has material methodological flaws, in which case flag the flaw explicitly.

| Tier | Source Type | Weight | When to flag caution |
|------|-------------|--------|----------------------|
| 1 | Systematic reviews / meta-analyses of RCTs | Highest | Small N of underlying studies; high heterogeneity (I² > 75%) |
| 2 | Individual RCTs | High | Small sample; short follow-up; industry-funded |
| 3 | Prospective cohort studies | Moderate | Confounding; self-reported outcomes |
| 4 | Retrospective / observational studies | Low-moderate | Selection bias; recall bias; no causal claim justified |
| 5 | Expert consensus / clinical guidelines | Moderate (when Tier 1-3 is absent) | Check recency; check whether consensus is genuine or manufactured |
| 6 | Expert opinion / case studies | Low | Cannot generalise; flag explicitly |
| 7 | Secondary synthesis / journalism / commentary | Reference only | Trace to primary source before treating as evidence |

**Red flags to name explicitly:**
- Claim widely cited but traces to a single study (especially if small N or industry-funded)
- Statistical significance without practical significance (effect size matters)
- Correlation presented as causation without causal mechanism
- Publication bias likely (only positive results published in a domain)
- Replication failures in the field (social psychology, nutrition, economics — flag by default)

---

## Comparison Framework Selection

Choose the structure that matches the type of comparison being made.

### Option Comparison (A vs. B vs. C)
Use when evaluating discrete alternatives against a decision.

Structure:
1. State the decision this comparison feeds — what are you actually choosing?
2. Define the evaluation axes — the dimensions that determine which option wins under which conditions
3. Assess each option per axis — strongest case for each, not a balanced-but-vague overview
4. State the verdict conditionally — "Option A wins if [condition]; Option B wins if [condition]"
5. Name what's unknown that would change the verdict

Do not: collapse to a single winner when the answer is genuinely conditional. An unresolved tradeoff is a valid output.

### Claim Evaluation (Is X true?)
Use when assessing the validity of a specific assertion.

Structure:
1. Restate the claim precisely — vague claims cannot be evaluated
2. Identify what type of claim it is: empirical fact / causal claim / definitional / normative
3. What evidence would confirm or falsify it?
4. What does the evidence actually show? Apply evidence hierarchy above
5. Verdict with epistemic label: [ESTABLISHED] / [CONTESTED] / [LIKELY BUT UNCONFIRMED] / [UNSUPPORTED]

### Landscape Mapping (What's the state of X?)
Use when the goal is understanding a field, domain, or debate rather than resolving a specific question.

Structure:
1. Define the scope boundary — what's in and out
2. Major positions / schools of thought — strongest version of each
3. Where consensus exists vs. where genuine disagreement persists
4. Key open questions the field hasn't resolved
5. What would need to be true for the landscape to shift materially

### Causal Analysis (Why did X happen? / What causes Y?)
Use when investigating mechanisms, not just correlations.

Structure:
1. Distinguish correlation from causation — does the proposed mechanism have a causal pathway?
2. Identify confounders — what else could explain the observed pattern?
3. Apply Bradford Hill criteria where relevant: strength, consistency, specificity, temporality, biological gradient, plausibility, coherence, experiment, analogy
4. State confidence in the causal claim with evidence basis

---

## Research Fallacies — Flag These Proactively

**Finance-specific defaults (added 2026-07):**
- Post-publication decay: discount published factor/anomaly effects by default (~⅓–½ post-publication, McLean-Pontiff); publication date is itself evidence
- Overlapping windows: long-horizon results on overlapping windows with persistent regressors are overstated by construction (BRW 2008) — count non-overlapping windows only
- Replication check: Chen-Zimmermann corpus is the default reproduction test for cross-sectional predictors; it certifies the published evidence is real, not that it still works
- Finance COI flags: index vendors on their own indices; factor shops on factor-timing; academics consulting for the firms whose product class they study

These are patterns Claude should name when encountered in sources or in my framing, without being asked:

| Fallacy | Description |
|---------|-------------|
| **Motte and Bailey** | Claim shifts between a defensible (motte) and indefensible (bailey) version depending on challenge |
| **Galaxy-brained reasoning** | Chain of individually plausible steps reaching a conclusion most would find absurd — length of reasoning chain ≠ validity |
| **Base rate neglect** | Focusing on specifics of a case while ignoring the prior probability |
| **Survivorship bias** | Drawing conclusions from visible successes while ignoring failures (common in business case studies) |
| **Streetlight effect** | Studying what's easy to measure rather than what matters |
| **False precision** | Expressing uncertain estimates with misleading specificity |
| **Overfitting to narrative** | Constructing a coherent story that fits available facts but ignores alternative explanations that fit equally well |
| **Replication crisis domains** | Social priming, ego depletion, many nutrition claims, much macroeconomic forecasting — flag studies from these domains automatically |

---

## Scoping Discipline

Before researching, apply this check to avoid wasted effort:

1. **What exactly is the question?** State it in one sentence. If it can't be stated in one sentence, it's multiple questions — split them.
2. **What type of answer is needed?** Factual lookup / comparative analysis / causal explanation / landscape map / decision input — the type determines the method.
3. **What would a good answer look like?** Define the output before producing it.
4. **What's explicitly out of scope?** Name what adjacent questions this research is *not* trying to answer.

---

## Source Credibility by Domain

General heuristics for domain-specific source quality. Override with specific knowledge when available.

| Domain | High credibility | Treat with caution |
|--------|-----------------|-------------------|
| Medicine / health | Cochrane reviews, NEJM, Lancet, BMJ, NIH | Nutrition studies (confounding endemic); industry-funded pharma trials without independent replication |
| Finance / economics | Federal Reserve working papers, BIS, IMF, peer-reviewed journals | Investment bank research (conflict of interest); economic forecasts generally (poor track record) |
| Technology | Primary documentation, peer-reviewed CS conferences (NeurIPS, ICML, ACL), arXiv preprints with replication | Press releases; benchmark results without methodology disclosure |
| Business / strategy | Case studies as illustration only, not evidence; BCG/McKinsey for frameworks not facts | Consultant reports (selection bias in case selection) |
| Law / policy | Primary legal sources, official government publications | Advocacy group summaries (check the primary source) |
| Science (general) | Peer-reviewed journals in established fields; replicated findings | Pre-registration absent; p-values near 0.05 without effect size; single-lab findings |
