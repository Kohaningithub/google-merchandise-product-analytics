"""CLI and Airflow share these idempotent historical task boundaries."""

import argparse
import json
import logging
import shutil
from datetime import UTC, datetime

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .anomaly_detection import detect
from .config import END, ROOT, SOURCE, START
from .experimentation import power_plan
from .extract import Warehouse
from .funnels import segments
from .metrics import METRICS
from .plotting import funnel_svg, retention_svg
from .retention import summarize
from .root_cause import investigate
from .validation import load, provenance, validate_exports


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False, default=str), encoding="utf-8")


def analyze():
    validate_exports()
    daily = load("mart_daily_product_metrics")
    experiment = load("mart_experiment")
    funnel = load("mart_funnel")
    ordered = sorted([r for r in funnel if r["grain"] == "ordered_sessions"], key=lambda r: r["stage"])
    transitions = [r for r in ordered[1:] if r["previous_reached"] >= 100]
    bottleneck = max(transitions, key=lambda r: r["dropoff_rate"]) if transitions else None
    chosen_stage = bottleneck["stage"] if bottleneck else None
    eligible_rows = [r for r in experiment if r["stage"] == chosen_stage]
    users = sum(r["eligible_users"] for r in eligible_rows)
    converted = sum(r["converted_users"] for r in eligible_rows)
    design = power_plan(converted, users, users / 91)
    design["observed_bottleneck"] = bottleneck
    hypotheses = {
        2: ("Product view to cart", "Clarify availability and the add-to-cart action on product pages."),
        3: ("Cart to checkout", "Make checkout entry and delivery-cost expectations clearer in the cart."),
        4: ("Checkout to purchase", "Simplify checkout form guidance and validation messages."),
    }
    design["transition"], design["product_change"] = hypotheses.get(
        chosen_stage, ("Not selected", "Insufficient observed stage volume.")
    )
    design["decision"] = (
        "Investigate the largest observed ordered-session dropoff; user-level power planning uses a separately aligned eligibility baseline."
    )
    summary = dict(
        status="verified",
        generated_at=datetime.now(UTC).isoformat(),
        source=SOURCE,
        start=START,
        end=END,
        provenance=provenance(),
        metrics=METRICS,
        daily=daily,
        funnel=funnel,
        segments=segments(load("mart_segments")),
        retention=summarize(load("mart_retention")),
        experiment=design,
        audit=[
            dict(row, label="redacted") if row["section"] == "transaction_duplicates" else row
            for row in load("audit")
        ],
        product_coverage=load("product_coverage"),
    )
    summary["findings"] = findings(summary)
    write_json(ROOT / "data/published/report.json", summary)
    # CSV exports are aggregate-only and reproduce the chart inputs.
    for name in ["daily", "funnel", "retention", "segments"]:
        pd.DataFrame(summary[name]).to_csv(ROOT / "data/published" / f"{name}.csv", index=False)


def findings(report):
    out = []
    f = sorted([r for r in report["funnel"] if r["grain"] == "ordered_sessions"], key=lambda r: r["stage"])
    if f and f[0]["reached"]:
        out.append(
            dict(
                title="Observable end-to-end funnel",
                evidence=f"{f[-1]['reached']:,} of {f[0]['reached']:,} product-view sessions reached all ordered stages ({f[-1]['reached'] / f[0]['reached']:.1%}).",
                interpretation="Missing and tied event order can undercount complete journeys.",
                action="Audit stage instrumentation before treating dropoff as UX friction.",
                boundary="Descriptive sequence, not a causal effect.",
            )
        )
    devices = {
        r["segment"]: r
        for r in report["segments"]
        if r["dimension"] == "device" and r["eligible_for_comparison"]
    }
    if "mobile" in devices and "desktop" in devices:
        a, b = devices["mobile"], devices["desktop"]
        out.append(
            dict(
                title="Device checkout comparison",
                evidence=f"Mobile {a['checkout_completion']:.1%}; desktop {b['checkout_completion']:.1%}. Difference {(a['checkout_completion'] - b['checkout_completion']) * 100:+.1f} percentage points.",
                interpretation="Wilson intervals and eligible counts are available in the aggregate download.",
                action="Review composition and instrumentation before prioritizing a device-specific test.",
                boundary="Exploratory association; multiple segment comparisons are not confirmatory tests.",
            )
        )
    cohorts = [r for r in report["retention"] if r["dimension"] == "all" and r["horizon"] == 7]
    n, k = sum(r["eligible_users"] for r in cohorts), sum(r["returned_users"] for r in cohorts)
    if n:
        out.append(
            dict(
                title="Return on the seventh day",
                evidence=f"{k:,} of {n:,} eligible first-observed users returned on exact D7 ({k / n:.1%}).",
                interpretation="This is browser-level return behavior, not signup retention.",
                action="Compare mature cohorts and first-session behavior before planning retention interventions.",
                boundary="No claim that carting or purchasing causes return.",
            )
        )
    return out


def monitor():
    path = ROOT / "data/published/report.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    if report["status"] != "verified":
        raise ValueError("Monitoring requires verified exports")
    report["alerts"] = detect(report["daily"])
    report["investigation"] = investigate(load("mart_segments"), report["alerts"])
    write_json(path, report)


def site():
    path = ROOT / "data/published/report.json"
    if not path.exists():
        write_json(
            path,
            dict(
                status="awaiting_bigquery",
                source=SOURCE,
                start=START,
                end=END,
                findings=[],
                metrics=METRICS,
                provenance={},
                reason="BigQuery application-default credentials and a query project are unavailable. No observed metrics have been generated.",
            ),
        )
    report = json.loads(path.read_text(encoding="utf-8"))
    if report["status"] == "verified":
        if (ROOT / "data/processed/quality.json").exists() and report["provenance"] != provenance():
            raise ValueError("Exports changed after analysis. Re-run analyze and monitor.")
        if "alerts" not in report:
            raise ValueError("Run monitoring before publishing")
        for name, function in [("funnel", funnel_svg), ("retention", retention_svg)]:
            function(report[name], ROOT / "site" / f"{name}.svg")
    env = Environment(loader=FileSystemLoader(ROOT / "site"), autoescape=select_autoescape(["html"]))
    html = env.get_template("template.html").render(r=report, verified=report["status"] == "verified")
    (ROOT / "site/index.html").write_text(html, encoding="utf-8")
    shutil.copyfile(path, ROOT / "site/report.json")
    for csv in (ROOT / "data/published").glob("*.csv"):
        shutil.copyfile(csv, ROOT / "site" / csv.name)


def run(command):
    if command == "all":
        for step in ["audit", "models", "validate", "export", "analyze", "monitor", "site"]:
            run(step)
    elif command in ["audit", "models", "validate", "export"]:
        getattr(Warehouse(), command)()
    else:
        {"analyze": analyze, "monitor": monitor, "site": site}[command]()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=["audit", "models", "validate", "export", "analyze", "monitor", "site", "all"]
    )
    run(parser.parse_args().command)
