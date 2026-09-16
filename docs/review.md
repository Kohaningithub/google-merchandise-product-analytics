# Candidate-style review and execution status

## Implemented

* SQL: bounded raw scans; nested arrays and structs; conditional aggregates; earliest-event dimensions; window functions / QUALIFY; transaction deduplication; sequential funnel; date-censored cohorts; safe ratios; standalone lag/rolling and product-ranking queries.
* Engineering: canonical SQL and drift-checked dbt copies, aggregate exports, machine-readable metric contracts, fail-closed validation, retryable Airflow task boundaries, and a static generated site.
* Statistical workflow: Wilson descriptive intervals, past-only robust anomaly detection, symmetric mix/rate decomposition, volume/revenue-per-session decomposition, prospective user-randomized power planning.
* Product reasoning: structured finding/evidence/interpretation/action/boundary cards generated only from data; instrumentation checks before UX recommendations; no invented experiment outcomes.

## Verified execution

The full pipeline successfully executed the real BigQuery source window, materialized every existing model, passed all warehouse quality checks, exported real aggregates and generated the case study. The existing signed-in CLI credential file was selected through `GOOGLE_APPLICATION_CREDENTIALS` because the conventional ADC path was absent. No credential content was published.

The first run correctly blocked on conflicting transaction IDs. Investigation separated invalid IDs, consistent repetitions and contradictory IDs. The final model quarantines contradictory IDs rather than arbitrarily choosing an owner or revenue. The accepted facts reconcile with source accounting, and the gate still rejects contradictory IDs in published facts. Purchase-event conversion is separately defined and retains all valid-identity purchase events.

Input snapshots, SQL hashes, successful BigQuery job metadata, and generated report/CSV/chart artifacts are preserved. Offline tests recompute the headline findings and prospective power design from those snapshots. Scheduler execution remains outside this historical replay; no live Airflow deployment is claimed.

## Material review fixes

* Do not conflate unordered user reach with a sequential funnel.
* Freeze acquisition dimensions and exclude cross-day first-session behavior from cohort-day classifications.
* Select the prospective experiment's transition from the observed bottleneck; align the power denominator to first eligible users.
* Quarantine source transaction conflicts, report their exclusions, and block any ambiguous ID from accepted facts.
* Suppress revenue alerts on dates with missing transaction revenue.
* Use prior observations only for monitoring and match weekdays in descriptive investigation.
* Do not publish raw transaction identifiers in audit artifacts.
* Preserve incomplete / no-anomaly states rather than manufacturing incidents or business recommendations.

## Known analytical limits

The short holiday-spanning sample is not a reliable long-run enrollment forecast. Robust scores are heuristic surveillance, with no formal false-discovery control across metrics/days. Source obfuscation can break otherwise reasonable invariants; investigate failures rather than weakening gates to make numbers appear. Transaction-category outputs describe purchased products, not product-specific conversion without an exposure denominator. Revenue diagnosis covers session-linked observed revenue and is not guaranteed to reconcile to all purchase-date revenue.

The observed January conversion increase survives comparison with the two most recent matched weekdays, excluding the older holiday dates. This supports investigation, not a causal attribution or invented product incident.

## Final validation

The full BigQuery quality gate passed, all 10 dbt tests passed on the real tables, and all 23 Python tests passed. The site was inspected on desktop and mobile; a result-table overflow was corrected. Headline values, charts and CSVs are regenerated from the preserved query outputs. See the dated dbt validation JSON and report warehouse job metadata for execution evidence.
