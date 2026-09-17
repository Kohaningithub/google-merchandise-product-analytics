# Production Data Science Extension

The existing analytics remains the case-study foundation. The extension adds a
first-product-view conversion feature mart, logistic regression and native sklearn
histogram boosting, temporal validation, sigmoid calibration, segment diagnostics
and fixed-reference weekly model health. No causal/incrementality analysis or
new cloud service is introduced. See [prediction contract](model-contract.md).

## Status and interpretation

The local synthetic integration test runs the whole modeling lifecycle, generates
reports and verifies deterministic reruns. These are software tests, not observed
GA4 model results. Actual model metrics, feature-mart execution, full Airflow
runtime and repeated cloud replay remain unverified on this desktop. The prior
BigQuery/dbt analytics evidence is preserved separately and does not verify ML.

PR-AUC is sklearn average precision (step-weighted PR area), with prevalence as
the baseline. Log loss selects among the fixed logistic, boosting and calibrated
boosting candidates on the later validation slice. Brier, ROC-AUC and calibration
error supplement it. Top-decile/quintile lift is ranking performance only; all
ties at the cutoff are included and the actual fraction is reported.

Reliability bins are equal-frequency, keep ties together and merge small bins;
each contains at least 100 observations. ECE is weighted absolute calibration
error over these bins; it depends on binning. Segment/weekly metrics need 200 rows,
and PR/ROC additionally need ten positives and ten negatives. Suppressed metrics
are null, never zero. Counts/prevalence remain available to explain suppression.
These screening thresholds do not establish statistical certainty. No confidence
intervals or claims of significant segment differences are made.

Logistic numeric coefficients are per training-standard-deviation change, categorical
coefficients are regularized one-hot log-odds associations (not independent causal
effects). Boosting permutation importance uses later validation negative log loss,
three repeats and at most 5,000 rows. Correlated inputs limit interpretation.

Health uses the selected frozen model on successive final-test weeks. Partial
boundary weeks are identified by actual start/end and row count. Numeric drift
uses training-quantile PSI with 0.5 pseudocounts and infinite end bins; categorical
drift uses total variation and unseen-category rate. No universal drift threshold,
automatic retraining or fake daily live schedule is claimed. In production, score
new partitions with the frozen model, wait for mature labels, then evaluate; do
not retrain on each monitoring window or reinterpret label-free drift as accuracy.

## Local setup and cost-first execution

```powershell
.\.venv\Scripts\python -m pip install -e ".[dev,ml,dbt]"
$env:GOOGLE_CLOUD_PROJECT="your-query-project"
# Authenticate with your own application-default credentials first.
.\.venv\Scripts\python -m src.replay estimate --start-date 2021-01-15 --end-date 2021-01-21
```

`estimate` performs only a dry run of the raw source scan, creates no dataset and
executes no paid query. Review its bytes before running `all`. Every subsequent
query also dry-runs and enforces BQ_MAX_BYTES (default 5 GB per query); logs show
estimates and actual job bytes. Source bytes are not a full-workflow budget or a
dollar quote. Pricing/free allowance depends on the user's account and region.
There has been no new cloud query/cost estimate on this desktop.

```powershell
python -m src.replay all --start-date 2021-01-15 --end-date 2021-01-21
# Build/validate only a small-window feature mart:
python -m src.replay build_model_features --start-date 2021-01-15 --end-date 2021-01-21
python -m src.replay validate_model_features --start-date 2021-01-15 --end-date 2021-01-21
# Estimate full source window before authorizing its execution:
python -m src.replay estimate
python -m src.replay all --include-model
```

Short windows cannot train the fixed November/December/January protocol and fail
the split gate. Each date window uses `<BQ_DATASET>_replay_YYYYMMDD_YYYYMMDD`
and ignored `artifacts/replays/YYYYMMDD_YYYYMMDD/`. Same-window reruns replace
whole tables using WRITE_TRUNCATE; dbt uses table materializations. They do not
append. Different windows do not overwrite each other or data/published. This is
a historical replay namespace, not a production partition-retention policy.
Use one writer at a time per window (the DAG has max_active_runs=1); concurrent
manual CLI/dbt writers against the same dataset are unsupported.

Direct rendering applies the validated date scope to the original historical SQL
without changing its committed bytes/hashes. Generated dbt files express the same
dates as vars, including calendar, retention and experiment censoring, and coverage.
For dbt, explicitly select the replay dataset and matching date vars:

```sh
export BQ_DATASET=product_analytics_replay_20210115_20210121
dbt build --project-dir dbt --profiles-dir dbt --vars '{"start_date":"2021-01-15","end_date":"2021-01-21"}'
```

Use a separate shell for this dbt setting; the replay CLI appends its own window
suffix to BQ_DATASET and should receive the base name `product_analytics`.

dbt builds/tests features but does not train sklearn. The DAG follows the existing
direct BigQuery runner, sharing canonical SQL with dbt, then runs Python ML. It
does not falsely claim to invoke dbt when it executes canonical SQL directly.

## Airflow 3.1.7 runtime

Use Linux/WSL2; native Windows is not a supported Airflow runtime. No usable Linux
runtime was found here. [Official installation](https://airflow.apache.org/docs/apache-airflow/3.1.7/installation/index.html)
and [dag.test documentation](https://airflow.apache.org/docs/apache-airflow/3.1.7/core-concepts/debug.html).

```sh
python3.12 -m venv .venv-airflow
. .venv-airflow/bin/activate
pip install 'apache-airflow==3.1.7' --constraint https://raw.githubusercontent.com/apache/airflow/constraints-3.1.7/constraints-3.12.txt
pip install -e '.[dev,ml]'
pip check
export AIRFLOW_HOME="$PWD/.airflow"
export AIRFLOW__CORE__LOAD_EXAMPLES=false
export AIRFLOW__CORE__DAGS_FOLDER="$PWD/airflow/dags"
airflow db migrate
python scripts/verify_airflow.py --failure-check
# Only after BigQuery authentication and cost review:
python scripts/verify_airflow.py --execute --repeat --start-date 2021-01-15 --end-date 2021-01-21
python scripts/verify_airflow.py --execute --repeat --include-model --start-date 2020-11-01 --end-date 2021-01-31
```

The verification script uses real DagBag and dag.test, no mocked tasks. It records
task states, full-table row counts/content fingerprints for repeated executions,
and optionally verifies deterministic invalid-date failure propagation without
cloud calls. Fingerprints are practical replay checks, not cryptographic equality
proofs. Its JSON is written only after successful checks. The added Linux CI job
parses the DAG and tests the failure path; it has not been run on GitHub yet.

With the scheduler/API running, manually trigger:

```sh
airflow dags trigger product_analytics_pipeline --conf '{"start_date":"2021-01-15","end_date":"2021-01-21","include_model":false}'
```

There is one extended DAG, schedule=None. It retains the original seven tasks and
adds nine ML stages. ValueError contracts fail without retries via AirflowFailException;
other task failures have at most two retries. No downstream publication succeeds
after a failed gate. ML is explicitly optional for short analytics replays.
Code, credentials and output filesystem must be available to each task process;
this is a single-host shared-directory workflow, not a distributed-storage design.

## Artifacts and BigQuery schema

Under the replay's `model/` directory: features.parquet, model.joblib, metadata.json,
predictions.parquet, model_metrics.json, model_calibration.csv,
model_segment_metrics.csv, model_health.csv, model_drift.csv,
model_coefficients.csv, model_importance.csv, four SVG figures and model_report.html.
All are ignored. Never load an untrusted joblib. Do not commit session rows or model
binaries. A reviewed aggregate-only report can later be promoted to Pages; current
ML results are not silently substituted into the verified historical case study.

Metadata records code/input hashes, Git base commit (working code hash disambiguates
uncommitted edits), sklearn version, parameters, seed, training time, split counts/
rates and selected candidate. Metric/chart outputs repeat for the same inputs and
runtime; metadata timestamps intentionally change. Environment changes may change
numerical results; record/freeze the verified environment before comparing runs.

BigQuery persists mart_conversion_features, model_predictions, model_evaluation,
model_segment_metrics and model_health in the isolated dataset. Predictions are
session_key × candidate, with session_date, target, probability and model_version.
Health grain is model_version × evaluation_window, with run_date (historical window
end, not wall-clock execution time), start/end, row_count, prevalence, prediction
mean, PR/ROC-AUC, Brier, log loss, ECE, support status and ranking lift. Execution
timestamp lives in metadata. Nullable quality metrics represent insufficient
support. DataFrame load jobs infer numeric/string fields and replace the result
tables; these uploads do not scan the GA4 source.

For interview evidence, capture the real Airflow Grid run and task logs alongside
airflow-evidence.json, feature query/job log, dbt run_results.json, metadata.json,
calibration plot and weekly health CSV. Do not use fixture screenshots as GA4 results.
