SELECT
  session_date, device, medium,
  COUNT(*)                 AS sessions,
  SUM(has_view_item)       AS view_item_sessions,
  SUM(has_add_to_cart)     AS add_to_cart_sessions,
  SUM(has_begin_checkout)  AS checkout_sessions,
  SUM(has_purchase)        AS purchase_sessions,
  SUM(n_transactions)      AS transactions,
  SUM(revenue)             AS revenue
FROM fct_sessions
GROUP BY session_date, device, medium
