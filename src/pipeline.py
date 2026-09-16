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
from .validation import file_digest, load, provenance, validate_exports


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
    design["converted_users"] = converted
    design["baseline_days"] = 91
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
        transaction_diagnosis=load("transaction_diagnosis"),
        quality=load("quality"),
        audit=[
            dict(row, label="redacted") if row["section"] == "transaction_duplicates" else row
            for row in load("audit")
        ],
        product_coverage=load("product_coverage"),
    )
    summary["findings"] = findings(summary)
    overview = next(
        (json.loads(row["detail"]) for row in summary["audit"] if row["section"] == "overview"), {}
    )
    summary["overview"] = dict(
        **overview,
        validated_transactions=sum(row["transactions"] for row in daily),
        validated_revenue_usd=sum(row["revenue_usd"] for row in daily),
        purchase_sessions=sum(row["purchase_sessions"] for row in daily),
    )
    inputs = ROOT / "data/published/inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    for name in summary["provenance"]:
        shutil.copyfile(ROOT / "data/processed" / name, inputs / name)
    log_path = ROOT / "data/processed/query_log.jsonl"
    if log_path.exists():
        latest_jobs = {}
        for line in log_path.read_text(encoding="utf-8").splitlines():
            job = json.loads(line)
            latest_jobs[job["name"]] = job
        summary["warehouse_jobs"] = latest_jobs
    summary["sql_provenance"] = {
        str(path.relative_to(ROOT)).replace("\\", "/"): file_digest(path)
        for path in sorted((ROOT / "sql").rglob("*.sql"))
    }
    write_json(ROOT / "data/published/report.json", summary)
    # CSV exports are aggregate-only and reproduce the chart inputs.
    for name in ["daily", "funnel", "retention", "segments"]:
        pd.DataFrame(summary[name]).to_csv(ROOT / "data/published" / f"{name}.csv", index=False)


def findings(report):
    out = []
    f = sorted([r for r in report["funnel"] if r["grain"] == "ordered_sessions"], key=lambda r: r["stage"])
    if f and f[0]["reached"] and report["experiment"]["observed_bottleneck"]:
        out.append(
            dict(
                title=f"Largest drop-off: {report['experiment']['transition'].lower()}",
                evidence=f"{report['experiment']['observed_bottleneck']['reached']:,} of {report['experiment']['observed_bottleneck']['previous_reached']:,} eligible sessions progressed; {report['experiment']['observed_bottleneck']['dropoff_rate']:.1%} did not. End-to-end completion was {f[-1]['reached'] / f[0]['reached']:.1%}.",
                interpretation="This is the largest proportional loss in the observable sequence; it is not proof of avoidable UX friction.",
                action=report["experiment"]["product_change"] + " Validate event order before testing.",
                boundary="Descriptive sequence, not a causal effect.",
                sources=["inputs/mart_funnel.json", "experiment.observed_bottleneck"],
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
                evidence=f"Mobile {a['checkout_completion']:.2%}; desktop {b['checkout_completion']:.2%}. Difference {(a['checkout_completion'] - b['checkout_completion']) * 100:+.2f} percentage points.",
                interpretation="Wilson intervals and eligible counts are available in the aggregate download.",
                action="Do not prioritize mobile checkout based on an assumed deficit; test the larger observed funnel bottleneck first."
                if a["checkout_completion"] >= b["checkout_completion"]
                else "Investigate mobile composition and instrumentation before choosing a device-specific test.",
                boundary="Exploratory association; multiple segment comparisons are not confirmatory tests.",
                sources=["inputs/mart_segments.json", "segments"],
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
                sources=["inputs/mart_retention.json"],
            )
        )
    investigation = report.get("investigation", {})
    cases = investigation.get("cases", [])
    if cases:
        case = next((c for c in cases if c["dimension"] == "device"), cases[0])
        overall = investigation["overall"]
        current, baseline = overall["current"], overall["baseline"]
        out.insert(
            2,
            dict(
                title=f"A real conversion change on {investigation['date']}",
                evidence=f"Session conversion was {current['conversion']:.2%}, versus {baseline['conversion']:.2%} across prior matched weekdays. Device mix contributed {case['mix'] * 100:+.3f} pp; within-device rates {case['within'] * 100:+.3f} pp.",
                interpretation="The change remains visible against the two most recent matched weekdays; the full baseline includes holiday dates.",
                action="Review changes in traffic quality, product demand and instrumentation across devices. Do not attribute the change to a release without independent evidence.",
                boundary="Descriptive decomposition; no product incident or causal explanation is established.",
                sources=[
                    "inputs/mart_segments.json",
                    "inputs/mart_daily_product_metrics.json",
                    "investigation",
                ],
            ),
        )
    design = report["experiment"]
    if design.get("scenarios"):
        a, b = design["scenarios"]
        out.append(
            dict(
                title="A testable next product decision",
                evidence=f"The eligible-user baseline is {design['baseline']:.2%}. A {design['relative_mde']:.0%} relative MDE requires {a['per_arm']:,} users per arm at {a['power']:.0%} power (~{a['duration_days']} days), or {b['per_arm']:,} at {b['power']:.0%} (~{b['duration_days']} days).",
                interpretation="Duration uses observed eligible traffic and full weeks; holiday seasonality limits forecasts.",
                action=design["product_change"] + " Randomize users with persistent assignment.",
                boundary="Prospective design at two-sided 5% alpha and 50/50 allocation; no treatment result.",
                sources=["inputs/mart_experiment.json", "experiment"],
            )
        )
    return out[:5]


def monitor():
    path = ROOT / "data/published/report.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    if report["status"] != "verified":
        raise ValueError("Monitoring requires verified exports")
    report["alerts"] = detect(report["daily"])
    report["investigation"] = investigate(load("mart_segments"), report["alerts"])
    report["findings"] = findings(report)
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
    readme = ROOT / "README.md"
    if report["status"] == "verified" and readme.exists():
        text = readme.read_text(encoding="utf-8")
        start, end = "<!-- BEGIN GENERATED FINDINGS -->", "<!-- END GENERATED FINDINGS -->"
        if start in text and end in text:
            lines = [start, "", "## Verified findings", ""]
            for f in report["findings"]:
                lines += [
                    f"* **{f['title']}:** {f['evidence']} **Decision:** {f['action']} {f['boundary']}",
                    "",
                ]
            lines += [
                "Generated from [report.json](data/published/report.json); source aggregates and query hashes are preserved alongside it.",
                "",
                end,
            ]
            text = text[: text.index(start)] + "\n".join(lines) + text[text.index(end) + len(end) :]
            readme.write_text(text, encoding="utf-8")


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
