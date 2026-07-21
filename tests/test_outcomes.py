"""Corporate-action tests for the outcome module — synthetic prices,
hand-computed expected values, no network.

Two layers:
  unit_checks()        score_name() branch rules, one scenario at a time
  integration_checks() compute_outcomes() end-to-end over the permanent
                       fixture in tests/fixtures/outcome_actions/ — a
                       four-name public_screen.csv (run date 2025-06-13,
                       mirroring the backdated outcome fixture) plus a
                       corporate_actions.csv exercising every §5 branch,
                       both config horizons, excess/hit flow-through, and
                       the §6 pre-registered stats. The blank
                       value_per_share column doubles as a regression test
                       for the NaN-override bug (a blank CSV cell is NaN,
                       NaN is truthy, and must not hijack the override
                       path). Fixture inputs are copied to a temp dir
                       before scoring so the checked-in files are never
                       overwritten.

Run:  python -m tests.test_outcomes
"""
from __future__ import annotations

import datetime as dt
import pathlib
import shutil
import tempfile

import pandas as pd

from screener.outcomes import add_months, compute_outcomes, score_name

RUN = dt.date(2024, 1, 10)
END = dt.date(2025, 1, 10)

# benchmark: 200 at run date, 210 on 2024-06-01, 220 at horizon
BENCH = [(dt.date(2024, 1, 10), 200.0), (dt.date(2024, 6, 1), 210.0),
         (dt.date(2025, 1, 10), 220.0)]
BENCH_RET = 220 / 200 - 1                       # 0.10


def approx(a, b, label="value"):
    assert a is not None and abs(a - b) < 1e-9, f"{label}: got {a}, expected {b}"


def unit_checks() -> None:
    assert add_months(dt.date(2025, 6, 13), 12) == dt.date(2026, 6, 13)
    assert add_months(dt.date(2024, 8, 31), 6) == dt.date(2025, 2, 28)

    # regular: 100 -> 120, excess vs 10% benchmark
    s = score_name("REG", RUN, END,
                   [(RUN, 100.0), (END, 120.0)], BENCH, None)
    approx(s["ret"], 0.20)
    approx(s["excess"], 0.20 - BENCH_RET)
    assert s["return_basis"] == "regular"

    # acquisition at $60 cash on 2024-06-01 from $50 start; proceeds rolled
    # at the benchmark 210 -> 220: ret = 60 * (220/210) / 50 - 1
    s = score_name("ACQ", RUN, END,
                   [(RUN, 50.0), (dt.date(2024, 5, 30), 58.0)], BENCH,
                   {"action": "acquisition",
                    "effective_date": dt.date(2024, 6, 1),
                    "value_per_share": 60.0})
    approx(s["ret"], 60.0 * (220.0 / 210.0) / 50.0 - 1.0)
    assert s["return_basis"] == "acquisition_rolled_at_benchmark"

    # delist for cause with a final observable trade: 40 -> 20 = -50%
    s = score_name("DLST", RUN, END,
                   [(RUN, 40.0), (dt.date(2024, 3, 1), 20.0)], BENCH,
                   {"action": "delist_for_cause",
                    "effective_date": dt.date(2024, 3, 1)})
    approx(s["ret"], -0.50)
    assert s["return_basis"] == "delist_final_value"

    # delist for cause with no observable exit: -100%, disclosed
    s = score_name("GONE", RUN, END, [(RUN, 40.0)], BENCH,
                   {"action": "delist_for_cause",
                    "effective_date": dt.date(2024, 3, 1)})
    approx(s["ret"], -1.0)
    assert s["return_basis"] == "delist_no_exit_minus_100"

    # halt: last trade 90 from 100, stale-flagged
    s = score_name("HALT", RUN, END,
                   [(RUN, 100.0), (dt.date(2024, 9, 15), 90.0)], BENCH,
                   {"action": "halt", "effective_date": dt.date(2024, 9, 15)})
    approx(s["ret"], -0.10)
    assert s["return_basis"] == "halt_last_trade_stale"

    # early series end with NO classification: computed but loudly flagged
    s = score_name("MYST", RUN, END,
                   [(RUN, 100.0), (dt.date(2024, 10, 1), 80.0)], BENCH, None)
    approx(s["ret"], -0.20)
    assert s["return_basis"] == "early_end_unclassified"


# ---------------------------------------------------------------------------
# integration fixture: synthetic dividend-adjusted closes. Run date
# 2025-06-13 (Fri); horizon ends 2025-12-13 and 2026-06-13 are Saturdays, so
# anchors fall back to the prior Friday — the same calendar behavior the
# KALU hand-check exercised against live data.
SERIES = {
    "IJR":  [("2025-06-13", 100.0), ("2025-09-15", 105.0),
             ("2025-12-12", 110.0), ("2026-06-12", 120.0)],
    "ACQ":  [("2025-06-13", 50.0), ("2025-09-15", 60.0)],   # ends at deal close
    "DLST": [("2025-06-13", 20.0)],                          # start price only
    "SPIN": [("2025-06-13", 40.0), ("2025-12-12", 46.0), ("2026-06-12", 50.0)],
    "HALT": [("2025-06-13", 10.0), ("2025-10-01", 8.0)],     # trading stops Oct 1
}


class FakeProvider:
    def series(self, ticker: str, start: dt.date, end: dt.date):
        return [(dt.date.fromisoformat(d), px) for d, px in SERIES[ticker]
                if start <= dt.date.fromisoformat(d) <= end]


def integration_checks() -> None:
    fixture = pathlib.Path(__file__).resolve().parent / "fixtures" / "outcome_actions"
    run_dir = pathlib.Path(tempfile.mkdtemp(prefix="outcome_actions_"))
    for name in ("public_screen.csv", "corporate_actions.csv"):
        shutil.copyfile(fixture / name, run_dir / name)

    summary = compute_outcomes(run_dir, [6, 12], provider=FakeProvider())
    o6 = pd.read_csv(run_dir / "outcomes_6m.csv").set_index("ticker")
    o12 = pd.read_csv(run_dir / "outcomes_12m.csv").set_index("ticker")

    # benchmark legs: 110/100-1 and 120/100-1
    approx(o6["bench_ret_6m"].iloc[0], 0.10, "bench_ret_6m")
    approx(o12["bench_ret_12m"].iloc[0], 0.20, "bench_ret_12m")

    # (1) acquisition: deal value 60 at 2025-09-15 (benchmark 105), proceeds
    # rolled at the benchmark to each horizon, over start price 50
    approx(o6.loc["ACQ", "ret_6m"], 60 * (110 / 105) / 50 - 1, "ACQ ret_6m")
    approx(o6.loc["ACQ", "excess_6m"], 60 * (110 / 105) / 50 - 1 - 0.10,
           "ACQ excess_6m")
    approx(o12.loc["ACQ", "ret_12m"], 60 * (120 / 105) / 50 - 1, "ACQ ret_12m")
    approx(o12.loc["ACQ", "excess_12m"], 60 * (120 / 105) / 50 - 1 - 0.20,
           "ACQ excess_12m")
    assert o6.loc["ACQ", "return_basis"] == "acquisition_rolled_at_benchmark"
    assert o12.loc["ACQ", "return_basis"] == "acquisition_rolled_at_benchmark"
    assert bool(o12.loc["ACQ", "hit_12m"]) is True

    # (2) delist for cause, no observable exit: -100% at both horizons, and
    # the loss still nets against the benchmark in excess
    approx(o6.loc["DLST", "ret_6m"], -1.0, "DLST ret_6m")
    approx(o6.loc["DLST", "excess_6m"], -1.10, "DLST excess_6m")
    approx(o12.loc["DLST", "ret_12m"], -1.0, "DLST ret_12m")
    approx(o12.loc["DLST", "excess_12m"], -1.20, "DLST excess_12m")
    assert o6.loc["DLST", "return_basis"] == "delist_no_exit_minus_100"
    assert o12.loc["DLST", "return_basis"] == "delist_no_exit_minus_100"
    assert bool(o12.loc["DLST", "hit_12m"]) is False

    # (3) spinoff: dividend-adjusted parent series as combined-entity proxy
    approx(o6.loc["SPIN", "ret_6m"], 46 / 40 - 1, "SPIN ret_6m")
    approx(o12.loc["SPIN", "ret_12m"], 50 / 40 - 1, "SPIN ret_12m")
    approx(o12.loc["SPIN", "excess_12m"], 0.25 - 0.20, "SPIN excess_12m")
    assert o6.loc["SPIN", "return_basis"] == "spinoff_combined_as_held"
    assert o12.loc["SPIN", "return_basis"] == "spinoff_combined_as_held"
    assert bool(o12.loc["SPIN", "hit_12m"]) is True

    # (4) halt: last trade (8, on 2025-10-01) carried to both horizons
    approx(o6.loc["HALT", "ret_6m"], 8 / 10 - 1, "HALT ret_6m")
    approx(o12.loc["HALT", "ret_12m"], 8 / 10 - 1, "HALT ret_12m")
    approx(o6.loc["HALT", "excess_6m"], -0.30, "HALT excess_6m")
    approx(o12.loc["HALT", "excess_12m"], -0.40, "HALT excess_12m")
    assert o6.loc["HALT", "return_basis"] == "halt_last_trade_stale"
    assert o12.loc["HALT", "return_basis"] == "halt_last_trade_stale"
    assert bool(o12.loc["HALT", "hit_12m"]) is False

    # hit is defined only at the 12m primary horizon
    assert "hit_6m" not in o6.columns
    assert "hit_rate" not in summary["horizons"]["6m"]

    # §6 pre-registered stats over the four picks at 12m
    s12 = summary["horizons"]["12m"]
    acq_x = 60 * (120 / 105) / 50 - 1 - 0.20
    approx(s12["hit_rate"], 0.5, "hit_rate")
    approx(s12["mean_excess"], (acq_x - 1.20 + 0.05 - 0.40) / 4, "mean_excess")
    approx(s12["median_excess"], (-0.40 + 0.05) / 2, "median_excess")
    approx(s12["slugging"], ((acq_x + 0.05) / 2) / ((1.20 + 0.40) / 2), "slugging")


def main() -> None:
    unit_checks()
    print("unit: all score_name branch assertions passed")
    integration_checks()
    print("integration: all four §5 branches verified end-to-end via "
          "corporate_actions.csv (acquisition roll, delist -100%, spinoff, "
          "halt) + §6 stats + NaN-override regression")


if __name__ == "__main__":
    main()
