"""Integration fixtures are synthetic and confined to pytest's temporary directory."""

import json
import shutil

import pandas as pd

from src import pipeline, validation


def test_full_offline_artifact_pipeline(tmp_path, monkeypatch):
    shutil.copytree(pipeline.ROOT / "site", tmp_path / "site")
    monkeypatch.setattr(pipeline, "ROOT", tmp_path)
    monkeypatch.setattr(validation, "ROOT", tmp_path)
    processed = tmp_path / "data/processed"
    processed.mkdir(parents=True)

    def save(name, value):
        (processed / f"{name}.json").write_text(json.dumps(value), encoding="utf-8")

    daily, segments, experiment = [], [], []
    for i, day in enumerate(pd.date_range("2020-11-01", "2021-01-31")):
        d = day.date().isoformat()
        n = 200 + (i % 7) * 10
        purchases = 100 if i == 40 else 20
        daily.append(
            dict(
                metric_date=d,
                users=n,
                purchase_users=purchases,
                sessions=n,
                purchase_sessions=purchases,
                transactions=purchases,
                revenue_usd=purchases * 10,
                missing_revenue_transactions=0,
                ordered_checkout_sessions=100,
                ordered_purchase_sessions=purchases,
                session_conversion=purchases / n,
                user_conversion=purchases / n,
                checkout_completion=purchases / 100,
            )
        )
        for device in ["mobile", "desktop"]:
            segments.append(
                dict(
                    metric_date=d,
                    dimension="device",
                    segment=device,
                    sessions=n // 2,
                    purchase_sessions=purchases // 2,
                    viewed=n // 2,
                    cart=60,
                    checkout=50,
                    purchased=purchases // 2,
                    revenue_usd=purchases * 5,
                    transactions=purchases // 2,
                )
            )
        if i < 91:
            for stage in [2, 3, 4]:
                experiment.append(
                    dict(stage=stage, eligibility_date=d, eligible_users=50, converted_users=20)
                )
    funnel = []
    previous = None
    for stage, reached in enumerate([1000, 800, 400, 300], 1):
        funnel.append(
            dict(
                grain="ordered_sessions",
                stage=stage,
                reached=reached,
                previous_reached=previous,
                dropoff_rate=(previous - reached) / previous if previous else None,
            )
        )
        previous = reached
    retention = [
        dict(
            cohort_week="2020-11-02",
            dimension="all",
            segment="all",
            horizon=h,
            eligible_users=1000,
            returned_users=100,
            retention=0.1,
        )
        for h in [1, 7, 14, 30]
    ]
    save("quality", [dict(test=f"check_{i}", failures=0) for i in range(12)])
    save(
        "audit",
        [
            dict(section="ecommerce_coverage", label=e, detail=json.dumps(dict(events=100)))
            for e in ["view_item", "add_to_cart", "begin_checkout", "purchase"]
        ],
    )
    for name, rows in [
        ("mart_daily_product_metrics", daily),
        ("mart_segments", segments),
        ("mart_funnel", funnel),
        ("mart_retention", retention),
        ("mart_experiment", experiment),
        ("product_coverage", []),
    ]:
        save(name, rows)
    pipeline.analyze()
    pipeline.monitor()
    pipeline.site()
    report = json.loads((tmp_path / "site/report.json").read_text(encoding="utf-8"))
    assert report["status"] == "verified"
    assert report["experiment"]["transition"] == "Cart to checkout"
    assert report["experiment"]["baseline"] == 0.4
    assert report["alerts"]
    assert report["investigation"]["cases"]
    assert (tmp_path / "site/funnel.svg").exists()
    assert "No numerical findings" not in (tmp_path / "site/index.html").read_text(encoding="utf-8")
    case = report["investigation"]["cases"][0]
    import pytest

    assert case["mix"] + case["within"] == pytest.approx(case["delta"])
    revenue = case["daily_revenue"]
    assert revenue["volume_effect"] + revenue["revenue_per_session_effect"] == pytest.approx(revenue["delta"])
