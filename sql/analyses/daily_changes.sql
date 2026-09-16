SELECT metric_date, sessions, session_conversion,
 LAG(session_conversion,7) OVER(ORDER BY metric_date) AS previous_week_conversion,
 AVG(session_conversion) OVER(ORDER BY metric_date ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING) AS trailing_mean
FROM {{ ref('mart_daily_product_metrics') }} ORDER BY metric_date
