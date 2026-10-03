# Tonight's run sheet

Total: about 5 to 6 hours. Do the steps in order and don't polish until the end.

## 1. Setup (20 min)

```bash
brew install openjdk@17 && brew install --cask google-cloud-sdk
export JAVA_HOME=$(/usr/libexec/java_home -v 17)   # add to ~/.zshrc
cd consumer-kpi-analytics
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

BigQuery sandbox: go to console.cloud.google.com/bigquery, sign in, create a project, copy its project ID. Then:

```bash
gcloud auth application-default login
export GCP_PROJECT=your-project-id
```

## 2. Extract (15 to 30 min)

```bash
python extract.py
```

Writes 3 monthly Parquet files to `data/raw/`. Write down the total row count. That's your real event count for the resume.

## 3. Pipeline (15 min)

```bash
python pipeline.py
```

Prints row counts per table and writes `output/dq_summary.json` (duplicates removed, nulls, sessionization match rate, users). Screenshot it for the README.

If you run out of memory, change `spark.driver.memory` in `pipeline.py` to `4g` and close Chrome.

## 4. Validate (5 min)

```bash
python validate.py
```

ERROR checks must pass. WARN checks are expected on obfuscated GA4 data. Report the counts as data quality findings, don't hide them.

## 5. Pick your periods and run the RCA (30 min)

Open `tableau/kpi_weekly.csv` and look at `conversion_rate` by week. Find the biggest sustained drop (likely the holiday peak into January). Then:

```bash
python rca.py --baseline 2020-11-01 2020-12-20 --comparison 2021-01-01 2021-01-31
```

Read the "mix explains X% of the change" line for each dimension. That's your headline finding, whatever it turns out to be.

## 6. Tableau Public (2.5 to 3 hours)

Connect to the CSVs in `tableau/` (Text file connection, one data source per CSV).

**Dashboard 1: Engagement** (source: `kpi_daily`, `kpi_weekly`)
- KPI tiles: total users, sessions, events per session, median session length
- Line: DAU by `session_date`, with WAU from `kpi_weekly` on a second sheet
- Line: `bounce_rate` and `events_per_session` over time

**Dashboard 2: Conversion** (source: `fct_funnel_daily`, `rca_decomposition`)
- Funnel bar: SUM of sessions, view_item_sessions, add_to_cart_sessions, checkout_sessions, purchase_sessions (use Measure Names / Measure Values)
- Calculated field `CVR = SUM([Purchase Sessions]) / SUM([Sessions])`, line by week, color by `device`
- Stacked area: sessions share by device by week (Quick Table Calc, Percent of Total, compute using device)
- Bar: `mix_effect` and `rate_effect` by segment from `rca_decomposition`, filtered to dimension = device. This is the money chart.
- Filters: device, medium

**Dashboard 3: Retention** (source: `fct_retention_cohort`, `fct_users`)
- Heatmap: `cohort_week` on rows, `week_number` on columns, color = `retention_rate`, label = retention_rate as %
- Bar: D7 retention by `first_medium` and by `first_device`. Calc field `D7 = SUM([Returned D7]) / SUM([D7 Eligible])` with filter `is_new_user = 1` and `d7_eligible = 1`

Publish to Tableau Public. Copy the link.

## 7. Ship it (30 min)

- Fill in the bracketed numbers in `README.md`
- Add 2 or 3 dashboard screenshots to `images/`
- `git init`, commit, push to github.com/yashaswi35
- Update the resume bullets with the real numbers
