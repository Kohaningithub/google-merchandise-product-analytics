-- Exact-day return. Dimensions are frozen at first observation / first session.
WITH activity AS (
 SELECT DISTINCT user_pseudo_id,event_date FROM {{ ref('stg_events') }} WHERE valid_user
), eligible AS (
 SELECT u.*, horizon FROM {{ ref('int_users') }} u CROSS JOIN UNNEST([1,7,14,30]) horizon
 WHERE DATE_ADD(first_observed_date,INTERVAL horizon DAY)<=DATE '2021-01-31'
), expanded AS (
 SELECT e.*, d.dimension, COALESCE(d.segment,'unknown') AS segment,
 a.user_pseudo_id IS NOT NULL AS returned
 FROM eligible e LEFT JOIN activity a ON e.user_pseudo_id=a.user_pseudo_id
 AND a.event_date=DATE_ADD(e.first_observed_date,INTERVAL e.horizon DAY)
 CROSS JOIN UNNEST([STRUCT('all' AS dimension,'all' AS segment),
 STRUCT('device',e.first_event.device), STRUCT('country',e.first_event.country),
 STRUCT('source_medium',CONCAT(COALESCE(e.first_event.source,'unknown'),' / ',COALESCE(e.first_event.medium,'unknown'))),
 STRUCT('first_session_behavior',CASE WHEN e.first_session.session_end_date>e.first_observed_date THEN 'cross_day_session_excluded'
 WHEN e.first_session.purchase_event THEN 'purchase'
 WHEN e.first_session.added_cart THEN 'cart_without_purchase'
 WHEN e.first_session.session_id IS NULL THEN 'no_valid_session' ELSE 'neither' END)]) d
)
SELECT DATE_TRUNC(first_observed_date,WEEK(MONDAY)) AS cohort_week, dimension, segment, horizon,
 COUNT(*) AS eligible_users, COUNTIF(returned) AS returned_users,
 SAFE_DIVIDE(COUNTIF(returned),COUNT(*)) AS retention
FROM expanded GROUP BY cohort_week, dimension, segment, horizon
