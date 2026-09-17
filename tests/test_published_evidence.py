"""Recompute published claims from the committed real aggregate query outputs."""

import json

import pandas as pd
import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.config import ROOT, SOURCE
from src.experimentation import power_plan
from src.funnels import segments
from src.pipeline import findings
from src.plotting import funnel_svg, retention_svg
from src.root_cause import investigate
from src.validation import file_digest


def report():
    result = json.loads((ROOT / "data/published/report.json").read_text(encoding="utf-8"))
    if result["status"] != "verified":
        pytest.skip("No published warehouse results yet")
    return result


def source(name):
    return json.loads((ROOT / "data/published/inputs" / f"{name}.json").read_text(encoding="utf-8"))


def test_published_inputs_and_sql_match_content_hashes():
    r = report()
    assert r["source"] == SOURCE
    for name, digest in r["provenance"].items():
        assert file_digest(ROOT / "data/published/inputs" / name) == digest, name
    for name, digest in r["sql_provenance"].items():
        assert file_digest(ROOT / name) == digest, name
    assert all(row["failures"] == 0 for row in source("quality"))
    assert r["warehouse_jobs"]["quality"]["job_id"]


def test_every_published_analysis_recomputes_from_real_inputs():
    r = report()
    assert r["daily"] == source("mart_daily_product_metrics")
    assert r["funnel"] == source("mart_funnel")
    assert r["segments"] == segments(source("mart_segments"))
    expected = investigate(source("mart_segments"), r["alerts"])
    assert r["investigation"] == expected
    stage = r["experiment"]["observed_bottleneck"]["stage"]
    eligible = [x for x in source("mart_experiment") if x["stage"] == stage]
    n = sum(x["eligible_users"] for x in eligible)
    k = sum(x["converted_users"] for x in eligible)
    plan = power_plan(k, n, n / 91)
    for key, value in plan.items():
        assert r["experiment"][key] == value
    assert r["findings"] == findings(r)
    assert 3 <= len(r["findings"]) <= 5
    assert all(f["sources"] for f in r["findings"])


def test_transaction_exclusions_reconcile_to_source_purchase_events():
    r = report()
    rows = source("transaction_diagnosis")
    assert (
        sum(x["source_purchase_events"] for x in rows) + r["overview"]["invalid_transaction_events"]
        == r["overview"]["purchase_events"]
    )
    accepted = [x for x in rows if x["status"] != "conflicting"]
    assert sum(x["transaction_ids"] for x in accepted) == r["overview"]["validated_transactions"]
    assert sum(x["sum_minimum_usd"] for x in accepted) == pytest.approx(
        r["overview"]["validated_revenue_usd"]
    )


def test_website_figures_csvs_and_readme_share_the_report(tmp_path):
    r = report()
    for name, function in [("funnel", funnel_svg), ("retention", retention_svg)]:
        file = tmp_path / f"{name}.svg"
        function(r[name], file)
        assert file.read_text(encoding="utf-8") == (ROOT / "site" / file.name).read_text(encoding="utf-8")
    for name in ["daily", "funnel", "retention", "segments"]:
        generated = tmp_path / f"{name}.csv"
        pd.DataFrame(r[name]).to_csv(generated, index=False)
        assert generated.read_text(encoding="utf-8") == (ROOT / "data/published" / generated.name).read_text(
            encoding="utf-8"
        )
    env = Environment(loader=FileSystemLoader(ROOT / "site"), autoescape=select_autoescape(["html"]))
    page = (ROOT / "site/index.html").read_text(encoding="utf-8")
    model_dir = ROOT / "data/published/model"
    model = {
        "metrics": json.loads((model_dir / "model_metrics.json").read_text(encoding="utf-8")),
        "metadata": json.loads((model_dir / "metadata.json").read_text(encoding="utf-8")),
        "calibration": pd.read_csv(model_dir / "model_calibration.csv").to_dict("records"),
        "health": pd.read_csv(model_dir / "model_health.csv").to_dict("records"),
        "drift": pd.read_csv(model_dir / "model_drift.csv").to_dict("records"),
        "segments": pd.read_csv(model_dir / "model_segment_metrics.csv").to_dict("records"),
    }
    execution = json.loads(
        (ROOT / "data/published/execution-evidence.json").read_text(encoding="utf-8-sig")
    )
    assert page == env.get_template("template.html").render(
        r=r, verified=True, m=model, execution=execution
    )
    assert "Awaiting data access" not in page
    assert "No numerical findings" not in page
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert all(f["evidence"] in readme for f in r["findings"])
