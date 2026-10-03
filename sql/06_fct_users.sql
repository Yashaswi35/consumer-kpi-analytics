-- One row per user: cohort assignment, first-session attributes, D1/D7/D30 return flags.
-- New users = first touch inside the data window (or unknown first touch).
WITH bounds AS (SELECT MAX(session_date) AS max_date FROM fct_sessions),
first_sess AS (
  SELECT user_pseudo_id,
         MIN(session_date)               AS first_seen_date,
         min_by(device, session_start)   AS first_device,
         min_by(medium, session_start)   AS first_medium
  FROM fct_sessions
  GROUP BY user_pseudo_id
),
ft AS (
  SELECT user_pseudo_id, MIN(first_touch_date) AS first_touch_date
  FROM events_clean GROUP BY user_pseudo_id
),
days AS (SELECT DISTINCT user_pseudo_id, session_date FROM fct_sessions)
SELECT
  f.user_pseudo_id, f.first_seen_date, ft.first_touch_date,
  CAST(date_trunc('WEEK', f.first_seen_date) AS DATE) AS cohort_week,
  f.first_device, f.first_medium,
  CASE WHEN ft.first_touch_date IS NULL OR ft.first_touch_date >= DATE'2020-11-01'
       THEN 1 ELSE 0 END AS is_new_user,
  MAX(CASE WHEN datediff(d.session_date, f.first_seen_date) = 1 THEN 1 ELSE 0 END)              AS returned_d1,
  MAX(CASE WHEN datediff(d.session_date, f.first_seen_date) BETWEEN 1 AND 7 THEN 1 ELSE 0 END)  AS returned_d7,
  MAX(CASE WHEN datediff(d.session_date, f.first_seen_date) BETWEEN 1 AND 30 THEN 1 ELSE 0 END) AS returned_d30,
  CASE WHEN datediff(MAX(b.max_date), f.first_seen_date) >= 7  THEN 1 ELSE 0 END AS d7_eligible,
  CASE WHEN datediff(MAX(b.max_date), f.first_seen_date) >= 30 THEN 1 ELSE 0 END AS d30_eligible
FROM first_sess f
JOIN days d ON d.user_pseudo_id = f.user_pseudo_id
LEFT JOIN ft ON ft.user_pseudo_id = f.user_pseudo_id
CROSS JOIN bounds b
GROUP BY f.user_pseudo_id, f.first_seen_date, ft.first_touch_date, f.first_device, f.first_medium
