"""Fixed historical scope and bounded warehouse configuration."""

import os
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = ROOT
ROOT = Path(os.environ.get("GA4_OUTPUT_ROOT", ROOT)).resolve()
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


def date_window(start=None, end=None):
    a = date.fromisoformat(start or os.getenv("GA4_START_DATE", "2020-11-01"))
    b = date.fromisoformat(end or os.getenv("GA4_END_DATE", "2021-01-31"))
    if not date(2020, 11, 1) <= a < b <= date(2021, 1, 31):
        raise ValueError("Replay requires 2020-11-01 <= start_date < end_date <= 2021-01-31")
    return a, b


def warehouse():
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    dataset = os.environ.get("BQ_DATASET", "product_analytics")
    if not re.fullmatch(r"[a-z][a-z0-9-]{4,61}[a-z0-9]", project):
        raise ValueError("Set GOOGLE_CLOUD_PROJECT to your BigQuery query project ID. See README.")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", dataset):
        raise ValueError("Invalid BQ_DATASET")
    return project, dataset
