-- Quarantine ambiguous IDs before deduplication; never choose an arbitrary owner/value.
-- Missing currency-converted revenue remains NULL, never imputed as zero.
WITH candidates AS (
 SELECT * FROM {{ ref('stg_events') }}
 WHERE event_name='purchase' AND transaction_id IS NOT NULL
 AND TRIM(transaction_id) NOT IN ('', '<Other>', '(not set)', '(direct)')
), consistent_ids AS (
 SELECT transaction_id FROM candidates GROUP BY transaction_id
 HAVING COUNT(DISTINCT user_pseudo_id)<=1 AND COUNT(DISTINCT revenue_usd)<=1
)
SELECT transaction_id, event_date AS purchase_date, event_timestamp, user_pseudo_id,
       session_id, revenue_usd, currency, items
FROM candidates JOIN consistent_ids USING(transaction_id)
QUALIFY ROW_NUMBER() OVER (PARTITION BY transaction_id ORDER BY event_timestamp, event_fingerprint)=1
