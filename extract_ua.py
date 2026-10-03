"""Pull the Universal Analytics (GA360) sample for the same store, Aug 2016 to Aug 2017.

This is an independent year of data used to test whether the 2020 holiday conversion
pattern is seasonal. UA stores one row per session with hits nested inside, so funnel
flags are computed in BigQuery and only session-level rows are downloaded.

Run:
  python extract_ua.py
"""
import os
import sys
from pathlib import Path

from google.cloud import bigquery

PROJECT = os.environ.get("GCP_PROJECT")
OUT = Path("data/raw_ua/ua_sessions.parquet")

# eCommerceAction.action_type: 2 = product detail view, 3 = add to cart, 5 = checkout
QUERY = """
SELECT
  date,
  fullVisitorId                         AS user_id,
  visitId                               AS visit_id,
  visitStartTime                        AS visit_start_time,
  device.deviceCategory                 AS device,
  trafficSource.medium                  AS medium,
  geoNetwork.country                    AS country,
  totals.pageviews                      AS pageviews,
  totals.transactions                   AS transactions,
  totals.totalTransactionRevenue        AS total_transaction_revenue,
  (SELECT COUNTIF(h.eCommerceAction.action_type = '2') FROM UNNEST(hits) h) > 0 AS has_view_item,
  (SELECT COUNTIF(h.eCommerceAction.action_type = '3') FROM UNNEST(hits) h) > 0 AS has_add_to_cart,
  (SELECT COUNTIF(h.eCommerceAction.action_type = '5') FROM UNNEST(hits) h) > 0 AS has_begin_checkout
FROM `bigquery-public-data.google_analytics_sample.ga_sessions_*`
WHERE _TABLE_SUFFIX BETWEEN '20160801' AND '20170801'
"""


def main():
    if not PROJECT:
        sys.exit("Set GCP_PROJECT to your BigQuery sandbox project id first.")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    client = bigquery.Client(project=PROJECT)
    print("Pulling UA sessions, Aug 2016 to Aug 2017 ...", flush=True)
    job = client.query(QUERY)
    try:
        df = job.to_dataframe()
    except Exception as e:
        print(f"  Storage API unavailable ({type(e).__name__}), falling back to REST (slower)")
        df = job.to_dataframe(create_bqstorage_client=False)
    df.to_parquet(OUT, index=False)
    print(f"Done. {len(df):,} UA sessions written to {OUT}")


if __name__ == "__main__":
    main()
