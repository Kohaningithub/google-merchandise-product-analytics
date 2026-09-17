# Completed historical execution

Current extension work is on `feature/ds-modeling-airflow`, uncommitted. See
[the extension audit](docs/ds-audit.md), [prediction contract](docs/model-contract.md)
and [execution/review evidence](docs/execution-evidence.md). Local modeling and
replay contracts pass; real model training, fresh warehouse validation and Linux
Airflow/repeated cloud replay await project credentials and a supported runtime.
The completed execution described below refers to the original analytics only.

The existing platform has now run end to end against the real GA4 public dataset for 20201101 through 20210131.

- Existing CLI credentials used without copying secrets.
- All existing SQL models executed on BigQuery.
- Conflicting transaction-ID assumption corrected through explicit quarantine and reconciliation.
- Warehouse validation passed; real aggregates and query metadata preserved.
- Funnel, retention, KPI, monitoring, decomposition and prospective power artifacts generated.
- Executive findings generated from the report; source snapshots and number-reconciliation tests added.
- README, methodological notes and static site updated for verified evidence.

No new modeling scope, synthetic observed results, product incident claims, or experimental treatment outcomes were introduced. The experiment remains prospective. GitHub Actions validates and deploys the updated case study on push.
