WITH checks AS (
SELECT 'nonempty' AS test, IF(COUNT(*)=0,1,0) AS failures FROM {{ ref('mart_conversion_features') }}
UNION ALL SELECT 'session_key',COUNT(*)-COUNT(DISTINCT session_key) FROM {{ ref('mart_conversion_features') }}
UNION ALL SELECT 'target',COUNTIF(target IS NULL OR target NOT IN (0,1)) FROM {{ ref('mart_conversion_features') }}
UNION ALL SELECT 'bounds',COUNTIF(early_events<1 OR seconds_to_view<0
 OR session_date<=DATE '{{ var("start_date", "2020-11-01") }}'
 OR session_date>=DATE '{{ var("end_date", "2021-01-31") }}') FROM {{ ref('mart_conversion_features') }}

) SELECT * FROM checks WHERE failures>0
