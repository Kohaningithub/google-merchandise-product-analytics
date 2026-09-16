WITH activity AS (
 SELECT user_pseudo_id, MIN(event_date) AS first_observed_date, COUNT(DISTINCT event_date) AS active_days,
 ARRAY_AGG(STRUCT(device, country, source, medium) ORDER BY event_timestamp, event_fingerprint LIMIT 1)[OFFSET(0)] AS first_event
 FROM {{ ref('stg_events') }} WHERE valid_user GROUP BY user_pseudo_id
), sessions AS (
 SELECT user_pseudo_id, COUNT(*) AS sessions,
 ARRAY_AGG(STRUCT(session_id, session_date, session_end_date, added_cart, purchase_event) ORDER BY session_start, session_id LIMIT 1)[OFFSET(0)] AS first_session
 FROM {{ ref('int_sessions') }} GROUP BY user_pseudo_id
), money AS (
 SELECT user_pseudo_id, COUNT(*) AS purchases, SUM(revenue_usd) AS revenue_usd
 FROM {{ ref('fct_purchases') }} GROUP BY user_pseudo_id
)
SELECT a.*, COALESCE(s.sessions,0) AS sessions, s.first_session,
 COALESCE(m.purchases,0) AS purchases, m.revenue_usd
FROM activity a LEFT JOIN sessions s USING(user_pseudo_id) LEFT JOIN money m USING(user_pseudo_id)
