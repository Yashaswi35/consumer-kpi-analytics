-- A GA4 session is an exact match when it maps to exactly one derived session
-- and that derived session contains no other GA4 session.
WITH ga_map AS (
  SELECT session_key,
         COUNT(DISTINCT derived_session_id) AS n_derived,
         MIN(derived_session_id)            AS derived_session_id
  FROM sessions_derived
  GROUP BY session_key
),
derived_map AS (
  SELECT derived_session_id, COUNT(DISTINCT session_key) AS n_ga
  FROM sessions_derived
  GROUP BY derived_session_id
)
SELECT g.session_key, g.n_derived, d.n_ga,
       CASE WHEN g.n_derived = 1 AND d.n_ga = 1 THEN 1 ELSE 0 END AS is_exact_match
FROM ga_map g
JOIN derived_map d ON g.derived_session_id = d.derived_session_id
