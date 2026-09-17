# Uncommitted extension review

Repository: `C:\Users\Administrator\Documents\Projects\google-merchandise-product-analytics`.
Base commit `1dafe6f`; branch `feature/ds-modeling-airflow`. No commit, push or
deployment has been performed. This is an implemented local extension with
remaining external execution prerequisites, not a completed real-data DS claim.

## Verification performed on this desktop

| Check | Result |
|---|---|
| Baseline install (`.[dev]`, Python 3.12.10) | Passed |
| Baseline pytest | 23 passed before code changes |
| Baseline dbt sync / Ruff / site generation | Passed |
| Extended pytest | 32 passed (9.91 seconds) |
| Extended dbt synchronization | Passed |
| Extended Ruff | Passed |
| Existing case-study generation/provenance tests | Passed |
| Actual dbt parse | Passed: dbt-core 1.12.5, bigquery adapter 1.12.1 |
| Dependency consistency (`pip check`) | Passed |
| First-view SQL relational execution | Passed on DuckDB-translated synthetic events |
| Full ML lifecycle | Passed on synthetic test fixtures, including serialized model, all metrics, calibration, segments, health and report charts |
| Deterministic ML rerun | Metric/CSV/SVG content matches on identical fixture inputs/runtime |
| Test-label isolation | Changing January labels leaves December selection metrics/selection unchanged |
| Same-window warehouse overwrite | WRITE_TRUNCATE exercised twice with a fake client; not a real cloud rerun |
| Real source scan estimate | Blocked: GOOGLE_CLOUD_PROJECT not configured |
| Airflow import/parse execution | Blocked: airflow.models unavailable; no supported Linux runtime installed |
| Fresh BigQuery feature build / dbt tests | Not run: no project/ADC configured |
| Real Airflow successful replay / repeated cloud replay | Not run |

One existing dbt deprecation warning remains: retention accepted_values arguments
use the older top-level syntax. It parses successfully; existing compatibility
has not been changed solely to silence the warning. The first baseline attempt
ran before pip finished and failed on missing statsmodels; the correctly ordered
baseline rerun passed all checks. New tests initially exposed a bounded permutation
sample-size bug and a pandas fixture assignment issue; both were corrected without
weakening the original tests.

## Requested review items

1. **Added files:** ML feature SQL/dbt and quality test, four Python modules
   (modeling, health, report, replay), three targeted test modules, real Airflow
   verification script and Linux CI job, audit/contract/operations/evidence docs.
2. **Modified files:** original DAG, date configuration/rendering/report validation,
   dbt generator and its date-sensitive generated files, optional ML dependencies,
   CI/Pages test extras, ignore/example configuration, README and existing site.
   The exact status and tracked diff summary are recorded below.
3. **Architecture:** the analytics branch is retained. A feature branch from
   stg_events joins the same manual Airflow workflow, then trains/evaluates models,
   checks calibration integrity, computes segment and weekly health, uploads
   BigQuery result tables and creates a separate local model report. Final replay
   publication waits for all requested gates. No new cloud services.
4. **Features:** device, country, first-acquisition source/medium, new/returning
   proxy, day_of_week, hour_utc, early_events, early_page_views, early_searches,
   seconds_to_view, unique_products, category_diversity.
5. **Leakage:** first-view prediction timestamp, event-time cutoff, no ambiguous
   tied non-view events, no purchase at/before prediction, conservative boundary/
   cross-day exclusions, explicit estimator allowlist and blocked-feature list,
   train-fitted encoders/scaler, and no historical/future-user aggregates.
6. **Dates:** train 2020-11-02–2020-12-14; validation 2020-12-15–2020-12-31,
   subdivided into calibration through December 23 and selection December 24–31;
   final test 2021-01-01–2021-01-30. Real row counts/prevalence remain unavailable.
7. **Logistic results:** real ROC-AUC, PR-AUC, log loss, Brier and ranking lift are
   unavailable until BigQuery session features are extracted. Fixtures verify
   computation, not expected GA4 performance.
8. **Nonlinear results:** same evidence boundary. Histogram boosting uses fixed
   configuration; no broad hyperparameter search or additional ML platform.
9. **Calibration results:** raw and sigmoid boosting plus logistic reliability
   artifacts are generated/tested. Actual real-data calibration and the preferred
   model cannot be reported yet. No test-set calibration or tuning.
10. **Segments:** device/country/acquisition/visitor proxy outputs are generated
    for all candidates, with row/class thresholds. Real segment findings pending.
11. **Health:** weekly selected-model prevalence, prediction mean, PR/ROC-AUC,
    Brier/log loss/ECE and support status; training-referenced numeric PSI and
    categorical distribution/unseen-rate outputs. Real historical values pending.
12. **DAG:** seven original tasks plus nine optional ML tasks; Airflow 3.1.7 is
    the documented runtime target. Date/boolean Params, two bounded retries,
    fail-fast contract failures, max_active_runs=1, manual schedule, gated final
    publication. AST parses locally; real DagBag/dag.test remain unverified.
13. **Manual replay:** see command below. Dates propagate into child-process
    environment, original warehouse SQL, feature SQL, Python validation and report
    metadata. dbt receives equivalent vars when invoked separately.
14. **Idempotency:** isolated per-window tables with WRITE_TRUNCATE; stable local
    artifact namespace. Unit tests verify overwrite configuration; fixture ML
    outputs repeat exactly. `verify_airflow.py --execute --repeat` must still
    establish real row-count/content-fingerprint stability against BigQuery.
15. **Tests:** original evidence tests remain intact. Added tests cover SQL future
    events/ties/exclusions, feature/probability contracts, temporal splits,
    calibration reconciliation, test isolation, drift, reruns and CLI publication
    failure propagation. Linux CI runtime evidence has not been produced yet.
16. **Limitations:** unavailable credentials/runtime; no real fitted model or model
    scores; no successful cloud replay evidence; no refreshed warehouse tests;
    finite obfuscated holiday data, same-day/product-viewing population selection,
    repeat-user dependence, sample-threshold heuristics, no uncertainty intervals,
    no live deployment or automatic retraining. Single-writer shared-directory
    execution; direct CLI/dbt concurrency on the same window is unsupported.

```sh
airflow dags trigger product_analytics_pipeline --conf '{"start_date":"2021-01-15","end_date":"2021-01-21","include_model":false}'
```

Full-window modeling uses start_date 2020-11-01, end_date 2021-01-31 and
include_model true. Review a source scan estimate before actual cloud execution.
Small-window analytics replay does not satisfy the fixed ML split requirements.

## What is needed to finish real evidence

Configure a BigQuery query project and local ADC (never paste credential contents),
and supply a Linux/WSL2 runtime for Airflow. Then estimate a small historical scan,
run small analytics/features and verify repeat behavior, estimate the full window,
run the complete model workflow, inspect real calibration/segments/health and
promote only reviewed aggregate evidence to the site. The final interview statement
should not yet claim successful Airflow orchestration or real GA4 modeling.

## Final local check output

```text
32 passed in 9.91s
Ruff: All checks passed!
pip check: No broken requirements found.
dbt sync --check: exit 0
site generation: exit 0
git diff --check: exit 0 (line-ending normalization warnings only)
```

## git diff --stat

This tracked-file summary excludes the new untracked files listed by git status.

```text
 .env.example                                    |  3 ++
 .github/workflows/ci.yml                        |  2 +-
 .github/workflows/pages.yml                     |  2 +-
 .gitignore                                      |  3 ++
 PLAN.md                                         |  7 ++++
 README.md                                       | 45 ++++++++++++++++++++++++-
 airflow/dags/product_analytics_pipeline.py      | 42 ++++++++++++++++++-----
 dbt/models/marts/mart_daily_product_metrics.sql |  2 +-
 dbt/models/marts/mart_experiment.sql            |  2 +-
 dbt/models/marts/mart_retention.sql             |  2 +-
 dbt/models/schema.yml                           |  6 ++++
 dbt/models/staging/stg_events.sql               |  2 +-
 dbt/tests/quality.sql                           |  4 +--
 docs/review.md                                  |  4 +++
 pyproject.toml                                  |  1 +
 scripts/sync_dbt.py                             | 32 ++++++++++++++----
 site/index.html                                 |  1 +
 site/template.html                              |  1 +
 src/config.py                                   | 11 ++++++
 src/extract.py                                  | 18 +++++++---
 src/pipeline.py                                 | 15 +++++----
 src/validation.py                               |  7 ++--
 22 files changed, 174 insertions(+), 38 deletions(-)
```

## git status

```text
On branch feature/ds-modeling-airflow
Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
	modified:   .env.example
	modified:   .github/workflows/ci.yml
	modified:   .github/workflows/pages.yml
	modified:   .gitignore
	modified:   PLAN.md
	modified:   README.md
	modified:   airflow/dags/product_analytics_pipeline.py
	modified:   dbt/models/marts/mart_daily_product_metrics.sql
	modified:   dbt/models/marts/mart_experiment.sql
	modified:   dbt/models/marts/mart_retention.sql
	modified:   dbt/models/schema.yml
	modified:   dbt/models/staging/stg_events.sql
	modified:   dbt/tests/quality.sql
	modified:   docs/review.md
	modified:   pyproject.toml
	modified:   scripts/sync_dbt.py
	modified:   site/index.html
	modified:   site/template.html
	modified:   src/config.py
	modified:   src/extract.py
	modified:   src/pipeline.py
	modified:   src/validation.py

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	.github/workflows/airflow.yml
	dbt/models/marts/mart_conversion_features.sql
	dbt/tests/model_feature_quality.sql
	docs/ds-audit.md
	docs/execution-evidence.md
	docs/model-contract.md
	docs/model-operations.md
	scripts/verify_airflow.py
	sql/analyses/model_feature_quality.sql
	sql/marts/mart_conversion_features.sql
	src/model_health.py
	src/model_report.py
	src/modeling.py
	src/replay.py
	tests/test_feature_sql.py
	tests/test_modeling.py
	tests/test_replay.py

no changes added to commit (use "git add" and/or "git commit -a")
```

## Real execution follow-up — setup checks

Checked at: 2026-09-17T04:09:27.884109+00:00. No implementation, model, split, README or site claims
were changed in this follow-up. No commit/push/merge/deployment occurred.

Observed environment: Windows, Python 3.12.10; dbt-core 1.12.5 and BigQuery adapter
1.12.1. gcloud was absent from PATH and the standard per-user/Program Files SDK
locations. Active gcloud account/project could not be checked because the CLI is
not installed. GOOGLE_CLOUD_PROJECT and GOOGLE_APPLICATION_CREDENTIALS were unset;
the standard ADC file was absent. google.auth.default() independently returned
DefaultCredentialsError (reported as ADC_DISCOVERED=False, with no credential
contents printed). WSL status/list commands reported WSL was not installed.
No native Windows Airflow installation was attempted.

Commands actually attempted:

```powershell
python -m src.replay estimate --start-date 2021-01-15 --end-date 2021-01-21
python -m src.replay estimate --start-date 2020-11-01 --end-date 2021-01-31
```

Both failed before a cloud query with: `Set GOOGLE_CLOUD_PROJECT to your BigQuery
query project ID. See README.` No scan estimate was returned; unknown is not zero.

| Requested real evidence | Observed result |
|---|---|
| Small-window estimated bytes/cost | Unavailable: project/ADC missing |
| Full-window estimated bytes/cost | Unavailable: project/ADC missing |
| Small real replay and repeat/fingerprints | Not executed |
| Real dbt warehouse tests/quality gates | Not executed |
| Full feature count, prevalence and all four split counts/rates | Unavailable |
| Real selection/test model metrics and selected model | Unavailable |
| Real calibration/segment/weekly health/drift | Unavailable |
| Airflow DagBag/parse and real small/repeated run | Not executed: Linux/WSL unavailable |
| Full modeling DAG | Not executed; small Airflow success prerequisite unmet |

Approximate US on-demand analysis pricing is $6.25/TiB before the applicable free
allowance. Once dry-run bytes B exist, the rough analysis-only estimate is
`B / 1099511627776 * 6.25` USD, before billing minimums/rounding, free allowance or
cache effects. The first 1 TiB/month allowance is account-wide; its remaining
balance is unknown. Storage and downstream queries are additional. The project's
5 GB query cap is not a measured scan or total workflow estimate.
Source: [BigQuery pricing](https://cloud.google.com/bigquery/pricing).

### Required user setup

Install the Google Cloud CLI using its official Windows installer:

```powershell
Invoke-WebRequest -Uri 'https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe' -OutFile "$env:TEMP\GoogleCloudSDKInstaller.exe"
& "$env:TEMP\GoogleCloudSDKInstaller.exe"
```

Open a new PowerShell after installation, then run:

```powershell
gcloud auth login
gcloud projects list
$ga4Project = Read-Host 'Enter your existing BigQuery project ID'
gcloud config set project $ga4Project
gcloud auth application-default login
gcloud auth application-default set-quota-project $ga4Project
$env:GOOGLE_CLOUD_PROJECT = $ga4Project
gcloud auth list --filter=status:ACTIVE --format='value(account)'
gcloud config get-value project
```

Choose a project where your account can run BigQuery jobs and create/write the
destination dataset. No project has been selected or invented on your behalf.
The ADC login is separate from CLI login. Never paste credential contents.
[Official installer](https://docs.cloud.google.com/sdk/docs/downloads-interactive).

In an Administrator PowerShell, install WSL with Ubuntu 24.04 (Python 3.12):

```powershell
wsl --install -d Ubuntu-24.04
```

Restart if prompted, launch Ubuntu and finish its initial user setup, then confirm
`wsl --list --verbose` shows version 2. No OS installation/restart was performed
by this follow-up. [Microsoft WSL setup](https://learn.microsoft.com/en-us/windows/wsl/install).
Linux requires its own accessible ADC setup; Windows authentication alone does not
automatically configure Linux. The existing model-operations.md contains the
isolated Airflow 3.1.7 setup and actual verify_airflow.py commands. Do not run its
optional manufactured-failure check for this follow-up; the user requested normal
real execution and observation of any naturally occurring retries only.

### Checks rerun in this follow-up

```text
python -m pytest -q: 32 passed in 8.81s
python -m ruff check src tests scripts airflow: All checks passed!
python scripts/sync_dbt.py --check: passed
 dbt parse --project-dir dbt --profiles-dir dbt --no-partial-parse: passed
```

The dbt parse used the existing offline verification placeholder only in its child
shell to satisfy profile rendering, not an authenticated/selected cloud project.
It made no warehouse-test claim. The existing accepted_values syntax deprecation
warning remains. No tests were relaxed.

### Follow-up git status

```text
On branch feature/ds-modeling-airflow
Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
	modified:   .env.example
	modified:   .github/workflows/ci.yml
	modified:   .github/workflows/pages.yml
	modified:   .gitignore
	modified:   PLAN.md
	modified:   README.md
	modified:   airflow/dags/product_analytics_pipeline.py
	modified:   dbt/models/marts/mart_daily_product_metrics.sql
	modified:   dbt/models/marts/mart_experiment.sql
	modified:   dbt/models/marts/mart_retention.sql
	modified:   dbt/models/schema.yml
	modified:   dbt/models/staging/stg_events.sql
	modified:   dbt/tests/quality.sql
	modified:   docs/review.md
	modified:   pyproject.toml
	modified:   scripts/sync_dbt.py
	modified:   site/index.html
	modified:   site/template.html
	modified:   src/config.py
	modified:   src/extract.py
	modified:   src/pipeline.py
	modified:   src/validation.py

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	.github/workflows/airflow.yml
	dbt/models/marts/mart_conversion_features.sql
	dbt/tests/model_feature_quality.sql
	docs/ds-audit.md
	docs/execution-evidence.md
	docs/model-contract.md
	docs/model-operations.md
	scripts/verify_airflow.py
	sql/analyses/model_feature_quality.sql
	sql/marts/mart_conversion_features.sql
	src/model_health.py
	src/model_report.py
	src/modeling.py
	src/replay.py
	tests/test_feature_sql.py
	tests/test_modeling.py
	tests/test_replay.py

no changes added to commit (use "git add" and/or "git commit -a")
```

### Follow-up git diff --stat

Tracked changes include the previously reviewed implementation. This follow-up
only updates this evidence document; untracked new files are excluded from diff --stat.

```text
 .env.example                                    |  3 ++
 .github/workflows/ci.yml                        |  2 +-
 .github/workflows/pages.yml                     |  2 +-
 .gitignore                                      |  3 ++
 PLAN.md                                         |  7 ++++
 README.md                                       | 45 ++++++++++++++++++++++++-
 airflow/dags/product_analytics_pipeline.py      | 42 ++++++++++++++++++-----
 dbt/models/marts/mart_daily_product_metrics.sql |  2 +-
 dbt/models/marts/mart_experiment.sql            |  2 +-
 dbt/models/marts/mart_retention.sql             |  2 +-
 dbt/models/schema.yml                           |  6 ++++
 dbt/models/staging/stg_events.sql               |  2 +-
 dbt/tests/quality.sql                           |  4 +--
 docs/review.md                                  |  4 +++
 pyproject.toml                                  |  1 +
 scripts/sync_dbt.py                             | 32 ++++++++++++++----
 site/index.html                                 |  1 +
 site/template.html                              |  1 +
 src/config.py                                   | 11 ++++++
 src/extract.py                                  | 18 +++++++---
 src/pipeline.py                                 | 15 +++++----
 src/validation.py                               |  7 ++--
 22 files changed, 174 insertions(+), 38 deletions(-)
```
