SELECT
  CAST(date_trunc('WEEK', session_date) AS DATE) AS week_start,
  COUNT(DISTINCT user_pseudo_id)                 AS wau,
  COUNT(*)                                       AS sessions,
  SUM(has_purchase) / COUNT(*)                   AS conversion_rate,
  SUM(revenue)                                   AS revenue
FROM fct_sessions
GROUP BY CAST(date_trunc('WEEK', session_date) AS DATE)
