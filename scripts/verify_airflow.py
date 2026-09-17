"""Real Airflow 3.1.7 import/parse; optional actual BigQuery-backed dag.test replay.

Run on Linux after airflow db migrate. --execute performs cloud work; estimate first.
No tasks are mocked, skipped artificially, or marked successful by this script.
"""

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from airflow.models.dagbag import DagBag

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--start-date", default="2021-01-15")
    parser.add_argument("--end-date", default="2021-01-21")
    parser.add_argument("--include-model", action="store_true")
    parser.add_argument("--repeat", action="store_true")
    parser.add_argument("--failure-check", action="store_true")
    args = parser.parse_args()
    bag = DagBag(dag_folder=str(ROOT / "airflow/dags"), include_examples=False)
    if bag.import_errors:
        raise RuntimeError(bag.import_errors)
    dag = bag.get_dag("product_analytics_pipeline")
    assert dag is not None and len(dag.tasks) == 16
    assert all(task.retries == 2 for task in dag.tasks)
    assert dag.get_task("publish_artifacts").upstream_task_ids == {
        "anomalies_and_diagnosis",
        "publish_model_report",
    }
    assert dag.get_task("train_models").upstream_task_ids == {"validate_model_features"}
    evidence = dict(runtime="Airflow 3.1.7", parsed=True, tasks=sorted(dag.task_ids), executions=[])
    conf = dict(start_date=args.start_date, end_date=args.end_date, include_model=args.include_model)
    if args.execute:
        from src.config import MODELS
        from src.replay import scope

        root, dataset = scope(args.start_date, args.end_date)
        signatures = []
        for _ in range(2 if args.repeat else 1):
            run = dag.test(run_conf=conf)
            states = {ti.task_id: str(ti.state) for ti in run.get_task_instances()}
            if str(run.state) != "success":
                raise RuntimeError(states)
            evidence["executions"].append(dict(run_id=run.run_id, state=str(run.state), tasks=states))
            # Verify full content/count stability, not only a stable task status.
            from google.cloud import bigquery

            client = bigquery.Client(project=os.environ["GOOGLE_CLOUD_PROJECT"])
            tables = MODELS + (
                ["mart_conversion_features", "model_predictions", "model_health"]
                if args.include_model
                else []
            )
            signature = {}
            for table in tables:
                sql = f"SELECT COUNT(*) AS n, BIT_XOR(FARM_FINGERPRINT(TO_JSON_STRING(t))) AS fingerprint FROM `{client.project}.{dataset}.{table}` t"
                dry = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True))
                cap = int(os.getenv("BQ_MAX_BYTES", "5000000000"))
                if dry.total_bytes_processed > cap:
                    raise ValueError("Replay verification exceeds byte cap")
                signature[table] = dict(
                    next(
                        iter(
                            client.query(
                                sql, job_config=bigquery.QueryJobConfig(maximum_bytes_billed=cap)
                            ).result()
                        )
                    )
                )
            signatures.append(signature)
        if args.repeat:
            assert signatures[0] == signatures[1], "Repeated replay changed table contents"
        evidence["table_signatures"] = signatures
        evidence["output"] = str(root)
    if args.failure_check:
        # Invalid chronology fails before any cloud call; downstream publication must not run.
        run = dag.test(run_conf=dict(start_date="2021-01-21", end_date="2021-01-15", include_model=True))
        states = {ti.task_id: str(ti.state) for ti in run.get_task_instances()}
        assert str(run.state) == "failed"
        assert states["extract_audit_staging"] == "failed"
        assert states["publish_artifacts"] == "upstream_failed"
        assert states["publish_model_report"] == "upstream_failed"
        evidence["failure_propagation"] = states
    evidence["checked_at"] = datetime.now(UTC).isoformat()
    output = ROOT / "artifacts" / "airflow-evidence.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
