-- Item revenue is a separate grain; never join repeated items into session denominators.
SELECT COALESCE(i.item_category,'unknown') AS category, COUNT(DISTINCT transaction_id) AS transactions,
 SUM(i.quantity) AS units, SUM(i.item_revenue_in_usd) AS observed_item_revenue_usd,
 DENSE_RANK() OVER(ORDER BY SUM(i.item_revenue_in_usd) DESC) AS revenue_rank
FROM {{ ref('fct_purchases') }}, UNNEST(items) i GROUP BY category
