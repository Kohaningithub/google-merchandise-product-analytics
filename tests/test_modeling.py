"""Synthetic mechanics only; no fixture results enter the published case study."""

import json

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("sklearn")
from src.model_health import drift, health
from src.model_report import publish
from src.modeling import (
    BLOCKED,
    FEATURES,
    ModelQualityError,
    calibration_checks,
    calibration_table,
    evaluate,
    metrics,
    segments,
    split,
    train,
    validate_features,
    validate_predictions,
)


@pytest.fixture
def feature_frame():
    rng = np.random.default_rng(42)
    rows = []
    for day in pd.date_range("2020-11-02", "2021-01-30"):
        for i in range(40):
            seconds = int(rng.integers(0, 180))
            rows.append(
                dict(
                    session_key=f"{day.date()}-{i}",
                    session_date=str(day.date()),
                    prediction_ts=int(day.timestamp() * 1e6) + seconds * 1000000,
                    target=int(rng.random() < (0.15 + seconds / 600)),
                    device="mobile" if i % 2 else "desktop",
                    country="US",
                    source="google",
                    medium="organic",
                    visitor_type="new_proxy" if i % 3 else "returning_proxy",
                    day_of_week=day.dayofweek + 1,
                    hour_utc=0,
                    early_events=3,
                    early_page_views=1,
                    early_searches=i % 2,
                    seconds_to_view=seconds,
                    unique_products=1,
                    category_diversity=1,
                )
            )
    return pd.DataFrame(rows)


def test_contracts_reject_bad_features_and_leakage(feature_frame):
    validate_features(feature_frame)
    assert not BLOCKED.intersection(FEATURES)
    for field, value in [
        ("target", None),
        ("target", 2),
        ("early_events", -1),
        ("seconds_to_view", np.inf),
        ("hour_utc", 24),
        ("prediction_ts", 1),
    ]:
        bad = feature_frame.copy()
        bad[field] = bad[field].astype(float)
        bad.loc[0, field] = value
        with pytest.raises((ModelQualityError, ValueError)):
            validate_features(bad)
    with pytest.raises(ModelQualityError):
        validate_features(pd.concat([feature_frame, feature_frame.iloc[:1]]))
    with pytest.raises(ModelQualityError):
        validate_features(feature_frame.drop(columns="device"))
    with pytest.raises(ModelQualityError):
        validate_features(feature_frame.iloc[:0])


def test_temporal_partition_and_duplicate_guards(feature_frame):
    parts = split(feature_frame.sample(frac=1, random_state=2))
    assert parts["train"].session_date.max() < parts["calibration"].session_date.min()
    assert parts["selection"].session_date.max() < parts["test"].session_date.min()
    assert parts["calibration"].session_date.max() < parts["selection"].session_date.min()
    assert pd.concat(parts.values()).session_key.nunique() == len(feature_frame)
    with pytest.raises(ModelQualityError):
        split(feature_frame[feature_frame.session_date > "2020-12-31"])


def test_probability_metric_and_calibration_contracts():
    for bad in [[np.nan], [-0.1], [1.1], [0.2, 0.3]]:
        with pytest.raises(ModelQualityError):
            validate_predictions([1], bad)
    y = np.tile([0, 0, 0, 1], 250)
    p = np.full(len(y), 0.25)
    bins = calibration_table(y, p)
    assert len(bins) == 1
    assert bins[0]["row_count"] == len(y)
    score = metrics(y, p)
    assert score["brier_score"] == pytest.approx(0.1875)
    assert score["pr_auc"] == pytest.approx(0.25)
    assert score["top_decile_lift"] == 1
    assert score["calibration_error"] == 0
    assert metrics([0] * 200, [0.1] * 200)["pr_auc"] is None
    assert metrics([0, 1], [0.1, 0.2])["brier_score"] is None
    uneven = calibration_table(y, np.linspace(0, 1, len(y)))
    assert sum(r["row_count"] for r in uneven) == len(y)
    assert all(r["row_count"] >= 100 for r in uneven)


def test_drift_retains_outliers_and_unseen_categories(feature_frame):
    same = drift(feature_frame, feature_frame)
    assert all(r["value"] == pytest.approx(0) for r in same)
    changed = feature_frame.copy()
    changed["device"] = "unseen"
    changed["seconds_to_view"] = 999999
    rows = {r["feature"]: r for r in drift(feature_frame, changed)}
    assert rows["device"]["unseen_rate"] == 1
    assert rows["device"]["value"] == 1
    assert rows["seconds_to_view"]["value"] > 0


def test_model_lifecycle_and_deterministic_rerun(feature_frame, tmp_path):
    feature_path = tmp_path / "features.parquet"
    feature_frame.to_parquet(feature_path, index=False)
    output = tmp_path / "model"
    metadata = train(feature_path, output)
    evaluate(feature_path, output)
    calibration_checks(output)
    segments(feature_path, output)
    health(feature_path, output)
    publish(output)
    names = [
        "model_metrics.json",
        "model_calibration.csv",
        "model_segment_metrics.csv",
        "model_health.csv",
        "model_drift.csv",
        "model_pr.svg",
        "model_calibration.svg",
    ]
    original = {name: (output / name).read_bytes() for name in names}
    scores = json.loads((output / "model_metrics.json").read_text())
    assert scores["selected"] == metadata["selected"]
    for score in scores["models"].values():
        for key in ["roc_auc", "pr_auc", "brier_score", "calibration_error"]:
            assert 0 <= score[key] <= 1
        assert score["log_loss"] >= 0
    assert (output / "model_report.html").exists()
    train(feature_path, output)
    evaluate(feature_path, output)
    calibration_checks(output)
    segments(feature_path, output)
    health(feature_path, output)
    publish(output)
    for name in names:
        assert original[name] == (output / name).read_bytes(), name
    # Held-out labels cannot affect fitted parameters or selection.
    modified = feature_frame.copy()
    mask = modified.session_date >= "2021-01-01"
    modified.loc[mask, "target"] = 1 - modified.loc[mask, "target"]
    modified.to_parquet(feature_path, index=False)
    new = train(feature_path, tmp_path / "changed_test")
    assert new["selection_metrics"] == metadata["selection_metrics"]
    assert new["selected"] == metadata["selected"]
