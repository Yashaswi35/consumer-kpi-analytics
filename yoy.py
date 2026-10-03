"""Step 5: Test whether the 2020 holiday conversion pattern repeats in an independent year.

Both seasons are aligned on the Monday of Thanksgiving week (season week 0) and compared on
the SAME calendar weeks, so window choice cannot favor one year:
  peak = season weeks 2-3 (the two weeks ending one week before Christmas)
  post = season weeks 5-8 (late December through most of January)

Run (after extract_ua.py and pipeline.py):
  python yoy.py
  python yoy.py --peak-weeks 0 3 --post-weeks 4 7   # sensitivity check with other windows
"""
import argparse
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from pyspark.sql import SparkSession

SEASONS = {
    "GA4 2020-21": {"view": "ga4_sessions",    "anchor": date(2020, 11, 23)},
    "UA 2016-17":  {"view": "ua_fct_sessions", "anchor": date(2016, 11, 21)},
}


def window(anchor, first_week, last_week):
    start = anchor + timedelta(weeks=first_week)
    end = anchor + timedelta(weeks=last_week + 1) - timedelta(days=1)
    return start.isoformat(), end.isoformat()
DIMENSIONS = ["device", "medium"]

FUNNEL_SQL = """
SELECT
  CASE WHEN session_date BETWEEN DATE'{b0}' AND DATE'{b1}' THEN 'baseline' ELSE 'comparison' END AS period,
  COUNT(*)                                        AS sessions,
  SUM(has_purchase) / COUNT(*)                    AS conversion_rate,
  SUM(has_view_item)      / COUNT(*)              AS view_rate,
  SUM(has_add_to_cart)    / SUM(has_view_item)    AS cart_per_view,
  SUM(has_begin_checkout) / SUM(has_add_to_cart)  AS checkout_per_cart,
  SUM(has_purchase)       / SUM(has_begin_checkout) AS purchase_per_checkout
FROM {view}
WHERE session_date BETWEEN DATE'{b0}' AND DATE'{b1}'
   OR session_date BETWEEN DATE'{c0}' AND DATE'{c1}'
GROUP BY 1
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--peak-weeks", nargs=2, type=int, default=[2, 3])
    ap.add_argument("--post-weeks", nargs=2, type=int, default=[5, 8])
    args = ap.parse_args()

    spark = (SparkSession.builder.appName("kpi-yoy").master("local[*]")
             .config("spark.driver.memory", "4g")
             .config("spark.sql.shuffle.partitions", "16").getOrCreate())
    spark.sparkContext.setLogLevel("WARN")

    spark.read.parquet("data/gold/fct_sessions").createOrReplaceTempView("ga4_sessions")
    spark.read.parquet("data/raw_ua").createOrReplaceTempView("raw_ua")
    raw_n = spark.table("raw_ua").count()
    ua = spark.sql(Path("sql/11_ua_fct_sessions.sql").read_text())
    ua.write.mode("overwrite").parquet("data/gold/ua_fct_sessions")
    spark.read.parquet("data/gold/ua_fct_sessions").createOrReplaceTempView("ua_fct_sessions")
    ua_n = spark.table("ua_fct_sessions").count()
    dupes = spark.sql("SELECT COUNT(*) - COUNT(DISTINCT session_key) FROM ua_fct_sessions").first()[0]
    assert dupes == 0, "UA session_key is not unique"
    print(f"UA sessions: {raw_n:,} raw, {ua_n:,} after dedupe ({raw_n - ua_n:,} duplicate rows removed)")

    template = Path("sql/10_rca_decomposition.sql").read_text()
    summary, funnels, decomps = [], [], []
    for season, cfg in SEASONS.items():
        b0, b1 = window(cfg["anchor"], *args.peak_weeks)
        c0, c1 = window(cfg["anchor"], *args.post_weeks)
        spark.table(cfg["view"]).createOrReplaceTempView("fct_sessions")

        f = spark.sql(FUNNEL_SQL.format(view=cfg["view"], b0=b0, b1=b1, c0=c0, c1=c1)).toPandas()
        f = f.set_index("period").loc[["baseline", "comparison"]]
        f.loc["relative_change"] = f.loc["comparison"] / f.loc["baseline"] - 1
        f.insert(0, "season", season)
        funnels.append(f.reset_index())

        change = f.loc["comparison", "conversion_rate"] - f.loc["baseline", "conversion_rate"]
        row = {"season": season, "baseline_window": f"{b0} to {b1}", "comparison_window": f"{c0} to {c1}",
               "cvr_baseline": f.loc["baseline", "conversion_rate"],
               "cvr_comparison": f.loc["comparison", "conversion_rate"],
               "relative_change": f.loc["relative_change", "conversion_rate"]}
        for dim in DIMENSIONS:
            d = spark.sql(template.format(b0=b0, b1=b1, c0=c0, c1=c1, dim=dim)).toPandas()
            d.insert(0, "season", season)
            decomps.append(d)
            # Report effects in conversion percentage points: ratios explode when the total change is small
            row[f"mix_pts_{dim}"] = d.mix_effect.sum() * 100
            row[f"rate_pts_{dim}"] = d.rate_effect.sum() * 100
        summary.append(row)

    summary = pd.DataFrame(summary)
    funnels = pd.concat(funnels, ignore_index=True)
    decomps = pd.concat(decomps, ignore_index=True)
    weekly = spark.sql(Path("sql/12_season_weekly.sql").read_text()).toPandas().sort_values(["season", "season_week"])
    ua_weekly = spark.sql("""
        SELECT CAST(date_trunc('WEEK', session_date) AS DATE) AS week_start,
               COUNT(*) AS sessions, SUM(has_purchase) / COUNT(*) AS conversion_rate, SUM(revenue) AS revenue
        FROM ua_fct_sessions GROUP BY 1 ORDER BY 1""").toPandas()

    Path("tableau").mkdir(exist_ok=True)
    summary.to_csv("tableau/yoy_summary.csv", index=False)
    funnels.to_csv("tableau/yoy_funnel_steps.csv", index=False)
    decomps.to_csv("tableau/yoy_rca_decomposition.csv", index=False)
    weekly.to_csv("tableau/yoy_season_weekly.csv", index=False)
    ua_weekly.to_csv("tableau/ua_weekly_full_year.csv", index=False)

    pd.set_option("display.width", 160)
    print(f"\nPeak = season weeks {args.peak_weeks[0]}-{args.peak_weeks[1]}, post = season weeks {args.post_weeks[0]}-{args.post_weeks[1]}")
    print(summary[["season", "baseline_window", "comparison_window"]].to_string(index=False))
    print("\n=== Conversion change, holiday peak vs post-holiday (mix and rate in percentage points) ===")
    print(summary.drop(columns=["baseline_window", "comparison_window"]).round(4).to_string(index=False))
    print("\n=== Funnel step rates ===")
    print(funnels.round(4).to_string(index=False))
    print("\n=== Weekly conversion, aligned on Thanksgiving week (week 0) ===")
    print(weekly.pivot(index="season_week", columns="season", values="conversion_rate").round(4).to_string())
    spark.stop()


if __name__ == "__main__":
    main()
