WITH e AS (SELECT * FROM {{ ref('stg_events') }})
SELECT 'overview' AS section, 'all' AS label, TO_JSON_STRING(STRUCT(
 COUNT(*) AS events, MIN(event_date) AS min_date, MAX(event_date) AS max_date,
 COUNT(DISTINCT IF(valid_user,user_pseudo_id,NULL)) AS users,
 COUNT(DISTINCT session_id) AS sessions, COUNTIF(event_name='purchase') AS purchase_events,
 COUNTIF(session_id IS NULL) AS missing_session_events,
 COUNTIF(NOT valid_user) AS invalid_user_events,
 COUNT(*)-COUNT(DISTINCT event_fingerprint) AS repeated_fingerprints,
 COUNTIF(duplicate_parameter_keys>0) AS events_with_duplicate_parameter_keys,
 COUNTIF(event_name='purchase' AND revenue_usd IS NULL) AS purchases_missing_usd,
 COUNTIF(event_name='purchase' AND (transaction_id IS NULL OR TRIM(transaction_id) IN ('','<Other>','(not set)','(direct)'))) AS invalid_transaction_events,
 COUNTIF(revenue_usd<0) AS negative_revenue_events,
 COUNTIF(refund_usd IS NOT NULL) AS refund_values_present)) AS detail FROM e
UNION ALL
SELECT 'event_names', event_name, TO_JSON_STRING(STRUCT(COUNT(*) AS events,
 COUNT(DISTINCT IF(valid_user,user_pseudo_id,NULL)) AS users)) FROM e GROUP BY event_name
UNION ALL
SELECT 'dimensions', d.dimension, TO_JSON_STRING(STRUCT(d.value,COUNT(*) AS events))
FROM e, UNNEST([STRUCT('device' AS dimension,device AS value),STRUCT('country',country),
STRUCT('source',source),STRUCT('medium',medium)]) d GROUP BY d.dimension,d.value
UNION ALL
SELECT 'transaction_duplicates','all',TO_JSON_STRING(STRUCT(COUNT(*) AS repeated_ids,
 SUM(events) AS events,COUNTIF(owners>1) AS conflicting_owner_ids,COUNTIF(revenue_values>1) AS conflicting_revenue_ids))
FROM (SELECT transaction_id,COUNT(*) AS events,COUNT(DISTINCT user_pseudo_id) AS owners,
 COUNT(DISTINCT revenue_usd) AS revenue_values FROM e WHERE event_name='purchase'
 GROUP BY transaction_id HAVING COUNT(*)>1)
UNION ALL
SELECT 'ecommerce_coverage', required, TO_JSON_STRING(STRUCT(COUNTIF(e.event_name=required) AS events))
FROM UNNEST(['session_start','page_view','view_item','add_to_cart','begin_checkout',
'add_shipping_info','add_payment_info','purchase']) required CROSS JOIN e GROUP BY required
