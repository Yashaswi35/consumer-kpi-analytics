-- One row per session with engagement, funnel flags, and revenue.
-- Note: GA4 traffic_source is user-scoped (first acquisition), so medium = acquisition medium.
WITH agg AS (
  SELECT
    session_key,
    MIN(user_pseudo_id)                                              AS user_pseudo_id,
    MIN(event_date)                                                  AS session_date,
    MIN(event_ts)                                                    AS session_start,
    (MAX(event_timestamp) - MIN(event_timestamp)) / 1000000.0        AS duration_sec,
    COALESCE(MAX(CASE WHEN device  <> 'unknown' THEN device  END), 'unknown') AS device,
    COALESCE(MAX(CASE WHEN medium  <> 'unknown' THEN medium  END), 'unknown') AS medium,
    COALESCE(MAX(CASE WHEN country <> 'unknown' THEN country END), 'unknown') AS country,
    COUNT(*)                                                         AS n_events,
    SUM(CASE WHEN event_name = 'page_view'      THEN 1 ELSE 0 END)   AS n_page_views,
    MAX(CASE WHEN event_name = 'view_item'      THEN 1 ELSE 0 END)   AS has_view_item,
    MAX(CASE WHEN event_name = 'add_to_cart'    THEN 1 ELSE 0 END)   AS has_add_to_cart,
    MAX(CASE WHEN event_name = 'begin_checkout' THEN 1 ELSE 0 END)   AS has_begin_checkout,
    MAX(CASE WHEN event_name = 'purchase'       THEN 1 ELSE 0 END)   AS has_purchase,
    COUNT(DISTINCT CASE WHEN event_name = 'purchase' THEN transaction_id END) AS n_transactions,
    COALESCE(SUM(CASE WHEN event_name = 'purchase' THEN purchase_revenue_in_usd END), 0) AS revenue
  FROM events_clean
  GROUP BY session_key
)
SELECT *,
  CASE WHEN n_page_views <= 1 AND has_view_item = 0 AND has_add_to_cart = 0
            AND has_begin_checkout = 0 AND has_purchase = 0 THEN 1 ELSE 0 END AS is_bounce,
  CASE WHEN has_purchase = 1 AND has_begin_checkout = 0 THEN 1 ELSE 0 END AS is_orphan_purchase
FROM agg
