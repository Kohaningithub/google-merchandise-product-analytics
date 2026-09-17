# Extension audit (before implementation)

Base: `1dafe6f`, restored from origin/main into Documents/Projects; clean checkout,
feature branch `feature/ds-modeling-airflow`. No pre-existing local work.

The direct runner executes audit/staging → eight further models → warehouse
validation → aggregate exports → analysis/power → anomaly diagnosis → site.
Canonical SQL is copied into a real dbt project by scripts/sync_dbt.py. dbt uses
table materializations; the direct runner uses WRITE_TRUNCATE. Neither appends.
Every direct query is dry-run with a 5 GB default per-query billing cap and a
query/job/hash log. This is not a total cost budget.

Existing models: stg_events, fct_purchases, int_sessions, int_users,
mart_daily_product_metrics, mart_funnel, mart_retention, mart_segments,
mart_experiment. Quality SQL checks uniqueness, conflict quarantine, chronology,
reconciliation, cohort bounds, retention subsets and all 92 source dates.
Python separately checks exports, daily denominators and funnel event coverage.

Airflow imports airflow.sdk (3.x), but no runtime version was pinned or installed.
Seven tasks form a linear chain; manual schedule, catchup=False, max_active_runs=1,
two retries separated by two minutes. No date parameters. All failures retry,
including deterministic quality failures. Tests parse Python AST only.

Dates are fixed in source SQL, mart calendars/censoring/quality, Python export
validation and report metadata; experiment traffic uses 91 eligible days.
Replay replaces whole tables and does not preserve prior windows. The output
directory is shared with the published evidence.

Analytics already implements ordered session funnels, censored exact-day
retention, Wilson intervals, past-only median/MAD monitoring, matched-weekday
diagnosis, symmetric mix/rate decomposition and prospective 80%/90% power.
There is no ML feature table, estimator, calibration or model-health pipeline.

CI runs dbt sync, site generation, pytest and Ruff on Python 3.12. Pages builds
the existing static case study on main. The repository contains real aggregate
inputs, query metadata and prior dbt execution evidence; no session training rows.
The original analytical work and historical SQL will be retained.

Environment: Windows/Python 3.12.10. No configured ADC/project, Cloud SDK, Docker,
or usable WSL installation found. These prevent fresh cloud/runtime evidence.
An initial check was launched before pip completed and encountered missing
statsmodels; this is an installation-order failure, not a repository regression.
Baseline results after installation are recorded in execution-evidence.md.
