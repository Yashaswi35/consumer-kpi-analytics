"""Step 1: Pull the GA4 sample ecommerce events from BigQuery into local Parquet.

Prereqs (once):
  brew install --cask google-cloud-sdk
  gcloud auth application-default login
  export GCP_PROJECT=<your-sandbox-project-id>

Run:
  python extract.py
"""
import os
import sys
from pathlib import Path

from google.cloud import bigquery

PROJECT = os.environ.get("GCP_PROJECT")
OUT_DIR = Path("data/raw")

# Flatten the nested GA4 export into one row per event with only the fields we need.
QUERY = """
SELECT
  event_date,
  event_timestamp,
  event_name,
  user_pseudo_id,
  user_first_touch_timestamp,
  device.category                  AS device,
  traffic_source.medium            AS medium,
  traffic_source.source            AS source,
  geo.country                      AS country,
  (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS ga_session_id,
  ecommerce.transaction_id         AS transaction_id,
  ecommerce.purchase_revenue_in_usd AS purchase_revenue_in_usd
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
WHERE _TABLE_SUFFIX BETWEEN @start AND @end
"""

MONTHS = [("20201101", "20201130"), ("20201201", "20201231"), ("20210101", "20210131")]


def main():
    if not PROJECT:
        sys.exit("Set GCP_PROJECT to your BigQuery sandbox project id first.")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = bigquery.Client(project=PROJECT)

    total = 0
    for start, end in MONTHS:
        cfg = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("start", "STRING", start),
            bigquery.ScalarQueryParameter("end", "STRING", end),
        ])
        print(f"Pulling {start} to {end} ...", flush=True)
        job = client.query(QUERY, job_config=cfg)
        try:
            df = job.to_dataframe()  # fast path via BigQuery Storage API
        except Exception as e:  # sandbox projects sometimes lack the Storage API
            print(f"  Storage API unavailable ({type(e).__name__}), falling back to REST (slower)")
            df = job.to_dataframe(create_bqstorage_client=False)
        df["ga_session_id"] = df["ga_session_id"].astype("Int64")
        path = OUT_DIR / f"events_{start[:6]}.parquet"
        df.to_parquet(path, index=False)
        total += len(df)
        print(f"  wrote {len(df):,} rows to {path}")

    print(f"Done. {total:,} raw events extracted.")


if __name__ == "__main__":
    main()
