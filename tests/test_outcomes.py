"""Corporate-action rule test for the outcome module — synthetic prices,
hand-computed expected values, no network.

Run:  python -m tests.test_outcomes
"""
from __future__ import annotations

import datetime as dt

from screener.outcomes import add_months, score_name

RUN = dt.date(2024, 1, 10)
END = dt.date(2025, 1, 10)

# benchmark: 200 at run date, 210 on 2024-06-01, 220 at horizon
BENCH = [(dt.date(2024, 1, 10), 200.0), (dt.date(2024, 6, 1), 210.0),
         (dt.date(2025, 1, 10), 220.0)]
BENCH_RET = 220 / 200 - 1                       # 0.10


def approx(a, b):
    assert abs(a - b) < 1e-9, (a, b)


def main() -> None:
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

    print("all corporate-action assertions passed")


if __name__ == "__main__":
    main()
