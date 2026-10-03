-- Weekly cohort retention for new users. Week 0 is 100% by construction.
WITH u AS (
  SELECT user_pseudo_id, cohort_week FROM fct_users WHERE is_new_user = 1
),
act AS (
  SELECT DISTINCT user_pseudo_id, CAST(date_trunc('WEEK', session_date) AS DATE) AS activity_week
  FROM fct_sessions
),
j AS (
  SELECT u.cohort_week,
         CAST(datediff(a.activity_week, u.cohort_week) / 7 AS INT) AS week_number,
         u.user_pseudo_id
  FROM u JOIN act a
    ON u.user_pseudo_id = a.user_pseudo_id AND a.activity_week >= u.cohort_week
),
sizes AS (SELECT cohort_week, COUNT(*) AS cohort_size FROM u GROUP BY cohort_week)
SELECT j.cohort_week, j.week_number,
       COUNT(DISTINCT j.user_pseudo_id)                 AS active_users,
       s.cohort_size,
       COUNT(DISTINCT j.user_pseudo_id) / s.cohort_size AS retention_rate
FROM j JOIN sizes s ON j.cohort_week = s.cohort_week
GROUP BY j.cohort_week, j.week_number, s.cohort_size
