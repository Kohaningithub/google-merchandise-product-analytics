import ast
import json
import subprocess
import sys

import sqlglot

from src.config import MODELS, ROOT
from src.extract import render


def test_all_bigquery_sql_parses():
    for path in (ROOT / "sql").rglob("*.sql"):
        sql = render(path.stem, "sample-project", "product_analytics")
        assert sqlglot.parse_one(sql, read="bigquery") is not None, path.name


def test_dbt_canonical_sync():
    subprocess.run([sys.executable, str(ROOT / "scripts/sync_dbt.py"), "--check"], check=True)


def test_raw_scan_is_bounded_and_not_repeated():
    raw = render("stg_events", "sample-project", "product_analytics")
    assert "_TABLE_SUFFIX BETWEEN '20201101' AND '20210131'" in raw
    for model in MODELS[1:]:
        assert "events_*" not in render(model, "sample-project", "product_analytics")


def test_airflow_syntax_and_boundaries():
    source = (ROOT / "airflow/dags/product_analytics_pipeline.py").read_text(encoding="utf-8")
    ast.parse(source)
    assert "schedule=None" in source.replace(" ", "")
    assert "audit >> models >> validation >> export >> metrics >> monitoring >> publish" in source


def test_site_artifact_and_number_contract():
    report = json.loads((ROOT / "data/published/report.json").read_text(encoding="utf-8"))
    assert json.loads((ROOT / "site/report.json").read_text(encoding="utf-8")) == report
    page = (ROOT / "site/index.html").read_text(encoding="utf-8")
    if report["status"] != "verified":
        assert "No numerical findings are published yet." in page
        assert "No incident has been asserted." in page
        assert not report["findings"]
        assert "funnel.svg" not in page
    else:
        assert report["provenance"]
        for finding in report["findings"]:
            assert finding["evidence"] in page


def test_no_secrets_in_project():
    for path in ROOT.rglob("*.json"):
        if any(part in [".venv", "node_modules"] for part in path.parts):
            continue
        assert '"private_key"' not in path.read_text(encoding="utf-8")
