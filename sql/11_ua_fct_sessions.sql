-- Standardize UA sessions to the same shape as the GA4 fct_sessions mart.
-- UA can repeat a session row across daily tables, so dedupe on user + visit + date.
WITH typed AS (
  SELECT
    CONCAT(user_id, '-', CAST(visit_id AS STRING), '-', date)  AS session_key,
    user_id                                                    AS user_pseudo_id,
    to_date(date, 'yyyyMMdd')                                  AS session_date,
    COALESCE(NULLIF(lower(trim(device)), ''), 'unknown')       AS device,
    CASE WHEN medium IS NULL OR trim(medium) = '' THEN 'unknown'
         ELSE lower(trim(medium)) END                          AS medium,
    COALESCE(NULLIF(trim(country), ''), 'unknown')             AS country,
    CASE WHEN has_view_item      THEN 1 ELSE 0 END             AS has_view_item,
    CASE WHEN has_add_to_cart    THEN 1 ELSE 0 END             AS has_add_to_cart,
    CASE WHEN has_begin_checkout THEN 1 ELSE 0 END             AS has_begin_checkout,
    CASE WHEN COALESCE(transactions, 0) > 0 THEN 1 ELSE 0 END  AS has_purchase,
    COALESCE(transactions, 0)                                  AS n_transactions,
    COALESCE(total_transaction_revenue, 0) / 1000000.0         AS revenue,
    ROW_NUMBER() OVER (PARTITION BY user_id, visit_id, date ORDER BY visit_start_time) AS rn
  FROM raw_ua
)
SELECT session_key, user_pseudo_id, session_date, device, medium, country,
       has_view_item, has_add_to_cart, has_begin_checkout, has_purchase, n_transactions, revenue
FROM typed
WHERE rn = 1
