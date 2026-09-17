"""Fixed temporal conversion experiment. No test-set model selection."""

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler
from threadpoolctl import threadpool_limits

from .config import CODE_ROOT

CATEGORICAL = ["device", "country", "source", "medium", "visitor_type"]
NUMERIC = [
    "day_of_week",
    "hour_utc",
    "early_events",
    "early_page_views",
    "early_searches",
    "seconds_to_view",
    "unique_products",
    "category_diversity",
]
FEATURES = CATEGORICAL + NUMERIC
BLOCKED = {
    "target",
    "purchase_event",
    "purchase_ts",
    "transaction_id",
    "transactions",
    "revenue_usd",
    "session_end",
    "session_end_date",
    "checkout_ts",
    "added_cart",
    "began_checkout",
    "user_pseudo_id",
    "session_id",
    "session_key",
    "prediction_ts",
}
WINDOWS = {
    "train": ("2020-11-02", "2020-12-14"),
    "calibration": ("2020-12-15", "2020-12-23"),
    "selection": ("2020-12-24", "2020-12-31"),
    "test": ("2021-01-01", "2021-01-30"),
}
SEED = 42


class ModelQualityError(ValueError):
    """Deterministic contract failure: do not retry in Airflow."""


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False, default=str), encoding="utf-8"
    )


def validate_features(frame):
    required = set(FEATURES + ["session_key", "session_date", "target", "prediction_ts"])
    if frame.empty or not required.issubset(frame.columns):
        raise ModelQualityError(f"Empty feature mart or missing columns: {required - set(frame.columns)}")
    if frame[list(required)].isna().any().any() or frame.session_key.duplicated().any():
        raise ModelQualityError("Null required values or duplicate session keys")
    if not frame.target.isin([0, 1]).all():
        raise ModelQualityError("Target must be binary")
    if BLOCKED.intersection(FEATURES) or len(set(FEATURES)) != len(FEATURES):
        raise ModelQualityError("Blocked/duplicate model feature")
    x = frame[NUMERIC].to_numpy(dtype=float)
    if not np.isfinite(x).all() or (x < 0).any():
        raise ModelQualityError("Invalid numeric features")
    if not frame.day_of_week.between(1, 7).all() or not frame.hour_utc.between(0, 23).all():
        raise ModelQualityError("Invalid calendar features")
    if (frame.early_events < 1).any() or (
        frame.early_page_views + frame.early_searches > frame.early_events
    ).any():
        raise ModelQualityError("Invalid early event counts")
    dates = pd.to_datetime(frame.session_date, errors="raise")
    if not dates.between("2020-11-02", "2021-01-30").all():
        raise ModelQualityError("Session dates outside complete historical scope")
    # UTC event date can differ from property-local session date by one day.
    prediction_dates = pd.to_datetime(frame.prediction_ts, unit="us", utc=True).dt.tz_localize(None)
    if ((prediction_dates.dt.normalize() - dates).abs() > pd.Timedelta(days=1)).any():
        raise ModelQualityError("Prediction timestamp inconsistent with session date")


def split(frame):
    validate_features(frame)
    frame = frame.copy()
    frame["session_date"] = pd.to_datetime(frame.session_date).dt.strftime("%Y-%m-%d")
    frame = frame.sort_values(["session_date", "session_key"]).reset_index(drop=True)
    parts = {name: frame[frame.session_date.between(a, b)].copy() for name, (a, b) in WINDOWS.items()}
    for name, part in parts.items():
        if len(part) < 100 or part.target.value_counts().reindex([0, 1], fill_value=0).min() < 10:
            raise ModelQualityError(f"{name} needs >=100 rows and >=10 of each class")
    for before, after in zip(list(parts.values()), list(parts.values())[1:]):
        if before.session_date.max() >= after.session_date.min():
            raise ModelQualityError("Overlapping temporal splits")
    if sum(map(len, parts.values())) != len(frame):
        raise ModelQualityError("Unassigned dates")
    return parts


def validate_predictions(y, p):
    p = np.asarray(p, dtype=float)
    if p.ndim != 1 or len(p) != len(y) or not len(p) or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ModelQualityError("Invalid prediction count/probabilities")
    if not np.isin(y, [0, 1]).all():
        raise ModelQualityError("Invalid scoring labels")
    return p


def calibration_table(y, p, minimum=100):
    """Equal-frequency bins, keep ties together; merge small adjacent bins."""
    p = validate_predictions(y, p)
    frame = pd.DataFrame({"target": np.asarray(y), "prediction": p})
    if len(frame) < minimum:
        return []
    edges = np.unique(np.quantile(p, np.linspace(0, 1, min(10, len(p) // minimum) + 1)))
    frame["bucket"] = np.searchsorted(edges[1:-1], p, side="right")
    chunks, pending = [], []
    for _, group in frame.groupby("bucket", sort=True):
        pending.append(group)
        if sum(map(len, pending)) >= minimum:
            chunks.append(pd.concat(pending))
            pending = []
    if pending:
        if chunks:
            chunks[-1] = pd.concat([chunks[-1], *pending])
        else:
            chunks = [pd.concat(pending)]
    return [
        dict(
            bucket=i,
            row_count=len(g),
            lower=float(g.prediction.min()),
            upper=float(g.prediction.max()),
            mean_prediction=float(g.prediction.mean()),
            conversion_rate=float(g.target.mean()),
        )
        for i, g in enumerate(chunks)
    ]


def metrics(y, p, minimum=100):
    validate_predictions(y, p)
    y = np.asarray(y, dtype=int)
    p = validate_predictions(y, p)
    enough = len(y) >= minimum
    ranked = enough and min(np.sum(y == 0), np.sum(y == 1)) >= 10
    bins = calibration_table(y, p, minimum)
    result = dict(
        row_count=len(y),
        conversion_rate=float(y.mean()),
        mean_prediction=float(p.mean()),
        roc_auc=float(roc_auc_score(y, p)) if ranked else None,
        pr_auc=float(average_precision_score(y, p)) if ranked else None,
        brier_score=float(brier_score_loss(y, p)) if enough else None,
        log_loss=float(log_loss(y, p, labels=[0, 1])) if enough else None,
        calibration_error=sum(r["row_count"] * abs(r["mean_prediction"] - r["conversion_rate"]) for r in bins)
        / len(y)
        if bins
        else None,
        metric_status="reported" if ranked else "insufficient_rows_or_class_support",
    )
    for fraction, label in [(0.1, "decile"), (0.2, "quintile")]:
        # Include all ties at cutoff rather than obtaining arbitrary ranking lift.
        selected = p >= np.quantile(p, 1 - fraction)
        result[f"top_{label}_lift"] = float(y[selected].mean() / y.mean()) if ranked and y.mean() else None
        result[f"top_{label}_fraction"] = float(selected.mean())
    return result


def build_models():
    linear = ColumnTransformer(
        [
            ("category", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=20), CATEGORICAL),
            ("numeric", StandardScaler(), NUMERIC),
        ]
    )
    nonlinear = ColumnTransformer(
        [
            (
                "category",
                OrdinalEncoder(
                    handle_unknown="use_encoded_value",
                    unknown_value=np.nan,
                    max_categories=64,
                    encoded_missing_value=np.nan,
                ),
                CATEGORICAL,
            ),
            ("numeric", "passthrough", NUMERIC),
        ]
    )
    return {
        "logistic": Pipeline(
            [("features", linear), ("model", LogisticRegression(C=1, max_iter=1000, random_state=SEED))]
        ),
        "boosting": Pipeline(
            [
                ("features", nonlinear),
                (
                    "model",
                    HistGradientBoostingClassifier(
                        max_iter=150,
                        max_leaf_nodes=15,
                        l2_regularization=10,
                        learning_rate=0.05,
                        early_stopping=False,
                        categorical_features=list(range(len(CATEGORICAL))),
                        random_state=SEED,
                    ),
                ),
            ]
        ),
    }


def predict(bundle, name, frame):
    base_name = "boosting" if name == "boosting_sigmoid" else name
    p = bundle["models"][base_name].predict_proba(frame[FEATURES])[:, 1]
    if name == "boosting_sigmoid":
        logits = np.log(np.clip(p, 1e-8, 1 - 1e-8) / np.clip(1 - p, 1e-8, 1))
        p = bundle["calibrator"].predict_proba(logits.reshape(-1, 1))[:, 1]
    return validate_predictions(frame.target, p)


@threadpool_limits.wrap(limits=2)
def train(feature_path, output):
    output = Path(output)
    frame = pd.read_parquet(feature_path)
    parts = split(frame)
    models = build_models()
    for model in models.values():
        model.fit(parts["train"][FEATURES], parts["train"].target)
    bundle = dict(models=models)
    p = predict(bundle, "boosting", parts["calibration"])
    logits = np.log(np.clip(p, 1e-8, 1 - 1e-8) / np.clip(1 - p, 1e-8, 1))
    bundle["calibrator"] = LogisticRegression(C=1e6, random_state=SEED).fit(
        logits.reshape(-1, 1), parts["calibration"].target
    )
    selection = {
        name: metrics(parts["selection"].target, predict(bundle, name, parts["selection"]))
        for name in ["logistic", "boosting", "boosting_sigmoid"]
    }
    bundle["selected"] = min(
        selection, key=lambda name: (selection[name]["log_loss"], -selection[name]["pr_auc"])
    )
    digest = hashlib.sha256(Path(feature_path).read_bytes()).hexdigest()
    code_hash = hashlib.sha256(
        b"".join(p.read_bytes() for p in sorted((CODE_ROOT / "src").glob("*.py")))
    ).hexdigest()
    version = hashlib.sha256((digest + code_hash + sklearn.__version__).encode()).hexdigest()[:16]
    bundle["version"] = version
    bundle["feature_sha256"] = digest
    output.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, output / "model.joblib")
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=CODE_ROOT, capture_output=True, text=True)
    metadata = dict(
        model_version=version,
        feature_sha256=digest,
        code_sha256=code_hash,
        git_commit=revision.stdout.strip(),
        trained_at=datetime.now(UTC).isoformat(),
        sklearn_version=sklearn.__version__,
        features=FEATURES,
        seed=SEED,
        selected=bundle["selected"],
        selection_metrics=selection,
        windows={
            name: dict(
                start=a, end=b, row_count=len(parts[name]), conversion_rate=float(parts[name].target.mean())
            )
            for name, (a, b) in WINDOWS.items()
        },
        parameters={name: model.named_steps["model"].get_params() for name, model in models.items()},
    )
    write_json(output / "metadata.json", metadata)
    coefficients = models["logistic"].named_steps["model"].coef_[0]
    pd.DataFrame(
        {
            "feature": models["logistic"].named_steps["features"].get_feature_names_out(),
            "coefficient": coefficients,
        }
    ).to_csv(output / "model_coefficients.csv", index=False)
    importance = permutation_importance(
        models["boosting"],
        parts["selection"][FEATURES],
        parts["selection"].target,
        scoring="neg_log_loss",
        n_repeats=3,
        random_state=SEED,
        max_samples=min(5000, len(parts["selection"])),
    )
    pd.DataFrame(
        {"feature": FEATURES, "importance": importance.importances_mean, "std": importance.importances_std}
    ).to_csv(output / "model_importance.csv", index=False)
    return metadata


def load_run(feature_path, output):
    # Only load artifacts generated locally by this workflow; never untrusted joblib files.
    bundle = joblib.load(Path(output) / "model.joblib")
    if hashlib.sha256(Path(feature_path).read_bytes()).hexdigest() != bundle["feature_sha256"]:
        raise ModelQualityError("Feature input changed after training")
    return bundle, split(pd.read_parquet(feature_path))


@threadpool_limits.wrap(limits=2)
def evaluate(feature_path, output):
    output = Path(output)
    bundle, parts = load_run(feature_path, output)
    test = parts["test"]
    rows, calibration, predictions = {}, [], []
    for name in ["logistic", "boosting", "boosting_sigmoid"]:
        p = predict(bundle, name, test)
        rows[name] = metrics(test.target, p)
        calibration.extend(dict(model=name, **r) for r in calibration_table(test.target, p))
        pred = test[["session_key", "session_date", "target"]].copy()
        pred["model"], pred["model_version"], pred["prediction"] = name, bundle["version"], p
        predictions.append(pred)
    write_json(output / "model_metrics.json", dict(selected=bundle["selected"], models=rows))
    pd.DataFrame(calibration).to_csv(output / "model_calibration.csv", index=False)
    pd.concat(predictions).to_parquet(output / "predictions.parquet", index=False)


def calibration_checks(output):
    output = Path(output)
    table = pd.read_csv(output / "model_calibration.csv")
    scores = json.loads((output / "model_metrics.json").read_text())
    for name, score in scores["models"].items():
        rows = table[table.model == name]
        if rows.empty or (rows.row_count < 100).any() or rows.row_count.sum() != score["row_count"]:
            raise ModelQualityError("Calibration bins do not reconcile")
        for column in ["mean_prediction", "conversion_rate"]:
            if not rows[column].between(0, 1).all():
                raise ModelQualityError("Invalid calibration values")
        if not np.isclose(np.average(rows.mean_prediction, weights=rows.row_count), score["mean_prediction"]):
            raise ModelQualityError("Calibration means do not reconcile")
        if not np.isclose(np.average(rows.conversion_rate, weights=rows.row_count), score["conversion_rate"]):
            raise ModelQualityError("Calibration outcomes do not reconcile")
    # Quality checks validate the report; poor calibration is reported, never hidden.
    write_json(output / "calibration_checks.json", dict(status="passed", models=len(scores["models"])))


@threadpool_limits.wrap(limits=2)
def segments(feature_path, output):
    output = Path(output)
    bundle, parts = load_run(feature_path, output)
    test = parts["test"].copy()
    rows = []
    for name in ["logistic", "boosting", "boosting_sigmoid"]:
        test["prediction"] = predict(bundle, name, test)
        for dimension in CATEGORICAL:
            for segment, group in test.groupby(dimension, sort=True):
                rows.append(
                    dict(
                        model=name,
                        dimension=dimension,
                        segment=segment,
                        **metrics(group.target, group.prediction, minimum=200),
                    )
                )
    pd.DataFrame(rows).to_csv(output / "model_segment_metrics.csv", index=False)
