"""Canonical SQL is shared by the direct runner and generated dbt models."""

import hashlib
import json
import logging
import os
from datetime import UTC, datetime

from jinja2 import Environment, StrictUndefined

from .config import CODE_ROOT, EXPORTS, MODELS, ROOT, date_window, warehouse

LOG = logging.getLogger(__name__)


def model_path(name):
    matches = list((CODE_ROOT / "sql").glob(f"**/{name}.sql"))
    if len(matches) != 1:
        raise ValueError(f"Expected one canonical SQL file for {name}")
    return matches[0]


def render(name, project, dataset, start=None, end=None):
    a, b = date_window(start, end)
    sql = (
        Environment(undefined=StrictUndefined)
        .from_string(model_path(name).read_text(encoding="utf-8"))
        .render(ref=lambda model: f"`{project}.{dataset}.{model}`",
                var=lambda key, default=None: {"start_date": str(a), "end_date": str(b)}.get(key, default))
    )
    # Preserve canonical historical SQL and its published hashes.
    return (sql.replace("20201101", a.strftime("%Y%m%d"))
            .replace("20210131", b.strftime("%Y%m%d"))
            .replace("2020-11-01", str(a)).replace("2021-01-31", str(b))
            .replace("ABS(92-COUNT", f"ABS({(b-a).days + 1}-COUNT"))


class Warehouse:
    def __init__(self):
        from google.cloud import bigquery

        self.bq = bigquery
        self.project, self.dataset = warehouse()
        self.client = bigquery.Client(project=self.project, location=os.getenv("BQ_LOCATION", "US"))
        self.log_path = ROOT / "data/processed/query_log.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def query(self, sql, name, destination=None):
        bq = self.bq
        limit = int(os.getenv("BQ_MAX_BYTES", "5000000000"))
        dry = self.client.query(sql, job_config=bq.QueryJobConfig(dry_run=True, use_query_cache=False))
        estimate = dry.total_bytes_processed or 0
        LOG.info("Dry run %s: %s bytes (cap %s)", name, estimate, limit)
        if estimate > limit:
            raise ValueError(f"{name}: {estimate:,} bytes exceeds per-query cap {limit:,}")
        config = bq.QueryJobConfig(maximum_bytes_billed=limit, use_query_cache=True)
        if destination:
            config.destination = f"{self.project}.{self.dataset}.{destination}"
            config.write_disposition = "WRITE_TRUNCATE"
        job = self.client.query(sql, job_config=config)
        result = job.result()
        rows = [] if destination else list(result)
        record = dict(
            name=name,
            job_id=job.job_id,
            sql_sha256=hashlib.sha256(sql.encode()).hexdigest(),
            estimated_bytes=estimate,
            processed_bytes=job.total_bytes_processed,
            billed_bytes=job.total_bytes_billed,
            cache_hit=job.cache_hit,
            completed_at=datetime.now(UTC).isoformat(),
        )
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        LOG.info("%s: %s bytes", name, job.total_bytes_processed)
        return [dict(row) for row in rows]

    def setup(self):
        dataset = self.bq.Dataset(f"{self.project}.{self.dataset}")
        dataset.location = os.getenv("BQ_LOCATION", "US")
        dataset.default_table_expiration_ms = 60 * 24 * 60 * 60 * 1000
        self.client.create_dataset(dataset, exists_ok=True)

    def schema(self):
        table = self.client.get_table("bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_20201101")
        fields = [f.to_api_repr() for f in table.schema]
        save("schema", fields)

    def model(self, name):
        self.query(render(name, self.project, self.dataset), name, destination=name)

    def audit(self):
        self.setup()
        self.schema()
        self.model("stg_events")
        save("audit", self.query(render("audit", self.project, self.dataset), "audit"))
        save(
            "transaction_diagnosis",
            self.query(render("transaction_diagnosis", self.project, self.dataset), "transaction_diagnosis"),
        )

    def models(self):
        for name in MODELS[1:]:
            self.model(name)

    def validate(self):
        checks = self.query(render("quality", self.project, self.dataset), "quality")
        save("quality", checks)
        failures = [row for row in checks if row["failures"]]
        if failures:
            raise ValueError(f"Publication blocked by data quality: {failures}")

    def export(self):
        for name in EXPORTS:
            save(name, self.query(f"SELECT * FROM `{self.project}.{self.dataset}.{name}`", name + "_export"))
        save(
            "product_coverage",
            self.query(render("product_coverage", self.project, self.dataset), "product_coverage"),
        )


def save(name, rows):
    path = ROOT / "data/processed" / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, default=str, indent=2), encoding="utf-8")
