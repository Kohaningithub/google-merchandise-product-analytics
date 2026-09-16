"""Airflow 3.x. Static replay: manual schedule; never fake source freshness."""

import logging
from datetime import UTC, datetime, timedelta

from airflow.sdk import dag, task


@dag(
    schedule=None,
    start_date=datetime(2021, 2, 1, tzinfo=UTC),
    catchup=False,
    max_active_runs=1,
    tags=["ga4", "historical-replay"],
    default_args={"retries": 2, "retry_delay": timedelta(minutes=2)},
)
def product_analytics_pipeline():
    @task
    def execute(step):
        from src.pipeline import run

        logging.info("Starting historical GA4 task %s", step)
        run(step)
        return step

    audit = execute.override(task_id="extract_audit_staging")("audit")
    models = execute.override(task_id="intermediate_and_marts")("models")
    validation = execute.override(task_id="validate")("validate")
    export = execute.override(task_id="export_aggregates")("export")
    metrics = execute.override(task_id="metrics_and_experiment_design")("analyze")
    monitoring = execute.override(task_id="anomalies_and_diagnosis")("monitor")
    publish = execute.override(task_id="publish_artifacts")("site")
    audit >> models >> validation >> export >> metrics >> monitoring >> publish


product_analytics_pipeline()
