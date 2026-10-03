-- Independent sessionization: a new session starts after 30+ minutes of inactivity.
-- Used to validate GA4's native ga_session_id (see 03_session_match).
WITH gaps AS (
  SELECT
    user_pseudo_id, session_key, event_ts, event_timestamp,
    CASE WHEN LAG(event_timestamp) OVER w IS NULL
           OR (event_timestamp - LAG(event_timestamp) OVER w) > 1800 * 1000000
         THEN 1 ELSE 0 END AS is_new_session
  FROM events_clean
  WINDOW w AS (PARTITION BY user_pseudo_id ORDER BY event_timestamp)
)
SELECT
  user_pseudo_id, session_key, event_ts,
  CONCAT(user_pseudo_id, '-d',
    CAST(SUM(is_new_session) OVER (
      PARTITION BY user_pseudo_id ORDER BY event_timestamp
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS STRING)) AS derived_session_id
FROM gaps
