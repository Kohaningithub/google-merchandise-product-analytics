-- Preserve source rows; fingerprints flag suspicious repeats, not unique event IDs.
WITH flat AS (
  SELECT PARSE_DATE('%Y%m%d', event_date) AS event_date,
    event_timestamp, event_name, NULLIF(user_pseudo_id, '') AS user_pseudo_id,
    (SELECT MAX(value.int_value) FROM UNNEST(event_params) WHERE key='ga_session_id') AS ga_session_id,
    (SELECT MAX(value.int_value) FROM UNNEST(event_params) WHERE key='ga_session_number') AS ga_session_number,
    (SELECT MAX(value.string_value) FROM UNNEST(event_params) WHERE key='page_location') AS page_location,
    (SELECT MAX(value.string_value) FROM UNNEST(event_params) WHERE key='currency') AS currency,
    (SELECT MAX(COALESCE(value.double_value, CAST(value.int_value AS FLOAT64)))
      FROM UNNEST(event_params) WHERE key='value') AS parameter_value,
    (SELECT COUNT(*)-COUNT(DISTINCT key) FROM UNNEST(event_params)) AS duplicate_parameter_keys,
    device.category AS device, geo.country AS country,
    traffic_source.source AS source, traffic_source.medium AS medium,
    ecommerce.transaction_id AS transaction_id,
    ecommerce.purchase_revenue_in_usd AS revenue_usd,
    ecommerce.refund_value_in_usd AS refund_usd,
    ARRAY(SELECT AS STRUCT item_id, item_name, item_category, quantity, item_revenue_in_usd
          FROM UNNEST(items)) AS items,
    TO_HEX(SHA256(TO_JSON_STRING(STRUCT(event_timestamp, event_name, user_pseudo_id,
      event_params, ecommerce)))) AS event_fingerprint
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  WHERE _TABLE_SUFFIX BETWEEN '20201101' AND '20210131'
)
SELECT *, CASE WHEN user_pseudo_id IS NOT NULL AND user_pseudo_id NOT IN ('<Other>', '(not set)')
  AND ga_session_id IS NOT NULL THEN TO_JSON_STRING(STRUCT(user_pseudo_id, ga_session_id)) END AS session_id,
  user_pseudo_id IS NOT NULL AND user_pseudo_id NOT IN ('<Other>', '(not set)') AS valid_user
FROM flat
