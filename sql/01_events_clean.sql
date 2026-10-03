-- Typed, standardized, deduplicated events. One row per real event.
-- GA4 export has no event_id, so the natural key is (user, timestamp, event_name, session).
WITH typed AS (
  SELECT
    to_date(event_date, 'yyyyMMdd')                        AS event_date,
    timestamp_micros(event_timestamp)                      AS event_ts,
    event_timestamp,
    event_name,
    user_pseudo_id,
    CASE WHEN user_first_touch_timestamp IS NOT NULL
         THEN to_date(timestamp_micros(user_first_touch_timestamp)) END AS first_touch_date,
    CASE WHEN device IS NULL OR trim(device) = '' THEN 'unknown'
         ELSE lower(trim(device)) END                      AS device,
    CASE WHEN medium IS NULL OR trim(medium) = '' THEN 'unknown'
         WHEN medium IN ('<Other>', '(data deleted)') THEN 'redacted'
         ELSE lower(trim(medium)) END                      AS medium,
    COALESCE(NULLIF(trim(country), ''), 'unknown')         AS country,
    ga_session_id,
    transaction_id,
    purchase_revenue_in_usd
  FROM raw_events
  WHERE user_pseudo_id IS NOT NULL
    AND ga_session_id IS NOT NULL
),
ranked AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY user_pseudo_id, event_timestamp, event_name, ga_session_id
      ORDER BY event_timestamp) AS rn
  FROM typed
)
SELECT
  event_date, event_ts, event_timestamp, event_name, user_pseudo_id, first_touch_date,
  device, medium, country, ga_session_id, transaction_id, purchase_revenue_in_usd,
  CONCAT(user_pseudo_id, '-', CAST(ga_session_id AS STRING)) AS session_key
FROM ranked
WHERE rn = 1
