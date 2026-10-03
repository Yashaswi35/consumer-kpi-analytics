"""Step 2: Run the Spark SQL pipeline: raw -> clean -> sessions -> marts.

Run:
  python pipeline.py                     # full history
  python pipeline.py --start 2021-01-01  # restrict the window (recurring / incremental runs)
"""
import argparse
import json
from pathlib import Path

from pyspark.sql import SparkSession

SQL_DIR = Path("sql")
GOLD_DIR = Path("data/gold")
TABLEAU_DIR = Path("tableau")
OUTPUT_DIR = Path("output")

# (view name, sql file, write to gold, export to tableau)
STAGES = [
    ("events_clean",         "01_events_clean.sql",         True,  False),
    ("sessions_derived",     "02_sessions_derived.sql",     False, False),
    ("session_match",        "03_session_match.sql",        True,  False),
    ("fct_sessions",         "04_fct_sessions.sql",         True,  True),
    ("fct_funnel_daily",     "05_fct_funnel_daily.sql",     True,  True),
    ("fct_users",            "06_fct_users.sql",            True,  True),
    ("fct_retention_cohort", "07_fct_retention_cohort.sql", True,  True),
    ("kpi_daily",            "08_kpi_daily.sql",            True,  True),
    ("kpi_weekly",           "09_kpi_weekly.sql",           True,  True),
]


def get_spark():
    return (SparkSession.builder
            .appName("consumer-kpi-analytics")
            .master("local[*]")
            .config("spark.driver.memory", "6g")
            .config("spark.sql.shuffle.partitions", "16")
            .config("spark.sql.session.timeZone", "UTC")
            .getOrCreate())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", help="YYYY-MM-DD, inclusive")
    ap.add_argument("--end", help="YYYY-MM-DD, inclusive")
    args = ap.parse_args()

    spark = get_spark()
    spark.sparkContext.setLogLevel("WARN")
    for d in (GOLD_DIR, TABLEAU_DIR, OUTPUT_DIR):
        d.mkdir(parents=True, exist_ok=True)

    raw = spark.read.parquet("data/raw")
    raw.createOrReplaceTempView("raw_all")
    where = []
    if args.start:
        where.append(f"to_date(event_date, 'yyyyMMdd') >= DATE'{args.start}'")
    if args.end:
        where.append(f"to_date(event_date, 'yyyyMMdd') <= DATE'{args.end}'")
    filt = f"WHERE {' AND '.join(where)}" if where else ""
    spark.sql(f"SELECT * FROM raw_all {filt}").createOrReplaceTempView("raw_events")

    # Data quality accounting for the bronze -> silver step
    dq = spark.sql("""
        SELECT COUNT(*) AS raw_rows,
               SUM(CASE WHEN user_pseudo_id IS NULL THEN 1 ELSE 0 END) AS null_user_rows,
               SUM(CASE WHEN ga_session_id IS NULL THEN 1 ELSE 0 END)  AS null_session_rows,
               SUM(CASE WHEN device IS NULL OR trim(device) = '' THEN 1 ELSE 0 END) AS null_device_rows,
               SUM(CASE WHEN medium IN ('<Other>', '(data deleted)') THEN 1 ELSE 0 END) AS redacted_medium_rows
        FROM raw_events
    """).first().asDict()

    for name, file, to_gold, to_tableau in STAGES:
        sql = (SQL_DIR / file).read_text()
        df = spark.sql(sql)
        if to_gold:
            out = GOLD_DIR / name
            df.write.mode("overwrite").parquet(str(out))
            # Re-read from disk so downstream stages don't recompute the whole lineage
            df = spark.read.parquet(str(out))
        else:
            df = df.cache()
        df.createOrReplaceTempView(name)
        n = df.count()
        print(f"[{name}] {n:,} rows")
        if to_tableau:
            df.toPandas().to_csv(TABLEAU_DIR / f"{name}.csv", index=False)

    clean_rows = spark.table("events_clean").count()
    eligible = dq["raw_rows"] - dq["null_user_rows"] - dq["null_session_rows"]
    dq["clean_rows"] = clean_rows
    dq["duplicate_rows_removed"] = max(eligible - clean_rows, 0)
    m = spark.sql("SELECT COUNT(*) AS ga_sessions, AVG(is_exact_match) AS match_rate FROM session_match").first()
    dq["ga_sessions"] = m["ga_sessions"]
    dq["derived_sessions"] = spark.sql("SELECT COUNT(DISTINCT derived_session_id) FROM sessions_derived").first()[0]
    dq["sessionization_match_rate"] = round(float(m["match_rate"]), 4)
    dq["users"] = spark.table("fct_users").count()

    (OUTPUT_DIR / "dq_summary.json").write_text(json.dumps(dq, indent=2, default=str))
    print(json.dumps(dq, indent=2, default=str))
    spark.stop()


if __name__ == "__main__":
    main()
