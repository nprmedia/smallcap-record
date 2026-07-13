"""SEC EDGAR: fundamentals (XBRL companyfacts), Form 4 insider activity,
filing-history seasoning, and an announced-acquisition heuristic.

Point-in-time discipline: every fact is filtered to `filed <= as_of`, and the
latest filing on or before as_of wins — values are as-known-at-run-date, so
restatements never leak backward (METHODOLOGY.md §5).

Known free-backend approximations (all disclosed in run_meta):
- total debt is the sum of whichever debt tags the filer reports; a filer
  using non-standard tags can understate debt (Sharadar is the real source).
- months_since_listing proxies from the earliest EDGAR filing date.
- announced_target is a filings heuristic: merger-proxy / tender-offer forms
  (DEFM14A, PREM14A, SC 14D9, ...) filed in the trailing 12 months.
"""
from __future__ import annotations

import datetime as dt
import statistics
import xml.etree.ElementTree as ET

# ---- XBRL tag lists, first usable wins ---------------------------------
EBIT_TAGS = ["OperatingIncomeLoss"]
DEP_TAGS = [
    "DepreciationDepletionAndAmortization",
    "DepreciationAmortizationAndAccretionNet",
    "DepreciationAndAmortization",
]
# when no combined D&A tag exists, sum whatever components are reported
DEP_COMPONENT_TAGS = [
    ["Depreciation"],
    ["AmortizationOfIntangibleAssets"],
]
REVENUE_TAGS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "SalesRevenueNet",
]
CASH_TAGS = [
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
]
ST_INVESTMENT_TAGS = ["ShortTermInvestments"]
# debt components summed if present (missing component counts as zero)
DEBT_COMPONENT_TAGS = [
    ["LongTermDebtNoncurrent", "LongTermDebt"],   # inner list: alternatives
    ["LongTermDebtCurrent"],
    ["ShortTermBorrowings", "CommercialPaper", "NotesPayableCurrent"],
    ["FinanceLeaseLiabilityNoncurrent"],
    ["FinanceLeaseLiabilityCurrent"],
]
ASSET_TAGS = ["Assets"]
EPS_TAGS = ["EarningsPerShareDiluted", "EarningsPerShareBasic"]
SHARES_TAGS = ["EntityCommonStockSharesOutstanding"]  # dei taxonomy

# cash-flow-statement working-capital lines for the CBOP accrual component
# (config ranks.factors cbop_a accruals_method: cash_flow_statement).
# accruals = ΔAR + ΔInventory + ΔPrepaid − ΔAP − ΔAccrued − ΔDeferredRev;
# XBRL IncreaseDecreaseIn* report increases as positive values.
ACCRUAL_ADD_TAGS = [
    ["IncreaseDecreaseInAccountsReceivable",
     "IncreaseDecreaseInReceivables",
     "IncreaseDecreaseInAccountsAndOtherReceivables",
     "IncreaseDecreaseInAccountsAndNotesReceivable",
     "IncreaseDecreaseInAccountsNotesAndLoansReceivable",
     "IncreaseDecreaseInContractReceivablesNet"],
    ["IncreaseDecreaseInInventories"],
    ["IncreaseDecreaseInPrepaidDeferredExpenseAndOtherAssets",
     "IncreaseDecreaseInPrepaidExpense",
     "IncreaseDecreaseInPrepaidExpensesOther"],
]
ACCRUAL_SUB_TAGS = [
    ["IncreaseDecreaseInAccountsPayable",
     "IncreaseDecreaseInAccountsPayableAndAccruedLiabilities",
     "IncreaseDecreaseInAccountsPayableTrade"],
    ["IncreaseDecreaseInAccruedLiabilities"],
    ["IncreaseDecreaseInContractWithCustomerLiability",
     "IncreaseDecreaseInDeferredRevenue"],
]
BUYBACK_TAGS = ["PaymentsForRepurchaseOfCommonStock"]
DIVIDEND_TAGS = ["PaymentsOfDividendsCommonStock", "PaymentsOfDividends"]
ISSUANCE_TAGS = ["ProceedsFromIssuanceOfCommonStock"]

ACQUISITION_FORMS = {"DEFM14A", "PREM14A", "SC 14D9", "SC14D9", "DEFM14C", "PREM14C"}


class Edgar:
    def __init__(self, session, cfg: dict):
        self.http = session
        self.cfg = cfg

    # ---- company directory ------------------------------------------------
    def ticker_directory(self) -> dict[str, dict]:
        """ticker -> {cik, name, exchange} from the SEC's exchange-tagged list."""
        data = self.http.get_json(self.cfg["tickers_url"])
        fields, rows = data["fields"], data["data"]
        out = {}
        for row in rows:
            rec = dict(zip(fields, row))
            out[str(rec["ticker"]).upper()] = {
                "cik": int(rec["cik"]),
                "name": rec["name"],
                "exchange": (rec.get("exchange") or "").upper(),
            }
        return out

    def companyfacts(self, cik: int) -> dict | None:
        return self.http.get_json(self.cfg["companyfacts_url"].format(cik=cik))

    def submissions(self, cik: int) -> dict | None:
        return self.http.get_json(self.cfg["submissions_url"].format(cik=cik))

    # ---- fundamentals -------------------------------------------------------
    def fundamentals(self, cik: int, as_of: dt.date) -> dict:
        out = {k: None for k in [
            "ebit_ttm_usd", "ebitda_ttm_usd", "net_debt_usd", "total_assets_usd",
            "asset_growth_yoy", "cbop_ttm_usd", "net_payout_ttm_usd",
            "revenue_ttm_usd", "shares_outstanding", "obs_sue_srw",
            "staleness_days"]}
        facts = self.companyfacts(cik)
        if not facts:
            return out

        ebit_ttm, latest_end = _ttm_any(facts, EBIT_TAGS, as_of)
        out["ebit_ttm_usd"] = ebit_ttm

        dep_ttm, _ = _ttm_any(facts, DEP_TAGS, as_of)
        if dep_ttm is None:
            # no combined D&A tag: sum reported components
            parts = [v for alternatives in DEP_COMPONENT_TAGS
                     for v in [_ttm_any(facts, alternatives, as_of)[0]]
                     if v is not None]
            dep_ttm = sum(parts) if parts else None
        if ebit_ttm is not None and dep_ttm is not None:
            out["ebitda_ttm_usd"] = ebit_ttm + dep_ttm

        out["revenue_ttm_usd"], _ = _ttm_any(facts, REVENUE_TAGS, as_of)

        cash, _ = _instant(facts, CASH_TAGS, as_of)
        sti, _ = _instant(facts, ST_INVESTMENT_TAGS, as_of)
        if cash is not None:
            debt = 0.0
            for alternatives in DEBT_COMPONENT_TAGS:
                val, _ = _instant(facts, alternatives, as_of)
                debt += val or 0.0
            out["net_debt_usd"] = debt - cash - (sti or 0.0)

        assets, assets_end = _instant(facts, ASSET_TAGS, as_of)
        out["total_assets_usd"] = assets
        if assets is not None and assets_end is not None:
            prior = _instant_near(facts, ASSET_TAGS, as_of,
                                  target=assets_end - dt.timedelta(days=365))
            if prior:
                out["asset_growth_yoy"] = assets / prior - 1.0

        # CBOP = EBIT_ttm − accruals_ttm (cash-flow-statement method).
        # Requires the receivables line at minimum; missing minor lines count 0.
        accruals, have_core = 0.0, False
        for i, alternatives in enumerate(ACCRUAL_ADD_TAGS):
            val, _ = _ttm_any(facts, alternatives, as_of)
            if val is not None:
                accruals += val
                if i == 0:
                    have_core = True
        for alternatives in ACCRUAL_SUB_TAGS:
            val, _ = _ttm_any(facts, alternatives, as_of)
            if val is not None:
                accruals -= val
        if ebit_ttm is not None and have_core:
            out["cbop_ttm_usd"] = ebit_ttm - accruals

        # net payout = completed buybacks + dividends − issuance (CF-sourced)
        buyback, _ = _ttm_any(facts, BUYBACK_TAGS, as_of)
        dividend, _ = _ttm_any(facts, DIVIDEND_TAGS, as_of)
        issuance, _ = _ttm_any(facts, ISSUANCE_TAGS, as_of)
        if any(v is not None for v in (buyback, dividend, issuance)):
            out["net_payout_ttm_usd"] = (
                (buyback or 0.0) + (dividend or 0.0) - (issuance or 0.0))

        out["shares_outstanding"], _ = _instant(
            facts, SHARES_TAGS, as_of, taxonomy="dei", unit="shares")

        out["obs_sue_srw"] = _sue_srw(
            _quarterly(facts, EPS_TAGS, as_of, unit="USD/shares"))

        if latest_end:
            out["staleness_days"] = (as_of - latest_end).days
        elif assets_end:
            out["staleness_days"] = (as_of - assets_end).days
        return out

    # ---- filing-history seasoning ------------------------------------------
    def seasoning(self, cik: int, as_of: dt.date) -> dict:
        subs = self.submissions(cik)
        if not subs:
            return {"months_since_listing": None, "quarters_filed": None}
        recent = subs.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        pairs = [(f, dt.date.fromisoformat(d)) for f, d in zip(forms, dates)
                 if d and dt.date.fromisoformat(d) <= as_of]
        quarters = sum(1 for f, _ in pairs if f in ("10-K", "10-Q"))
        earliest = min((d for _, d in pairs), default=None)
        # older filings live in archived segments; their date range extends
        # the (otherwise truncated) listing-age proxy
        for seg in subs.get("filings", {}).get("files", []):
            frm = seg.get("filingFrom")
            if frm:
                earliest = min(earliest or dt.date.max, dt.date.fromisoformat(frm))
        months = (as_of - earliest).days / 30.44 if earliest else None
        return {"months_since_listing": months, "quarters_filed": quarters}

    # ---- announced-acquisition heuristic -------------------------------------
    def announced_target(self, cik: int, as_of: dt.date) -> bool | None:
        subs = self.submissions(cik)
        if not subs:
            return None
        recent = subs.get("filings", {}).get("recent", {})
        window_start = as_of - dt.timedelta(days=365)
        for form, filed in zip(recent.get("form", []), recent.get("filingDate", [])):
            d = dt.date.fromisoformat(filed)
            if window_start <= d <= as_of and form.strip().upper() in ACQUISITION_FORMS:
                return True
        return False

    # ---- Form 4 insider activity ---------------------------------------------
    def insider_activity(self, cik: int, as_of: dt.date, window_days: int) -> dict:
        out = {"obs_n_insider_buyers_90d": None, "obs_insider_net_buy_usd_90d": None,
               "insider_od_buyers_90d": None, "insider_od_buy_usd_90d": None}
        subs = self.submissions(cik)
        if not subs:
            return out
        recent = subs.get("filings", {}).get("recent", {})
        window_start = as_of - dt.timedelta(days=window_days)
        form4s = [
            (recent["accessionNumber"][i], recent["primaryDocument"][i])
            for i, form in enumerate(recent.get("form", []))
            if form == "4"
            and window_start <= dt.date.fromisoformat(recent["filingDate"][i]) <= as_of
        ]
        buyers, od_buyers = set(), set()
        net_buy, od_buy = 0.0, 0.0
        for accession, primary_doc in form4s:
            xml = self._form4_xml(cik, accession, primary_doc)
            if xml is None:
                continue
            parsed = _parse_form4(xml, window_start, as_of)
            if parsed is None or parsed["is_plan"]:   # 10b5-1 plan trades excluded
                continue
            net_buy += parsed["buy_usd"] - parsed["sell_usd"]
            if parsed["buy_usd"] > 0:
                buyers.update(parsed["owner_ciks"])
                if parsed["is_officer_or_director"]:
                    od_buyers.update(parsed["owner_ciks"])
                    od_buy += parsed["buy_usd"]
        out["obs_n_insider_buyers_90d"] = len(buyers)
        out["obs_insider_net_buy_usd_90d"] = net_buy
        out["insider_od_buyers_90d"] = len(od_buyers)
        out["insider_od_buy_usd_90d"] = od_buy
        return out

    def _form4_xml(self, cik: int, accession: str, primary_doc: str) -> str | None:
        accn = accession.replace("-", "")
        doc = (primary_doc or "").split("/")[-1]
        if doc.endswith(".xml"):
            url = self.cfg["archives_url"].format(cik=cik, accession=accn, doc=doc)
            text = self.http.get_text(url)
            if text and text.lstrip().startswith("<"):
                return text
        # fallback: list the filing directory and take the first real .xml
        index = self.http.get_json(
            self.cfg["archives_url"].format(cik=cik, accession=accn, doc="index.json"))
        if not index:
            return None
        for item in index.get("directory", {}).get("item", []):
            name = item.get("name", "")
            if name.endswith(".xml") and not name.startswith("xsl"):
                return self.http.get_text(
                    self.cfg["archives_url"].format(cik=cik, accession=accn, doc=name))
        return None


# ============ XBRL helpers (point-in-time aware) ============

def _fact_rows(facts: dict, tag: str, as_of: dt.date, taxonomy: str, unit: str) -> list[dict]:
    rows = (facts.get("facts", {}).get(taxonomy, {}).get(tag, {})
            .get("units", {}).get(unit, []))
    iso = as_of.isoformat()
    return [r for r in rows if r.get("filed") and r["filed"] <= iso and r.get("val") is not None]


def _first_tag_with_data(facts, tags, as_of, taxonomy, unit):
    for tag in tags:
        rows = _fact_rows(facts, tag, as_of, taxonomy, unit)
        if rows:
            return rows
    return []


def _quarterly(facts: dict, tags: list[str], as_of: dt.date,
               taxonomy: str = "us-gaap", unit: str = "USD") -> dict[dt.date, float]:
    """Quarterly duration series, latest filing per period wins; Q4 derived
    from the annual figure minus the three interior quarters when needed."""
    rows = _first_tag_with_data(facts, tags, as_of, taxonomy, unit)
    by_period: dict[tuple[dt.date, dt.date], dict] = {}
    for r in rows:
        if not r.get("start"):
            continue
        key = (dt.date.fromisoformat(r["start"]), dt.date.fromisoformat(r["end"]))
        if key not in by_period or r["filed"] > by_period[key]["filed"]:
            by_period[key] = r

    quarters, annuals = {}, {}
    for (start, end), r in by_period.items():
        span = (end - start).days
        if 70 <= span <= 100:
            quarters[end] = float(r["val"])
        elif 330 <= span <= 400:
            annuals[(start, end)] = float(r["val"])
    for (start, end), annual_val in annuals.items():
        if end in quarters:
            continue
        interior = [v for e, v in quarters.items()
                    if start + dt.timedelta(days=60) < e < end - dt.timedelta(days=60)]
        if len(interior) == 3:
            quarters[end] = annual_val - sum(interior)
    return dict(sorted(quarters.items()))


def _all_durations(facts: dict, tags: list[str], as_of: dt.date,
                   taxonomy: str = "us-gaap", unit: str = "USD"
                   ) -> dict[tuple[dt.date, dt.date], float]:
    """All duration facts (any span), latest filing per period wins."""
    rows = _first_tag_with_data(facts, tags, as_of, taxonomy, unit)
    by_period: dict[tuple[dt.date, dt.date], dict] = {}
    for r in rows:
        if not r.get("start"):
            continue
        key = (dt.date.fromisoformat(r["start"]), dt.date.fromisoformat(r["end"]))
        if key not in by_period or r["filed"] > by_period[key]["filed"]:
            by_period[key] = r
    return {k: float(r["val"]) for k, r in by_period.items()}


def _ttm_any(facts: dict, tags: list[str], as_of: dt.date,
             unit: str = "USD") -> tuple[float | None, dt.date | None]:
    """TTM trying each tag until one yields a value (filers switch tags over
    time, so 'first tag with any data' can land on a stale series). Per tag,
    try discrete quarterly summation first, then the YTD-flow method."""
    for tag in tags:
        val, end = _ttm(_quarterly(facts, [tag], as_of, unit=unit))
        if val is not None:
            return val, end
        val, end = _flow_ttm(_all_durations(facts, [tag], as_of, unit=unit))
        if val is not None:
            return val, end
    return None, None


def _flow_ttm(durations: dict[tuple[dt.date, dt.date], float]
              ) -> tuple[float | None, dt.date | None]:
    """TTM for concepts reported as year-to-date cumulatives (3/6/9/12
    months), the cash-flow-statement convention.
    TTM = prior fiscal year + current YTD − prior-year matching YTD;
    a fresh full-year figure is used directly."""
    if not durations:
        return None, None
    latest_end = max(end for _, end in durations)
    # the most cumulative duration ending at the latest period end
    start, span_val = None, None
    for (s, e), v in durations.items():
        if e == latest_end and (start is None or s < start):
            start, span_val = s, v
    span = (latest_end - start).days
    if span >= 330:                       # already a full year
        return span_val, latest_end
    annual = prior_ytd = None
    for (s, e), v in durations.items():
        if 330 <= (e - s).days <= 400 and abs((e - (start - dt.timedelta(days=1))).days) <= 20:
            annual = v                    # fiscal year ending where the YTD starts
        if abs((e - (latest_end - dt.timedelta(days=365))).days) <= 25 \
                and abs((e - s).days - span) <= 25:
            prior_ytd = v                 # same-span YTD one year earlier
    if annual is None or prior_ytd is None:
        return None, latest_end
    return annual + span_val - prior_ytd, latest_end


def _ttm(quarters: dict[dt.date, float]) -> tuple[float | None, dt.date | None]:
    """Sum of the latest four quarters, if they actually span ~one year."""
    ends = sorted(quarters)
    if len(ends) < 4:
        return None, None
    last4 = ends[-4:]
    span = (last4[-1] - last4[0]).days
    if not 230 <= span <= 330:
        return None, None
    return sum(quarters[e] for e in last4), last4[-1]


def _instant(facts: dict, tags: list[str], as_of: dt.date,
             taxonomy: str = "us-gaap", unit: str = "USD"
             ) -> tuple[float | None, dt.date | None]:
    rows = _first_tag_with_data(facts, tags, as_of, taxonomy, unit)
    best = None
    for r in rows:
        if r.get("start"):
            continue  # duration fact, not instant
        end = dt.date.fromisoformat(r["end"])
        if end > as_of:
            continue
        if best is None or (end, r["filed"]) > (best[1], best[2]):
            best = (float(r["val"]), end, r["filed"])
    return (best[0], best[1]) if best else (None, None)


def _instant_near(facts, tags, as_of, target: dt.date,
                  tolerance_days: int = 60) -> float | None:
    rows = _first_tag_with_data(facts, tags, as_of, "us-gaap", "USD")
    best = None
    for r in rows:
        if r.get("start"):
            continue
        end = dt.date.fromisoformat(r["end"])
        gap = abs((end - target).days)
        if gap <= tolerance_days and (best is None or gap < best[1]):
            best = (float(r["val"]), gap)
    return best[0] if best else None


def _sue_srw(eps_quarters: dict[dt.date, float]) -> float | None:
    """Seasonal-random-walk earnings surprise scaled by its own volatility.
    Null until ~8 surprises (12 quarters of EPS) are computable — per config
    observation_layer sue_srw nulls_until_computable."""
    ends = sorted(eps_quarters)
    surprises = []
    for i, end in enumerate(ends):
        if i < 4:
            continue
        prior = ends[i - 4]
        if 300 <= (end - prior).days <= 430:   # same fiscal quarter last year
            surprises.append(eps_quarters[end] - eps_quarters[prior])
    if len(surprises) < 8:
        return None
    window = surprises[-8:]
    sigma = statistics.stdev(window)
    return window[-1] / sigma if sigma > 0 else None


# ============ Form 4 XML parsing ============

def _strip_ns(tag: str) -> str:
    return tag.split("}")[-1]


def _parse_form4(xml_text: str, window_start: dt.date, as_of: dt.date) -> dict | None:
    try:
        root = ET.fromstring(xml_text.encode("utf-8"))
    except ET.ParseError:
        return None

    def findall(node, name):
        return [el for el in node.iter() if _strip_ns(el.tag) == name]

    def text_of(node, name):
        els = findall(node, name)
        return els[0].text.strip() if els and els[0].text else None

    def value_of(node, name):
        # amounts and dates sit inside a <value> child, e.g.
        # <transactionShares><value>1000</value></transactionShares>
        els = findall(node, name)
        return text_of(els[0], "value") if els else None

    is_plan = (text_of(root, "aff10b5One") or "").lower() in ("1", "true")

    owner_ciks, is_od = set(), False
    for owner in findall(root, "reportingOwner"):
        cik_text = text_of(owner, "rptOwnerCik")
        if cik_text:
            owner_ciks.add(cik_text.lstrip("0"))
        if (text_of(owner, "isOfficer") or "").lower() in ("1", "true") \
           or (text_of(owner, "isDirector") or "").lower() in ("1", "true"):
            is_od = True

    buy_usd = sell_usd = 0.0
    for txn in findall(root, "nonDerivativeTransaction"):
        code = text_of(txn, "transactionCode")
        if code not in ("P", "S"):
            continue
        date_text = value_of(txn, "transactionDate") or text_of(txn, "transactionDate")
        if date_text:
            txn_date = dt.date.fromisoformat(date_text[:10])
            if not window_start <= txn_date <= as_of:
                continue
        try:
            shares = float(value_of(txn, "transactionShares") or 0)
            price = float(value_of(txn, "transactionPricePerShare") or 0)
        except ValueError:
            continue
        if code == "P":
            buy_usd += shares * price
        else:
            sell_usd += shares * price

    return {"is_plan": is_plan, "owner_ciks": owner_ciks,
            "is_officer_or_director": is_od,
            "buy_usd": buy_usd, "sell_usd": sell_usd}
