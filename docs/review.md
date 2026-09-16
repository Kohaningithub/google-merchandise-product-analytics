# Candidate-style review and execution status

## Implemented

* SQL: bounded raw scans; nested arrays and structs; conditional aggregates; earliest-event dimensions; window functions / QUALIFY; transaction deduplication; sequential funnel; date-censored cohorts; safe ratios; standalone lag/rolling and product-ranking queries.
* Engineering: canonical SQL and drift-checked dbt copies, aggregate exports, machine-readable metric contracts, fail-closed validation, retryable Airflow task boundaries, and a static generated site.
* Statistical workflow: Wilson descriptive intervals, past-only robust anomaly detection, symmetric mix/rate decomposition, volume/revenue-per-session decomposition, prospective user-randomized power planning.
* Product reasoning: structured finding/evidence/interpretation/action/boundary cards generated only from data; instrumentation checks before UX recommendations; no invented experiment outcomes.

## Not yet verified against BigQuery

The local Google authentication library raises `DefaultCredentialsError`. No project ID is configured and no gcloud/bq executable was found during inspection. Live schema, source event coverage, model execution, data-quality outcomes, query bytes, findings, and power estimates are therefore **pending**, not passed. The documented schema was checked against Google's primary documentation. SQL parses locally; parsing is not warehouse execution.

## Material review fixes

* Do not conflate unordered user reach with a sequential funnel.
* Freeze acquisition dimensions and exclude cross-day first-session behavior from cohort-day classifications.
* Select the prospective experiment's transition from the observed bottleneck; align the power denominator to first eligible users.
* Keep transaction conflicts visible and block publication rather than arbitrarily claiming clean revenue.
* Suppress revenue alerts on dates with missing transaction revenue.
* Use prior observations only for monitoring and match weekdays in descriptive investigation.
* Do not publish raw transaction identifiers in audit artifacts.
* Preserve incomplete / no-anomaly states rather than manufacturing incidents or business recommendations.

## Known analytical limits

The short holiday-spanning sample is not a reliable long-run enrollment forecast. Robust scores are heuristic surveillance, with no formal false-discovery control across metrics/days. Source obfuscation can break otherwise reasonable invariants; investigate failures rather than weakening gates to make numbers appear. Transaction-category outputs describe purchased products, not product-specific conversion without an exposure denominator. Revenue diagnosis covers session-linked observed revenue and is not guaranteed to reconcile to all purchase-date revenue.

If no actionable anomaly is detected, that is a valid result. If authentication remains unavailable, the code and honest pending-data case study are deliverable; an evidence-backed finished analysis is not.
