# Data and metric contracts

Source: `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`, bounded to `20201101`–`20210131`. The published schema has been reviewed; actual historical schema, coverage, counts and query bytes require authenticated execution. `audit` saves the actual first-table schema and checks all scanned rows. Do not mistake documentation review for a live query.

## Fields used

| Field | Use / limitation |
|---|---|
| `event_date` | Property-local calendar date; cohort and activity dates. Parsed with `%Y%m%d`. |
| `event_timestamp` | UTC microseconds; ordering and session duration. Ties do not prove sequence. |
| `event_name` | Event presence and funnel stages. All actual values audited; unexpected names are not discarded. |
| `user_pseudo_id` | Browser/app identity. Null, blank, `<Other>`, `(not set)` excluded from user metrics. Not a person or signup ID. |
| `event_params.ga_session_id` | Integer session component. Session key is JSON STRUCT of user ID plus session ID to avoid collisions. Missing IDs excluded from session metrics, counted in audit. |
| `event_params.ga_session_number` | First-event new/returning proxy: 1 / greater than 1 / unknown. Not lifetime verified history. |
| `event_params.page_location` | Audit/instrumentation context only; not published in aggregates. |
| `event_params.currency`, `value` | Audit context. Local values are not summed across currencies or substituted for USD. |
| `device.category`, `geo.country` | First session event for session segments; first user event for cohorts. Nulls retained as unknown. |
| `traffic_source.source`, `medium` | User-acquisition fields from the export. Not session attribution; no attribution or marketing-effect claims. |
| `ecommerce.transaction_id` | Global valid-transaction key after excluding known placeholders. Earliest row wins; conflicting users or revenues stop publication. |
| `ecommerce.purchase_revenue_in_usd` | Currency-converted gross purchase value. Missing remains missing; negatives stop publication. |
| `ecommerce.refund_value_in_usd` | Coverage audit only. Refund completeness is unverified; net revenue is not claimed. |
| `items.item_id`, `item_name`, `item_category`, `quantity`, `item_revenue_in_usd` | Separate transaction-item category audit. Never fan out session denominators through item arrays. |

Repeated event parameters use MAX for deterministic extraction and produce a duplicate-key warning. Event fingerprints describe suspicious repeats, not a source-supplied primary key; source events are preserved because duplicate-looking rows may be legitimate.

## Model grains

* `stg_events`: one source row; scan only the fixed suffix range.
* `fct_purchases`: one valid global transaction ID; earliest observed row. Unlinked transactions remain included in transaction-date revenue and are excluded from session-linked revenue.
* `int_sessions`: one user/session pair; session date is earliest timestamp's property date. Sessions can cross midnight. Revenue reconciles only to purchases linked to valid sessions.
* `int_users`: one valid pseudonymous user; first observation across **all** events, including events without valid session IDs. Session count can be zero.
* Daily mart: one calendar date; user activity is event-date based; sessions are start-date based; transaction revenue is purchase-date based. These dates are deliberately not interchangeable.
* Funnel: grain × stage. Ordered sessions require strictly increasing event timestamps. Unordered users are reach counts, with no stage-to-stage conversion or dropoff claims.
* Retention: cohort week × dimension × segment × exact-day horizon. Eligible denominator differs by horizon. A partially mature week is not silently treated as a fully observed week.
* Segment mart: session date × dimension × segment. Sum within one dimension only.
* Experiment mart: eligibility date × transition. Each user contributes at most one exposure per transition and one same-session binary outcome. The last source day is excluded; sessions ending on that day are excluded too.

## Metrics

`src/metrics.py` is the machine-readable metric dictionary; it generates the site table and is included in `report.json`. It records grain, SQL, numerator, denominator, exclusions and caveat. Purchasing users is a **candidate** north star, subject to identity and transaction audit. Revenue/user and AOV require a missing-revenue coverage review; incomplete sums are observed amounts, not full business revenue. Input session flags are unordered; the sequential funnel is a different metric.

Minimum checkout denominator for segment comparisons: 100. Wilson intervals describe sampling uncertainty conditional on observed rows; sessions from the same user are not independent, so they are not a confirmatory significance test. The threshold is a screening choice, not evidence of practical importance.

## Retention / leakage

Primary definition: any event on the exact Nth property-local calendar day after the first observed event, for N in {1, 7, 14, 30}. Eligibility requires `first_observed_date + N <= 2021-01-31`. Do not add future information to acquisition dimensions. First-session behavior is only classified if the first session ends on the first-observed day; cross-day sessions receive a separate exclusion category. Associations with subsequent return are not causal effects.

## Freshness

This is a frozen historical export: source-age alerts are disabled. A production adaptation would verify daily partition arrival, ingestion delay, event-volume completeness and late-arrival changes; replay at least the documented late-arrival window before closing partitions. Google documents updates to daily exports for up to three days. Define freshness against ingestion timestamps and an agreed SLA, not against these historical event dates.

Sources: [Google dataset](https://developers.google.com/analytics/bigquery/web-ecommerce-demo-dataset), [GA4 export schema](https://support.google.com/analytics/answer/7029846).
