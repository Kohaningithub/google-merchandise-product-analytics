"""Aggregate-only local report with the established dark/teal chart palette."""

import html
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import precision_recall_curve

from .modeling import ModelQualityError


def publish(output):
    output = Path(output)
    gate = json.loads((output / "calibration_checks.json").read_text())
    if gate.get("status") != "passed":
        raise ModelQualityError("Calibration integrity gate not passed")
    scores = json.loads((output / "model_metrics.json").read_text())
    calibration = pd.read_csv(output / "model_calibration.csv")
    health = pd.read_csv(output / "model_health.csv")
    segments = pd.read_csv(output / "model_segment_metrics.csv")
    predictions = pd.read_parquet(output / "predictions.parquet")
    colors = ["#64d9bd", "#ebc394", "#8bbdf5"]
    plt.rcParams.update(
        {
            "figure.facecolor": "#101e2b",
            "axes.facecolor": "#101e2b",
            "text.color": "#e5eef3",
            "axes.labelcolor": "#e5eef3",
            "xtick.color": "#a4b4c2",
            "ytick.color": "#a4b4c2",
            "axes.edgecolor": "#a4b4c2",
            "svg.hashsalt": "ga4-model",
        }
    )

    def save(fig, name):
        fig.tight_layout()
        fig.savefig(output / f"{name}.svg", metadata={"Date": None}, bbox_inches="tight")
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    for color, (name, group) in zip(colors, predictions.groupby("model", sort=True)):
        precision, recall, _ = precision_recall_curve(group.target, group.prediction)
        ax.plot(recall, precision, color=color, label=name)
    ax.axhline(predictions.target.mean(), color="#a4b4c2", linestyle="--", label="prevalence")
    ax.set(xlabel="Recall", ylabel="Precision", title="Final temporal test · ranking performance")
    ax.legend(facecolor="#101e2b", labelcolor="#e5eef3")
    save(fig, "model_pr")
    fig, ax = plt.subplots(figsize=(7, 4))
    for color, (name, group) in zip(colors, calibration.groupby("model", sort=True)):
        ax.plot(group.mean_prediction, group.conversion_rate, "o-", color=color, label=name)
    upper = max(calibration.mean_prediction.max(), calibration.conversion_rate.max()) * 1.1
    ax.plot([0, upper], [0, upper], "--", color="#a4b4c2")
    ax.set(
        xlabel="Mean predicted probability",
        ylabel="Observed conversion rate",
        title="Reliability · at least 100 sessions per bucket",
    )
    ax.legend(facecolor="#101e2b", labelcolor="#e5eef3")
    save(fig, "model_calibration")
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(health.window_end, health.mean_prediction, "o-", color=colors[0], label="prediction")
    ax.plot(health.window_end, health.conversion_rate, "o-", color=colors[1], label="observed")
    ax.plot(health.window_end, health.brier_score, "o-", color=colors[2], label="Brier")
    ax.set(title="Selected model · weekly health", ylabel="Probability / Brier score")
    ax.legend(facecolor="#101e2b", labelcolor="#e5eef3")
    save(fig, "model_health")
    device = segments[
        (segments.model == scores["selected"])
        & (segments.dimension == "device")
        & (segments.row_count >= 200)
    ]
    fig, ax = plt.subplots(figsize=(7, 4))
    if not device.empty:
        ax.bar(device.segment, device.mean_prediction, color=colors[0], label="predicted")
        ax.plot(device.segment, device.conversion_rate, "o", color=colors[1], label="observed")
        ax.legend(facecolor="#101e2b", labelcolor="#e5eef3")
    else:
        ax.text(0.5, 0.5, "Insufficient device volume", ha="center", transform=ax.transAxes)
    ax.set(title="Selected model · device calibration", ylabel="Conversion probability")
    save(fig, "model_segments")
    table = pd.DataFrame(scores["models"]).T.to_html(float_format=lambda v: f"{v:.4f}")
    page = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
    page += '<title>Conversion propensity evaluation</title><body style="background:#0b141d;color:#e5eef3;font:16px sans-serif;margin:3%">'
    page += "<h1>Conversion propensity · temporal evaluation</h1><p>Historical offline evaluation. Ranking lift is not causal impact.</p>"
    page += f'<p>Selected on December validation: {html.escape(scores["selected"])}</p><div style="overflow:auto">{table}</div>'
    for name in ["model_pr", "model_calibration", "model_health", "model_segments"]:
        page += f'<p><img style="max-width:100%" src="{name}.svg" alt="{name.replace("_", " ")}"></p>'
    page += "<p>Small groups suppress quality metrics. Full metadata, calibration buckets, segment and drift CSVs accompany this local report.</p></body></html>"
    (output / "model_report.html").write_text(page, encoding="utf-8")
