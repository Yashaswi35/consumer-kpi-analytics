SELECT
  session_date,
  COUNT(DISTINCT user_pseudo_id)                                  AS dau,
  COUNT(*)                                                        AS sessions,
  COUNT(*) / COUNT(DISTINCT user_pseudo_id)                       AS sessions_per_user,
  AVG(n_events)                                                   AS events_per_session,
  percentile_approx(duration_sec, 0.5)                            AS median_session_sec,
  AVG(is_bounce)                                                  AS bounce_rate,
  SUM(has_purchase) / COUNT(*)                                    AS conversion_rate,
  SUM(n_transactions)                                             AS transactions,
  SUM(revenue)                                                    AS revenue,
  SUM(revenue) / NULLIF(SUM(n_transactions), 0)                   AS aov
FROM fct_sessions
GROUP BY session_date
