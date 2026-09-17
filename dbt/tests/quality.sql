WITH checks AS (
-- Nonzero failures block publication. Source conflicts are quarantined, never ignored.
SELECT 'session_key_unique' AS test, COUNT(*)-COUNT(DISTINCT session_id) AS failures FROM {{ ref('int_sessions') }}
UNION ALL SELECT 'user_key_unique',COUNT(*)-COUNT(DISTINCT user_pseudo_id) FROM {{ ref('int_users') }}
UNION ALL SELECT 'transaction_unique',COUNT(*)-COUNT(DISTINCT transaction_id) FROM {{ ref('fct_purchases') }}
UNION ALL SELECT 'session_time_order',COUNTIF(session_start>session_end OR session_id IS NULL) FROM {{ ref('int_sessions') }}
UNION ALL SELECT 'ordered_funnel',COUNTIF((purchase_ts IS NOT NULL AND checkout_ts IS NULL)
 OR (checkout_ts IS NOT NULL AND cart_ts IS NULL) OR (cart_ts IS NOT NULL AND view_ts IS NULL)) FROM {{ ref('int_sessions') }}
UNION ALL SELECT 'negative_revenue',COUNTIF(revenue_usd<0) FROM {{ ref('fct_purchases') }}
UNION ALL SELECT 'transaction_conflicts_in_accepted_facts',COUNT(*) FROM (
 SELECT transaction_id FROM {{ ref('stg_events') }} WHERE event_name='purchase'
 AND transaction_id IS NOT NULL AND TRIM(transaction_id) NOT IN ('','<Other>','(not set)','(direct)')
 GROUP BY transaction_id HAVING COUNT(DISTINCT user_pseudo_id)>1 OR COUNT(DISTINCT revenue_usd)>1) conflicts
 JOIN {{ ref('fct_purchases') }} USING(transaction_id)
UNION ALL SELECT 'session_event_reconciliation',ABS(
 (SELECT COUNT(*) FROM {{ ref('stg_events') }} WHERE session_id IS NOT NULL)
 -(SELECT COALESCE(SUM(events),0) FROM {{ ref('int_sessions') }}))
UNION ALL SELECT 'transaction_reconciliation',ABS(
 (SELECT COUNT(*) FROM (SELECT transaction_id FROM {{ ref('stg_events') }} WHERE event_name='purchase'
 AND transaction_id IS NOT NULL AND TRIM(transaction_id) NOT IN ('','<Other>','(not set)','(direct)')
 GROUP BY transaction_id HAVING COUNT(DISTINCT user_pseudo_id)<=1 AND COUNT(DISTINCT revenue_usd)<=1))
 -(SELECT COUNT(*) FROM {{ ref('fct_purchases') }}))
UNION ALL SELECT 'cohort_bounds',COUNTIF(first_observed_date<DATE '{{ var("start_date", "2020-11-01") }}' OR first_observed_date>DATE '{{ var("end_date", "2021-01-31") }}') FROM {{ ref('int_users') }}
UNION ALL SELECT 'retention_subset',COUNTIF(returned_users>eligible_users OR eligible_users<=0) FROM {{ ref('mart_retention') }}
UNION ALL SELECT 'critical_event_fields',COUNTIF(event_date IS NULL OR event_timestamp IS NULL OR event_name IS NULL) FROM {{ ref('stg_events') }}
UNION ALL SELECT 'cohort_activity_order',COUNTIF(e.event_date<u.first_observed_date)
 FROM {{ ref('stg_events') }} e JOIN {{ ref('int_users') }} u USING(user_pseudo_id)
UNION ALL SELECT 'first_session_chronology',COUNTIF(first_session.session_date<first_observed_date)
 FROM {{ ref('int_users') }}
UNION ALL SELECT 'daily_session_reconciliation',ABS(
 (SELECT SUM(sessions) FROM {{ ref('mart_daily_product_metrics') }})-(SELECT COUNT(*) FROM {{ ref('int_sessions') }}))
UNION ALL SELECT 'daily_transaction_reconciliation',ABS(
 (SELECT SUM(transactions) FROM {{ ref('mart_daily_product_metrics') }})-(SELECT COUNT(*) FROM {{ ref('fct_purchases') }}))
UNION ALL SELECT 'observed_date_coverage',ABS((DATE_DIFF(DATE '{{ var("end_date", "2021-01-31") }}', DATE '{{ var("start_date", "2020-11-01") }}', DAY)+1)-COUNT(DISTINCT event_date)) FROM {{ ref('stg_events') }}

) SELECT * FROM checks WHERE failures>0
