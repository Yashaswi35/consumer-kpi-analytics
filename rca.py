"""Step 4: Root-cause a conversion change with a mix vs rate decomposition.

Look at the weekly conversion trend first (tableau/kpi_weekly.csv), then pick the two periods.
Run:
  python rca.py --baseline 2020-11-01 2020-12-20 --comparison 2021-01-01 2021-01-31
"""
import argparse
from pathlib import Path

import pandas as pd
from pyspark.sql import SparkSession

DIMENSIONS = ["device", "medium", "country"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", nargs=2, default=["2020-11-01", "2020-12-20"])
    ap.add_argument("--comparison", nargs=2, default=["2021-01-01", "2021-01-31"])
    args = ap.parse_args()

    spark = (SparkSession.builder.appName("kpi-rca").master("local[*]")
             .config("spark.driver.memory", "4g").getOrCreate())
    spark.sparkContext.setLogLevel("WARN")
    spark.read.parquet("data/gold/fct_sessions").createOrReplaceTempView("fct_sessions")
    template = Path("sql/10_rca_decomposition.sql").read_text()

    frames = []
    for dim in DIMENSIONS:
        sql = template.format(b0=args.baseline[0], b1=args.baseline[1],
                              c0=args.comparison[0], c1=args.comparison[1], dim=dim)
        frames.append(spark.sql(sql).toPandas())
    out = pd.concat(frames, ignore_index=True)
    out["baseline_period"] = " to ".join(args.baseline)
    out["comparison_period"] = " to ".join(args.comparison)
    out.to_csv("tableau/rca_decomposition.csv", index=False)

    d = out[out.dimension == "device"]
    cvr_b = (d.share_b.fillna(0) * d.cvr_b.fillna(0)).sum()
    cvr_c = (d.share_c.fillna(0) * d.cvr_c.fillna(0)).sum()
    change = cvr_c - cvr_b
    print(f"\nConversion: {cvr_b:.4%} -> {cvr_c:.4%}  ({change / cvr_b:+.1%} relative)\n")
    for dim in DIMENSIONS:
        x = out[out.dimension == dim]
        mix, rate = x.mix_effect.sum(), x.rate_effect.sum()
        share = mix / change if change else float("nan")
        print(f"{dim:8}  mix {mix:+.4%}   rate {rate:+.4%}   mix explains {share:.0%} of the change")
    print("\nPer-segment detail:")
    print(out[["dimension", "segment", "share_b", "share_c", "cvr_b", "cvr_c",
               "mix_effect", "rate_effect"]].round(4).to_string(index=False))
    spark.stop()


if __name__ == "__main__":
    main()
