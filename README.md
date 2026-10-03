# Consumer Product Usage and KPI Analytics

Spark SQL pipeline and Tableau dashboards for engagement, conversion, and retention reporting on real GA4 ecommerce event data from the Google Merchandise Store.

**Live dashboard:** [Tableau Public link]

## Data

[`bigquery-public-data.ga4_obfuscated_sample_ecommerce`](https://developers.google.com/analytics/bigquery/web-ecommerce-demo-dataset), Google's public GA4 BigQuery export sample covering Nov 1, 2020 to Jan 31, 2021. [X] events, [X] sessions, [X] users. The data is obfuscated by Google, so some fields contain placeholder values and internal consistency is imperfect. The validation layer measures this rather than hiding it.

## Architecture

```
BigQuery (GA4 export, nested)
   │  extract.py: flatten event_params, pull to Parquet
   ▼
data/raw  ──►  Spark SQL (local)
                 01 events_clean          typed, standardized, deduplicated
                 02 sessions_derived      independent 30 min inactivity sessionization
                 03 session_match         derived sessions vs GA4 ga_session_id
                 04 fct_sessions          one row per session, funnel flags, revenue
                 05 fct_funnel_daily      funnel by date, device, medium
                 06 fct_users             cohorts, D1/D7/D30 return flags
                 07 fct_retention_cohort  weekly cohort retention
                 08/09 kpi_daily/weekly   headline KPIs
                 10 rca_decomposition     mix vs rate decomposition
   ▼
validate.py (12 SQL assertions)  ──►  tableau/*.csv  ──►  Tableau Public (3 views)
```

## Metric definitions

| Metric | Definition |
|---|---|
| Session | GA4 `user_pseudo_id` + `ga_session_id` |
| Conversion rate | Sessions with ≥1 purchase event / all sessions |
| Bounce | Session with ≤1 page_view and no ecommerce events |
| Funnel | view_item → add_to_cart → begin_checkout → purchase, measured as sessions reaching each step |
| New user | First touch on or after 2020-11-01 |
| D7 retention | New users with a session on days 1 to 7 after first session / new users with ≥7 days of observable history |
| Medium | GA4 `traffic_source`, which is user-scoped first acquisition medium |

## Data quality

| Check | Result |
|---|---|
| Duplicate events removed | [X] |
| Events dropped for missing session id | [X] |
| Sessionization match rate vs GA4 sessions | [X]% |
| Orphan purchases (no begin_checkout) | [X] |
| ERROR checks passing | 8 / 8 |

## Key finding

Session conversion moved from [X]% in [baseline period] to [X]% in [comparison period], a [X]% relative change. A mix vs rate decomposition attributes [X]% of the change to shifts in device mix and [X]% to changes in within-device conversion. [One or two sentences on what that means.]

## Run it

```bash
pip install -r requirements.txt
export GCP_PROJECT=your-project-id
python extract.py && python pipeline.py && python validate.py
python rca.py --baseline 2020-11-01 2020-12-20 --comparison 2021-01-01 2021-01-31
```

`pipeline.py --start YYYY-MM-DD --end YYYY-MM-DD` reruns the pipeline for a reporting window.
