"""Date plumbing and materialization behavior; no claims of cloud execution."""

from types import SimpleNamespace

import pytest

from src.config import date_window
from src.extract import Warehouse, render
from src.replay import scope


def test_cli_publication_waits_for_the_model_branch(monkeypatch):
    from src import replay

    execute = replay.execute
    stages = []

    def stage(step, *args):
        stages.append(step)
        if step == "calibration_checks":
            raise ValueError("Deliberate invalid calibration")

    monkeypatch.setattr(replay, "execute", stage)
    with pytest.raises(ValueError):
        execute("all", include_model=True)
    assert "train_models" in stages
    assert "site" not in stages and "publish_model_report" not in stages


def test_window_reaches_sql_calendar_quality_and_censoring():
    a, b = "2021-01-15", "2021-01-21"
    assert "BETWEEN '20210115' AND '20210121'" in render("stg_events", "p", "d", a, b)
    assert "DATE '2021-01-15',DATE '2021-01-21'" in render("mart_daily_product_metrics", "p", "d", a, b)
    assert "ABS(7-COUNT" in render("quality", "p", "d", a, b)
    assert "<=DATE '2021-01-21'" in render("mart_retention", "p", "d", a, b)
    assert "<DATE '2021-01-21'" in render("mart_experiment", "p", "d", a, b)
    assert "last_date<DATE '2021-01-21'" in render("mart_conversion_features", "p", "d", a, b)
    assert scope(a, b) == scope(a, b)
    assert scope(a, b) != scope("2021-01-14", b)
    for start, end in [(b, a), (a, a), ("2020-10-31", b), (a, "2021-02-01")]:
        with pytest.raises(ValueError):
            date_window(start, end)


def test_warehouse_replay_replaces_instead_of_appending(tmp_path):
    from google.cloud import bigquery

    wh = Warehouse.__new__(Warehouse)
    wh.bq, wh.project, wh.dataset, wh.log_path = bigquery, "p", "d", tmp_path / "jobs.jsonl"
    tables = {}
    calls = []

    def query(sql, job_config):
        calls.append(job_config)
        if not job_config.dry_run:
            assert job_config.write_disposition == "WRITE_TRUNCATE"
            tables[str(job_config.destination)] = [1, 2]
        return SimpleNamespace(
            total_bytes_processed=10,
            total_bytes_billed=10,
            cache_hit=False,
            job_id="fixture-job",
            result=lambda: [],
        )

    wh.client = SimpleNamespace(query=query)
    wh.model("stg_events")
    wh.model("stg_events")
    assert len(tables) == 1 and list(tables.values()) == [[1, 2]]
    assert len(calls) == 4 and calls[0].dry_run and calls[2].dry_run
