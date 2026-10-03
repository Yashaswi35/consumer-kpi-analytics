-- Weekly conversion for both seasons, aligned on the Monday of Thanksgiving week (season_week 0).
-- Weeks 0 to 3 are the holiday peak window, weeks 4 to 7 the post-holiday window.
WITH both AS (
  SELECT 'GA4 2020-21' AS season, session_date, has_purchase, revenue,
         DATE'2020-11-23' AS anchor
  FROM ga4_sessions
  UNION ALL
  SELECT 'UA 2016-17' AS season, session_date, has_purchase, revenue,
         DATE'2016-11-21' AS anchor
  FROM ua_fct_sessions
  WHERE session_date BETWEEN DATE'2016-10-31' AND DATE'2017-01-31'
)
SELECT
  season,
  CAST(FLOOR(datediff(session_date, anchor) / 7.0) AS INT) AS season_week,
  MIN(session_date)                                        AS week_start,
  COUNT(*)                                                 AS sessions,
  SUM(has_purchase) / COUNT(*)                             AS conversion_rate,
  SUM(revenue)                                             AS revenue
FROM both
GROUP BY season, CAST(FLOOR(datediff(session_date, anchor) / 7.0) AS INT)
