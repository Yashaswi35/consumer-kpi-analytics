"""Step 3: Validate the marts. Exits non-zero if any ERROR check fails.

Every check is a SQL query that returns the number of violating rows (0 = pass).
WARN checks are reported but don't fail the run (obfuscated GA4 data has known gaps).
"""
import json
import sys
from pathlib import Path

from pyspark.sql import SparkSession

GOLD = Path("data/gold")
TABLES = ["events_clean", "session_match", "fct_sessions", "fct_funnel_daily",
          "fct_users", "fct_retention_cohort", "kpi_daily", "kpi_weekly"]

CHECKS = [
    ("ERROR", "events_clean natural key is unique", """
        SELECT COUNT(*) FROM (
          SELECT user_pseudo_id, event_timestamp, event_name, ga_session_id
          FROM events_clean GROUP BY 1, 2, 3, 4 HAVING COUNT(*) > 1)"""),
    ("ERROR", "fct_sessions session_key is unique", """
        SELECT COUNT(*) - COUNT(DISTINCT session_key) FROM fct_sessions"""),
    ("ERROR", "session revenue reconciles to event revenue (within $1)", """
        SELECT CASE WHEN ABS(
          (SELECT SUM(revenue) FROM fct_sessions) -
          (SELECT COALESCE(SUM(purchase_revenue_in_usd), 0) FROM events_clean WHERE event_name = 'purchase')
        ) > 1 THEN 1 ELSE 0 END"""),
    ("ERROR", "session counts reconcile between fct_sessions and funnel mart", """
        SELECT CASE WHEN (SELECT COUNT(*) FROM fct_sessions) <>
                         (SELECT SUM(sessions) FROM fct_funnel_daily) THEN 1 ELSE 0 END"""),
    ("ERROR", "purchase_sessions <= sessions on every funnel row", """
        SELECT COUNT(*) FROM fct_funnel_daily WHERE purchase_sessions > sessions"""),
    ("ERROR", "retention week 0 equals 100%", """
        SELECT COUNT(*) FROM fct_retention_cohort WHERE week_number = 0 AND ABS(retention_rate - 1) > 1e-9"""),
    ("ERROR", "retention never exceeds 100%", """
        SELECT COUNT(*) FROM fct_retention_cohort WHERE retention_rate > 1"""),
    ("ERROR", "no negative session durations", """
        SELECT COUNT(*) FROM fct_sessions WHERE duration_sec < 0"""),
    ("WARN", "funnel rows where checkouts exceed add_to_cart", """
        SELECT COUNT(*) FROM fct_funnel_daily WHERE checkout_sessions > add_to_cart_sessions"""),
    ("WARN", "purchase sessions with no begin_checkout (orphan purchases)", """
        SELECT SUM(is_orphan_purchase) FROM fct_sessions"""),
    ("WARN", "sessions with unknown device", """
        SELECT COUNT(*) FROM fct_sessions WHERE device = 'unknown'"""),
    ("WARN", "days with event volume > 3 std devs from trailing 14-day mean", """
        SELECT COUNT(*) FROM (
          SELECT n,
                 AVG(n)    OVER (ORDER BY event_date ROWS BETWEEN 14 PRECEDING AND 1 PRECEDING) AS mu,
                 STDDEV(n) OVER (ORDER BY event_date ROWS BETWEEN 14 PRECEDING AND 1 PRECEDING) AS sd
          FROM (SELECT event_date, COUNT(*) AS n FROM events_clean GROUP BY event_date))
        WHERE sd > 0 AND ABS(n - mu) > 3 * sd"""),
]


def main():
    spark = (SparkSession.builder.appName("kpi-validate").master("local[*]")
             .config("spark.driver.memory", "4g").getOrCreate())
    spark.sparkContext.setLogLevel("WARN")
    for t in TABLES:
        spark.read.parquet(str(GOLD / t)).createOrReplaceTempView(t)

    results, errors = [], 0
    for level, name, sql in CHECKS:
        bad = spark.sql(sql).first()[0] or 0
        status = "PASS" if bad == 0 else ("FAIL" if level == "ERROR" else "FLAG")
        errors += status == "FAIL"
        results.append({"level": level, "check": name, "violations": int(bad), "status": status})
        print(f"{status:4}  [{level}] {name}: {bad}")

    Path("output").mkdir(exist_ok=True)
    Path("output/validation_report.json").write_text(json.dumps(results, indent=2))
    spark.stop()
    if errors:
        sys.exit(f"{errors} ERROR check(s) failed")
    print("All ERROR checks passed.")


if __name__ == "__main__":
    main()
