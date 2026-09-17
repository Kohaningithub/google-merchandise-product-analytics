"""Airflow 3.x. Static replay: manual schedule; never fake source freshness."""

import logging
from datetime import UTC, datetime, timedelta

from airflow.exceptions import AirflowFailException, AirflowSkipException
from airflow.sdk import Param, dag, task


@dag(
    schedule=None,
    start_date=datetime(2021, 2, 1, tzinfo=UTC),
    catchup=False,
    max_active_runs=1,
    tags=["ga4", "historical-replay"],
    default_args={"retries": 2, "retry_delay": timedelta(minutes=2)},
    params={
        "start_date": Param("2020-11-01", type="string", format="date"),
        "end_date": Param("2021-01-31", type="string", format="date"),
        "include_model": Param(False, type="boolean"),
    },
)
def product_analytics_pipeline():
    @task
    def execute(step, params=None):
        from src.replay import MODELING
        from src.replay import execute as replay

        logging.info("Starting historical GA4 task %s", step)
        if step in MODELING and not params["include_model"]:
            raise AirflowSkipException("Model extension not requested")
        try:
            replay(step, params["start_date"], params["end_date"])
        except ValueError as error:
            raise AirflowFailException(str(error)) from error
        return step

    audit = execute.override(task_id="extract_audit_staging")("audit")
    models = execute.override(task_id="intermediate_and_marts")("models")
    validation = execute.override(task_id="validate")("validate")
    export = execute.override(task_id="export_aggregates")("export")
    metrics = execute.override(task_id="metrics_and_experiment_design")("analyze")
    monitoring = execute.override(task_id="anomalies_and_diagnosis")("monitor")
    publish = execute.override(task_id="publish_artifacts", trigger_rule="none_failed_min_one_success")("site")
    audit >> models >> validation >> export >> metrics >> monitoring >> publish
    features = execute.override(task_id="build_model_features")("build_model_features")
    feature_gate = execute.override(task_id="validate_model_features")("validate_model_features")
    train = execute.override(task_id="train_models")("train_models")
    evaluate = execute.override(task_id="evaluate_models")("evaluate_models")
    calibration = execute.override(task_id="calibration_checks")("calibration_checks")
    segments = execute.override(task_id="segment_diagnostics")("segment_diagnostics")
    health = execute.override(task_id="model_health")("model_health")
    persist = execute.override(task_id="persist_model_results")("persist_model_results")
    model_report = execute.override(task_id="publish_model_report")("publish_model_report")
    validation >> features >> feature_gate >> train >> evaluate >> calibration >> segments >> health >> persist
    persist >> model_report
    model_report >> publish
    # Both branches must pass before the replay's final publication gate succeeds.
    # When ML is not requested, the analytics chain still publishes normally.


dag = product_analytics_pipeline()
