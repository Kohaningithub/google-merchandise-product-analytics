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


## Windows restoration and preservation — 2026-09-17

Restored a separate clone under `%USERPROFILE%/Documents/Projects/google-merchandise-product-analytics`.
The pre-existing portfolio checkout and its uncommitted presentation edits were left untouched.
Both new annotated rollback tags were pushed and their peeled targets verified against origin:

- `public-product-analytics-v1`: `1dafe6f3075891ab56141dfb5874803a2e4e5b94`.
- `pre-real-execution-v1`: `0cd26126d4c1be43e9b2fef1a4776e6834261814`.

The public commit is an ancestor of main and remains its tip. The feature branch
remains separate at the checkpoint above. Neither tag was moved. No branch push,
new code commit, merge, workflow dispatch or deployment occurred. The clone was
clean after switching to `feature/ds-modeling-airflow` and a fast-forward-only pull.
Only this evidence document was subsequently edited.

### Environment actually observed

- Windows; Python 3.14.3 on the current PATH.
- Google Cloud SDK 585.0.0 is installed in the normal per-user SDK location,
  but its bin directory is absent from this process PATH. BigQuery CLI 2.1.38.
- CLI account is signed in; configured project is `project-a1c7b526-d5b8-4e0c-9f1`.
- BigQuery API is enabled, verified with the CLI service listing. Actual source
  access through the Python runner has not yet been verified on this clone.
- No explicit ADC environment configuration; conventional ADC file absent.
  `google.auth.default()` returned `DefaultCredentialsError`. No secrets printed.
- WSL status and distribution listing both report WSL is not installed.
  No native Windows Airflow installation attempted. Docker not found on PATH.
- dbt-core, dbt-bigquery and scikit-learn are absent from this Python environment.
  The prior Python 3.12 checkpoint results above belong to the prior machine.

### Checks and estimates attempted

- `python -m pytest -q`: **27 passed, 1 skipped** (13.79 seconds).
  The modeling test module is skipped because scikit-learn is absent; this is
  not a complete 32-test ML verification.
- `python -m ruff check src tests scripts airflow`: passed.
- `python scripts/sync_dbt.py --check`: passed.
- dbt parse and Airflow verification: not run here; required runtimes absent.
- Small estimate: `python -m src.replay estimate --start-date 2021-01-15 --end-date 2021-01-21`.
- Full estimate: `python -m src.replay estimate --start-date 2020-11-01 --end-date 2021-01-31 --include-model`.

Both estimates were attempted with the configured project explicitly supplied via
`GOOGLE_CLOUD_PROJECT`. Both stopped at ADC discovery before a BigQuery query.
Bytes, GiB/TiB, costs and dominant scans are unavailable, not zero. Inspection also
confirms the existing `estimate` stage estimates only stg_events source scanning;
it does not estimate downstream materialized-table scans or model execution.
A source-only estimate must not be represented as a full-workflow cost estimate.

No real replay, repeat/idempotency check, feature extraction, model fit, evaluation,
calibration, segment/health/drift output, or Airflow run occurred in this follow-up.
No new model metrics or public claims were generated. Existing analysis, modeling
implementation, temporal splits, README and site remain unchanged.

### First authenticated small replay attempt — 2026-09-17

ADC refresh, the configured project and a zero-byte BigQuery dry run succeeded.
The replay used `BQ_MAX_BYTES=5368709120` (exactly 5 GiB). Every warehouse query
performed its own dry run before execution; all 18 estimates were below the cap.
The largest was `stg_events` at 138,847,135 bytes (0.129 GiB).

The warehouse, validation, export, analysis and monitoring stages completed for
2021-01-15 through 2021-01-21. All 17 warehouse quality checks returned zero
failures. Aggregate outputs contain 7 daily rows, 8 funnel rows, 246 retention
rows, 763 segment rows and 18 experiment rows. The source audit observed 297,357
events, 22,801 users and 27,395 sessions. No row-level identifiers were reported.

The run stopped at final site rendering. This short window generated zero anomaly
flags and therefore no device investigation case; the current recruiter template
unconditionally selects a device case and raised a Jinja `UndefinedError`. This
is a short-window publication compatibility bug after successful warehouse work,
not a BigQuery or quality-gate failure. Per the execution stop conditions, the
identical replay, full feature build and model lifecycle were not started.

Session usage through the stop point: estimated and processed bytes were both
531,557,467 (0.495051 GiB); billed bytes were 670,040,064 (0.624023 GiB). This is
well below the 200 GiB internal ceiling. The query log records job IDs, dry-run
estimates, actual processed/billed bytes, cache status and SQL hashes. No service
beyond the already-enabled BigQuery API was enabled.

### Continued replay, idempotency and real model execution — 2026-09-17

The short-window publication assumption was corrected without changing analysis:
when no device anomaly case exists, the template renders a neutral no-flag state.
The original full-window result remains unchanged. The first replay then completed
through site generation and the full local checks passed.

The same 2021-01-15 through 2021-01-21 replay was executed again with the exact
5 GiB cap. All nine warehouse tables retained identical row counts and full-table
fingerprints after `WRITE_TRUNCATE`: stg_events 297,357 / -5309162196314258893;
fct_purchases 272 / 3969245514017424322; int_sessions 27,395 /
-5996788293651334876; int_users 22,801 / -1123140342108037465;
mart_daily_product_metrics 7 / 1162578661996687369; mart_funnel 8 /
-7325095425782887940; mart_retention 246 / 2698181718582952445;
mart_segments 763 / -6336609104176835938; mart_experiment 18 /
-6271436215799732386. Each fingerprint query was dry-run and capped first.

The full 2020-11-01 through 2021-01-31 source estimate was 2,076,000,935 bytes
(1.933 GiB). The full analytics, feature, training, evaluation, calibration,
segment, health, persistence and local model-report workflow completed. Its 21
queries processed 8,816,474,964 bytes (8.210982 GiB) and billed 8,887,730,176
bytes (8.277344 GiB). The largest query remained stg_events at 1.933 GiB; every
query dry-run estimate was below 5 GiB. BigQuery DataFrame uploads replaced result
tables and did not scan the GA4 source.

BigQuery table metadata confirms 75,414 feature rows, 67,224 prediction rows
(22,408 test sessions × three candidates), 3 evaluation rows, 375 segment rows
and 5 weekly health rows in the isolated full-window replay dataset. Metadata API
checks do not execute queries or add processed bytes.

The real feature mart contains 75,414 eligible sessions. Temporal splits and
prevalence: train 40,993 / 6.7938%; calibration 8,406 / 6.9117%; selection 3,607 /
4.5744%; final test 22,408 / 4.6100%. Leakage and split gates passed. Validation
selected uncalibrated histogram boosting by the predefined log-loss rule: selection
log loss 0.166808 and PR-AUC 0.155028, versus logistic 0.170200 / 0.119204 and
sigmoid boosting 0.167394 / 0.155028. Final-test results were evaluated only after
selection:

| Candidate | ROC-AUC | PR-AUC | Log loss | Brier | ECE | Decile lift | Quintile lift |
|---|---:|---:|---:|---:|---:|---:|---:|
| Logistic | 0.732620 | 0.112063 | 0.172704 | 0.042605 | 0.010828 | 2.8265 | 2.5990 |
| Boosting | 0.750267 | 0.117913 | 0.172800 | 0.043137 | 0.020539 | 2.8458 | 2.5119 |
| Boosting + sigmoid | 0.750267 | 0.117913 | 0.172851 | 0.042962 | 0.020668 | 2.8458 | 2.5119 |

The selected boosting model's ten equal-frequency final-test calibration buckets
each contain about 2,240 sessions. Mean prediction versus observed conversion runs
from 0.006514 / 0.003124 in the lowest bucket to 0.205406 / 0.131191 in the highest;
the model overpredicts in this later period. Calibration integrity checks passed.

Supported selected-model segment results are descriptive. Device prevalence was
desktop 4.3745% (n=13,030), mobile 4.9236% (n=8,835), tablet 5.1565% (n=543).
New-proxy prevalence was 2.5678% (n=15,967) versus returning-proxy 9.6724%
(n=6,441). Supported source groups ranged from 3.8877% for `<Other>` (n=6,019)
to 9.3117% for `(data deleted)` (n=1,482); these are predictive associations,
not effects. Fourteen countries, five sources, six media, three devices and two
visitor-proxy groups met the implemented support rule.

Five weekly health windows were generated. Selected-model PR-AUC ranged from
0.063049 to 0.153723; ROC-AUC 0.673836 to 0.786352; Brier 0.034689 to 0.048028;
log loss 0.152876 to 0.182179; ECE 0.011521 to 0.036210. Categorical unseen rates
were zero. The largest PSI, day_of_week=4.581741 in the initial three-day partial
week, reflects its incomplete weekday composition and is not treated as a live
incident. Later notable PSI values include seconds_to_view 0.364071 and
unique_products 0.193833 in the final partial week.

Cumulative project-session query usage, including both small replays, both
fingerprint audits and the full model run, is 10,121,244,136 processed bytes
(9.426143 GiB) and 10,617,880,576 billed bytes (9.888672 GiB). Dry-run-only
estimates and the zero-byte access check add no processed bytes. Usage remains far
below the 200 GiB ceiling. No reservations, BigQuery ML, Vertex AI, Dataflow,
Pub/Sub, Composer or other GCP service was enabled.

Python 3.14.3 with scikit-learn 1.7.2 completed 32 pytest tests; Ruff, dependency
checking, dbt synchronization and replay site generation passed.

### Real Airflow runtime — 2026-09-17

Ubuntu 24.04 is installed under WSL2 with Linux user `kchen`. Airflow 3.1.7 runs
in the isolated environment `/home/kchen/.venvs/ga4-airflow`; the runtime copy of
the repository is `/home/kchen/google-merchandise-product-analytics`. Application
Default Credentials from the Windows gcloud installation work inside WSL, and
the active billing/quota project is `project-a1c7b526-d5b8-4e0c-9f1`.

DagBag loaded `product_analytics_pipeline` without import errors and parsed all 16
expected tasks. The typed params are `start_date`, `end_date` and `include_model`.
Every task has two retries and a two-minute retry delay. Dependency assertions
confirmed that model training is gated by `validate_model_features`, while final
publication waits for both anomaly diagnosis and model-report publication.

Two real Airflow small-window runs used 2021-01-15 through 2021-01-21 with
`include_model=false`:

| Run ID | DAG status | Analytics tasks | Model tasks | Publication |
|---|---|---:|---:|---|
| `manual__2026-09-17T13:54:31.031658+00:00` | success | 7 success | 9 skipped | success |
| `manual__2026-09-17T13:56:02.165931+00:00` | success | 7 success | 9 skipped | success |

All 17 warehouse quality gates passed in both runs. The repeated run produced
identical row counts and full-table fingerprints for all nine warehouse tables:
stg_events 297,357 / -5309162196314258893; fct_purchases 272 /
3969245514017424322; int_sessions 27,395 / -5996788293651335876; int_users
22,801 / -1123140342108037465; mart_daily_product_metrics 7 /
1162578661996687369; mart_funnel 8 / -7325095425782887940; mart_retention 246 /
2698181718582952445; mart_segments 763 / -6336609104176835938; and
mart_experiment 18 / -6271436215799732386. This is observed Airflow replay
idempotency evidence, including successful artifact publication on both runs.

The full real Airflow run used 2020-11-01 through 2021-01-31 with
`include_model=true`. Run `manual__2026-09-17T13:57:45.110265+00:00` finished
`success` in 153.317 seconds. All 16 tasks finished `success`: the seven analytics
tasks plus feature build and validation, training, evaluation, calibration,
segment diagnostics, model health, result persistence and model-report
publication. Analytics quality gates, leakage/split gates and calibration
integrity checks passed. Final publication succeeded. The resulting table
signatures were 4,295,584 staged events, 4,436 purchases, 360,129 sessions,
270,154 users, 75,414 model-feature rows, 67,224 prediction rows and five model
health rows; these agree with the independently verified full-window artifacts.

Every Airflow BigQuery statement was dry-run first and executed with
`maximum_bytes_billed=5368709120`. The two small runs plus their fingerprint
audits processed 1,304,769,172 bytes (1.215161 GiB) and billed 1,730,150,400
bytes (1.611328 GiB); their largest query was 138,847,135 bytes. The full Airflow
run plus its fingerprint audit processed 10,581,602,695 bytes (9.854885 GiB) and
billed 10,726,932,480 bytes (9.990234 GiB); its largest individual query was
2,076,000,935 bytes (1.933 GiB). All queries stayed below the 5 GiB cap.

Cumulative project-session usage after Windows and Airflow verification is
22,007,616,003 processed bytes (20.496190 GiB) and 23,074,963,456 billed bytes
(21.490234 GiB), well below the 200 GiB safety ceiling. No reservations,
BigQuery ML, Vertex AI, Dataflow, Pub/Sub, Composer or other GCP service was
enabled.

Final Linux runtime verification completed 32 pytest tests; Ruff, dbt canonical
sync and `pip check` passed. A final parse-only DagBag check again reported
Airflow 3.1.7, `parsed: true` and all 16 expected tasks.
