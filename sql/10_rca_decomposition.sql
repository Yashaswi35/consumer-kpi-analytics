-- Mix vs rate decomposition of the change in session conversion rate.
-- mix_effect + rate_effect summed over segments equals the total CVR change exactly.
WITH p AS (
  SELECT
    CASE WHEN session_date BETWEEN DATE'{b0}' AND DATE'{b1}' THEN 'baseline'
         WHEN session_date BETWEEN DATE'{c0}' AND DATE'{c1}' THEN 'comparison' END AS period,
    {dim} AS segment,
    has_purchase
  FROM fct_sessions
),
seg AS (
  SELECT period, segment, COUNT(*) AS sessions, SUM(has_purchase) AS conversions
  FROM p WHERE period IS NOT NULL
  GROUP BY period, segment
),
tot AS (SELECT period, SUM(sessions) AS total FROM seg GROUP BY period),
s AS (
  SELECT seg.period, seg.segment, seg.sessions,
         seg.sessions / tot.total        AS share,
         seg.conversions / seg.sessions  AS cvr
  FROM seg JOIN tot ON seg.period = tot.period
),
w AS (
  SELECT segment,
    MAX(CASE WHEN period = 'baseline'   THEN sessions END) AS sessions_b,
    MAX(CASE WHEN period = 'comparison' THEN sessions END) AS sessions_c,
    MAX(CASE WHEN period = 'baseline'   THEN share END)    AS share_b,
    MAX(CASE WHEN period = 'comparison' THEN share END)    AS share_c,
    MAX(CASE WHEN period = 'baseline'   THEN cvr END)      AS cvr_b,
    MAX(CASE WHEN period = 'comparison' THEN cvr END)      AS cvr_c
  FROM s GROUP BY segment
)
SELECT
  '{dim}' AS dimension, segment, sessions_b, sessions_c, share_b, share_c, cvr_b, cvr_c,
  (COALESCE(share_c, 0) - COALESCE(share_b, 0)) * COALESCE(cvr_b, 0)  AS mix_effect,
  COALESCE(share_c, 0) * (COALESCE(cvr_c, 0) - COALESCE(cvr_b, 0))    AS rate_effect
FROM w
