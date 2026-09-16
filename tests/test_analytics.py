"""Small synthetic edge cases are tests only; never published as observed results."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from src.anomaly_detection import MONITORS, detect
from src.experimentation import power_plan
from src.funnels import interval
from src.retention import eligible
from src.root_cause import decompose, investigate


def test_retention_boundary():
    assert eligible(date(2021, 1, 1), 30)
    assert not eligible(date(2021, 1, 2), 30)
    assert eligible(date(2021, 1, 30), 1)
    assert not eligible(date(2021, 1, 31), 1)


def test_decomposition_reconciles_with_entering_and_exiting_segments():
    a = pd.DataFrame({"segment": ["a", "b"], "sessions": [100, 300], "purchase_sessions": [10, 90]})
    b = pd.DataFrame({"segment": ["a", "c"], "sessions": [200, 100], "purchase_sessions": [60, 40]})
    result = decompose(a, b)
    assert result["delta"] == pytest.approx(100 / 300 - 100 / 400)
    assert result["mix"] + result["within"] == pytest.approx(result["delta"])
    entering = next(r for r in result["contributions"] if r["segment"] == "c")
    assert entering["within_effect"] == 0


def test_pure_mix_change():
    a = pd.DataFrame({"segment": ["a", "b"], "sessions": [100, 300], "purchase_sessions": [10, 90]})
    b = pd.DataFrame({"segment": ["a", "b"], "sessions": [300, 100], "purchase_sessions": [30, 30]})
    result = decompose(a, b)
    assert result["within"] == pytest.approx(0)
    assert result["mix"] == pytest.approx(-0.10)


def test_random_decompositions_reconcile():
    rng = np.random.default_rng(4)
    for _ in range(40):
        a = pd.DataFrame(
            {
                "segment": list("abc"),
                "sessions": rng.integers(50, 500, 3),
                "purchase_sessions": rng.integers(0, 50, 3),
            }
        )
        b = pd.DataFrame(
            {
                "segment": list("abc"),
                "sessions": rng.integers(50, 500, 3),
                "purchase_sessions": rng.integers(0, 50, 3),
            }
        )
        result = decompose(a, b)
        assert result["mix"] + result["within"] == pytest.approx(result["delta"], abs=1e-12)


def series():
    rows = []
    for i, day in enumerate(pd.date_range("2020-11-01", periods=45)):
        row = {"metric_date": day.date().isoformat(), "ordered_checkout_sessions": 200}
        row.update({m: 200 + (i % 7) * 5 for m in MONITORS})
        row["session_conversion"] = 0.1 + (i % 7) * 0.001
        row["checkout_completion"] = 0.5 + (i % 7) * 0.002
        rows.append(row)
    rows[30]["sessions"] = 2000
    return rows


def test_monitor_no_future_leakage_and_warmup():
    rows = series()
    partial = detect(rows[:31])
    future = detect(rows)
    assert partial == [a for a in future if a["date"] <= rows[30]["metric_date"]]
    assert any(a["date"] == rows[30]["metric_date"] and a["metric"] == "sessions" for a in partial)
    assert not detect(rows[:21])


def test_monitor_flat_history_and_low_volume():
    rows = series()
    for r in rows:
        for m in MONITORS:
            r[m] = 1
    assert not detect(rows)


def test_missing_revenue_not_alerted():
    rows = series()
    for r in rows:
        r["missing_revenue_transactions"] = 1
    rows[30]["revenue_usd"] = 100000
    assert not any(a["metric"] == "revenue_usd" for a in detect(rows))


def test_power_monotonicity_and_duration():
    plan = power_plan(200, 1000, 100)
    assert plan["baseline"] == 0.2
    a, b = plan["scenarios"]
    assert b["per_arm"] > a["per_arm"]
    for row in plan["scenarios"]:
        assert row["duration_days"] * 100 >= row["total"]
        assert row["duration_days"] % 7 == 0
    assert power_plan(200, 1000, 100, 0.05)["scenarios"][0]["per_arm"] > a["per_arm"]
    assert "scenarios" not in power_plan(100, 100, 20)


def test_wilson_boundary():
    assert interval(0, 0) == [None, None]
    low, high = interval(0, 100)
    assert low == pytest.approx(0, abs=1e-10)
    assert 0 < high < 0.1


def test_no_fake_investigation():
    rows = [{"metric_date": "2020-11-01", "dimension": "device", "segment": "mobile"}]
    assert investigate(rows, [])["cases"] == []
