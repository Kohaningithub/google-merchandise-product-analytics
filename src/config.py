"""Fixed historical scope and bounded warehouse configuration."""

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*"
START, END = "20201101", "20210131"
MODELS = [
    "stg_events",
    "fct_purchases",
    "int_sessions",
    "int_users",
    "mart_daily_product_metrics",
    "mart_funnel",
    "mart_retention",
    "mart_segments",
    "mart_experiment",
]
EXPORTS = MODELS[4:]


def warehouse():
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    dataset = os.environ.get("BQ_DATASET", "product_analytics")
    if not re.fullmatch(r"[a-z][a-z0-9-]{4,61}[a-z0-9]", project):
        raise ValueError("Set GOOGLE_CLOUD_PROJECT to your BigQuery query project ID. See README.")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", dataset):
        raise ValueError("Invalid BQ_DATASET")
    return project, dataset
