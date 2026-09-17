-- First-product-view prediction contract: docs/model-contract.md.
WITH boundaries AS (
 SELECT session_id, MIN(event_timestamp) AS session_start,
   MIN(event_date) AS first_date, MAX(event_date) AS last_date,
   MIN(IF(event_name='view_item', event_timestamp, NULL)) AS prediction_ts,
   MIN(IF(event_name='purchase', event_timestamp, NULL)) AS first_purchase_ts
 FROM {{ ref('stg_events') }} WHERE session_id IS NOT NULL GROUP BY session_id
), eligible AS (
 SELECT * FROM boundaries
 WHERE prediction_ts IS NOT NULL
   AND (first_purchase_ts IS NULL OR first_purchase_ts>prediction_ts)
   AND first_date=last_date
   AND first_date>DATE '{{ var("start_date", "2020-11-01") }}'
   AND last_date<DATE '{{ var("end_date", "2021-01-31") }}'
), early AS (
 SELECT e.*, s.prediction_ts, s.session_start, s.first_date,
   s.first_purchase_ts
 FROM {{ ref('stg_events') }} e JOIN eligible s USING(session_id)
 WHERE (e.event_timestamp<s.prediction_ts
        OR (e.event_timestamp=s.prediction_ts AND e.event_name='view_item'))
   AND e.event_name IN ('session_start','first_visit','page_view','view_item',
                        'view_item_list','view_search_results','search','user_engagement')
), behavior AS (
 SELECT session_id, first_date AS session_date, prediction_ts,
   CAST(first_purchase_ts IS NOT NULL AS INT64) AS target,
   ARRAY_AGG(STRUCT(device,country,source,medium,ga_session_number)
     ORDER BY event_timestamp,event_fingerprint LIMIT 1)[OFFSET(0)] AS context,
   COUNT(*) AS early_events, COUNTIF(event_name='page_view') AS early_page_views,
   COUNTIF(event_name IN ('search','view_search_results')) AS early_searches,
   (prediction_ts-session_start)/1000000.0 AS seconds_to_view
 FROM early GROUP BY session_id,first_date,prediction_ts,first_purchase_ts,session_start
), products AS (
 SELECT session_id, COUNT(DISTINCT NULLIF(i.item_id,'')) AS unique_products,
   COUNT(DISTINCT NULLIF(i.item_category,'')) AS category_diversity
 FROM early LEFT JOIN UNNEST(items) i ON TRUE
 WHERE event_name='view_item' GROUP BY session_id
)
SELECT TO_HEX(SHA256(b.session_id)) AS session_key, session_date, prediction_ts, target,
 COALESCE(context.device,'unknown') AS device, COALESCE(context.country,'unknown') AS country,
 COALESCE(context.source,'unknown') AS source, COALESCE(context.medium,'unknown') AS medium,
 CASE WHEN context.ga_session_number=1 THEN 'new_proxy'
      WHEN context.ga_session_number>1 THEN 'returning_proxy' ELSE 'unknown' END AS visitor_type,
 EXTRACT(DAYOFWEEK FROM session_date) AS day_of_week,
 EXTRACT(HOUR FROM TIMESTAMP_MICROS(prediction_ts)) AS hour_utc,
 early_events,early_page_views,early_searches,seconds_to_view,
 COALESCE(unique_products,0) AS unique_products, COALESCE(category_diversity,0) AS category_diversity
FROM behavior b LEFT JOIN products p USING(session_id)
