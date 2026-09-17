# Prediction-time contract (defined before feature SQL)

One row per eligible session, predicted at its first `view_item` timestamp.
This event exists in the current audited staging schema and represents a useful
shopping-intent decision point. The population is product-viewing sessions, not
all visits. The target is any purchase event strictly after prediction in that
session; it is not accepted transaction revenue or a causal outcome.

Exclude sessions with a purchase at/before prediction (including timestamp ties).
Only events at/before prediction enter features. At the prediction timestamp,
include view_item rows but exclude other tied events because their order is unknown.
Context is frozen at the earliest timestamp/fingerprint among eligible events.
No cart/checkout events enter behavior counts. Product and category counts use only
eligible view_item arrays. Full-session fields are used exclusively for label and
censoring eligibility, never as inputs. Exclude sessions touching either source
boundary day and sessions spanning property-local dates; these conservative
exclusions reduce truncation and ensure outcomes end before the next split.
They limit generalization to same-day sessions; source obfuscation remains a limit.

Inputs: device, country, first-user acquisition source/medium, visitor_type proxy,
property-local day of week, UTC hour, early allowed-event count, page-view count,
search count, distinct viewed products/categories and time to first product view.
Source/medium are acquisition attributes, not session attribution. No raw URL,
campaign, user identifier or historical user aggregates are estimator inputs.
Historical aggregates are omitted because the short observation window makes
lifetime history misleading. SHA256 session keys support integrity checks; they
are pseudonymous and stay in ignored local artifacts/BigQuery, never the site.

Blocked inputs: target, purchase_event, purchase_ts, transaction_id, transactions,
revenue_usd, session_end, session_end_date, checkout_ts, added_cart, began_checkout,
user_pseudo_id, session_id, session_key, prediction_ts and any unlisted column.
An explicit feature allowlist is the actual enforcement mechanism.

Chronological protocol: train November 2–December 14; validation December 15–31;
test January 1–30. Validation is further divided: December 15–23 fits sigmoid
calibration; December 24–31 selects raw/calibrated boosting and compares baseline
using log loss (PR-AUC breaks ties). All preprocessing is fitted on train only.
Fixed estimator configurations, seed 42. Final test is evaluated after selection;
no refitting or tuning follows test inspection. Repeated users may cross splits;
this estimates future-session performance, not unseen-user generalization.

Actual split row counts and prevalence must be generated from the feature mart;
no real metrics can be inferred from the existing aggregate-only snapshots.
Replay training requires these windows; a short replay can build/validate features
without fitting a model. The default full window covers all three splits.
