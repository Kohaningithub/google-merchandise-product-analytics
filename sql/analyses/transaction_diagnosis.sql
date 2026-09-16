-- Aggregate-only reconciliation of purchase events with valid transaction facts.
WITH ids AS (
 SELECT transaction_id,COUNT(*) AS events,COUNT(DISTINCT user_pseudo_id) AS owners,
 COUNT(DISTINCT revenue_usd) AS revenue_values,COUNT(DISTINCT session_id) AS sessions,
 MIN(revenue_usd) AS minimum_usd,MAX(revenue_usd) AS maximum_usd
 FROM {{ ref('stg_events') }} WHERE event_name='purchase' AND transaction_id IS NOT NULL
 AND TRIM(transaction_id) NOT IN ('','<Other>','(not set)','(direct)') GROUP BY transaction_id
)
SELECT CASE WHEN owners>1 OR revenue_values>1 THEN 'conflicting'
 WHEN events>1 THEN 'consistent_repeats' ELSE 'single' END AS status,
 COUNT(*) AS transaction_ids,SUM(events) AS source_purchase_events,
 SUM(minimum_usd) AS sum_minimum_usd,SUM(maximum_usd) AS sum_maximum_usd,
 COUNTIF(sessions>1) AS cross_session_ids
FROM ids GROUP BY status ORDER BY status
