-- Global transaction-ID deduplication. Conflicting owners/values fail validation.
-- Missing currency-converted revenue remains NULL, never imputed as zero.
SELECT transaction_id, event_date AS purchase_date, event_timestamp, user_pseudo_id,
       session_id, revenue_usd, currency, items
FROM {{ ref('stg_events') }}
WHERE event_name='purchase' AND transaction_id IS NOT NULL
  AND TRIM(transaction_id) NOT IN ('', '<Other>', '(not set)', '(direct)')
QUALIFY ROW_NUMBER() OVER (PARTITION BY transaction_id ORDER BY event_timestamp, event_fingerprint)=1
