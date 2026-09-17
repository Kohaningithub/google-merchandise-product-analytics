"""Isolated, parameterized replay shared by CLI and the existing Airflow DAG."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

from .config import CODE_ROOT, date_window

ANALYTICS = ["audit", "models", "validate", "export", "analyze", "monitor", "site"]
MODELING = [
    "build_model_features",
    "validate_model_features",
    "train_models",
    "evaluate_models",
    "calibration_checks",
    "segment_diagnostics",
    "model_health",
    "persist_model_results",
    "publish_model_report",
]


def scope(start, end):
    a, b = date_window(start, end)
    key = f"{a:%Y%m%d}_{b:%Y%m%d}"
    base = os.getenv("BQ_DATASET", "product_analytics")
    # Bounded stable namespace: same-window retries overwrite, other windows are isolated.
    dataset = f"{base}_replay_{key}"
    root = CODE_ROOT / "artifacts" / "replays" / key
    return root, dataset


def execute(step, start="2020-11-01", end="2021-01-31", include_model=False):
    root, dataset = scope(start, end)
    if step == "all":
        for stage in ANALYTICS[:-1] + (MODELING if include_model else []) + ["site"]:
            execute(stage, start, end, include_model)
        return
    if step not in ANALYTICS + MODELING + ["estimate"]:
        raise ValueError(f"Unknown stage {step}")
    root.mkdir(parents=True, exist_ok=True)
    (root / "site").mkdir(exist_ok=True)
    for name in ["template.html", "styles.css", "app.js"]:
        shutil.copyfile(CODE_ROOT / "site" / name, root / "site" / name)
    env = dict(
        os.environ, GA4_START_DATE=start, GA4_END_DATE=end, GA4_OUTPUT_ROOT=str(root), BQ_DATASET=dataset
    )
    # Child process prevents date/output state leaking between Airflow task executions.
    result = subprocess.run(
        [sys.executable, "-m", "src.replay", "--worker", step], cwd=CODE_ROOT, env=env, text=True
    )
    if result.returncode == 2:
        raise ValueError(f"Deterministic validation/configuration failure in {step}")
    result.check_returncode()


def worker(step):
    from .config import ROOT
    from .extract import Warehouse, render
    from .pipeline import run

    if step in ANALYTICS:
        run(step)
        return
    if step == "estimate":
        from google.cloud import bigquery

        wh = Warehouse()
        sql = render("stg_events", wh.project, wh.dataset)
        job = wh.client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False))
        estimate = dict(
            stage="stg_events",
            estimated_bytes=job.total_bytes_processed,
            note="Source scan only; downstream scans are estimated separately after materialization.",
        )
        print(json.dumps(estimate, indent=2))
        return
    from .modeling import (
        ModelQualityError,
        calibration_checks,
        evaluate,
        segments,
        train,
        validate_features,
        write_json,
    )

    output = ROOT / "model"
    output.mkdir(exist_ok=True)
    features = output / "features.parquet"
    if step in ["build_model_features", "validate_model_features"]:
        import pandas as pd

        wh = Warehouse()
        if step == "build_model_features":
            wh.model("mart_conversion_features")
        else:
            checks = wh.query(
                render("model_feature_quality", wh.project, wh.dataset), "model_feature_quality"
            )
            if not checks or any(row["failures"] for row in checks):
                raise ModelQualityError(f"Feature quality failed: {checks}")
            frame = pd.DataFrame(
                wh.query(
                    f"SELECT * FROM `{wh.project}.{wh.dataset}.mart_conversion_features` ORDER BY session_date,session_key",
                    "model_features_export",
                )
            )
            validate_features(frame)
            frame.to_parquet(features, index=False)
            write_json(
                output / "feature_provenance.json",
                dict(
                    source="BigQuery",
                    project=wh.project,
                    dataset=wh.dataset,
                    row_count=len(frame),
                    sha256=hashlib.sha256(features.read_bytes()).hexdigest(),
                ),
            )
    elif step == "train_models":
        # Invalidate prior downstream success before a new fit (retry cannot publish stale evidence).
        (output / "calibration_checks.json").unlink(missing_ok=True)
        (output / "model_report.html").unlink(missing_ok=True)
        train(features, output)
    elif step == "evaluate_models":
        evaluate(features, output)
    elif step == "calibration_checks":
        calibration_checks(output)
    elif step == "segment_diagnostics":
        segments(features, output)
    elif step == "model_health":
        from .model_health import health

        health(features, output)
    elif step == "persist_model_results":
        persist(output)
    elif step == "publish_model_report":
        from .model_report import publish

        publish(output)


def persist(output):
    """Replace same-window result tables; never append repeated predictions."""
    import pandas as pd
    from google.cloud import bigquery

    from .extract import Warehouse

    wh = Warehouse()
    tables = {
        "model_predictions": pd.read_parquet(output / "predictions.parquet"),
        "model_health": pd.read_csv(output / "model_health.csv"),
        "model_segment_metrics": pd.read_csv(output / "model_segment_metrics.csv"),
    }
    scores = json.loads((output / "model_metrics.json").read_text())
    tables["model_evaluation"] = pd.DataFrame([dict(model=k, **v) for k, v in scores["models"].items()])
    metadata = json.loads((output / "metadata.json").read_text())
    for name, frame in tables.items():
        frame["model_version"] = metadata["model_version"]
        config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
        wh.client.load_table_from_dataframe(
            frame, f"{wh.project}.{wh.dataset}.{name}", job_config=config
        ).result()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("step", choices=ANALYTICS + MODELING + ["all", "estimate"])
    parser.add_argument("--start-date", default="2020-11-01")
    parser.add_argument("--end-date", default="2021-01-31")
    parser.add_argument("--include-model", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        if args.worker:
            worker(args.step)
        else:
            execute(args.step, args.start_date, args.end_date, args.include_model)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        sys.exit(2)
