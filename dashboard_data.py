"""Package the dashboard inputs into one Excel file, one tidy sheet per chart.

Run (after pipeline.py, rca.py and yoy.py):
  python dashboard_data.py
Output: tableau/dashboard_data.xlsx
"""
import pandas as pd

T = "tableau/"
STEP_LABELS = {
    "view_rate": "1. Session views a product",
    "cart_per_view": "2. Product view to add to cart",
    "checkout_per_cart": "3. Cart to checkout",
    "purchase_per_checkout": "4. Checkout to purchase",
}


def main():
    funnel = pd.read_csv(T + "fct_funnel_daily.csv", parse_dates=["session_date"])
    users = pd.read_csv(T + "fct_users.csv", usecols=["user_pseudo_id"])

    # KPI tiles for the GA4 season
    kpi = pd.DataFrame([{
        "events": 4295584,
        "sessions": int(funnel.sessions.sum()),
        "users": int(users.user_pseudo_id.nunique()),
        "conversion_rate": funnel.purchase_sessions.sum() / funnel.sessions.sum(),
        "revenue": funnel.revenue.sum(),
        "peak_conversion": 0.0183, "post_conversion": 0.0086, "decline": -0.529,
        "ua_decline": -0.511,
    }])

    # Hero chart: weekly conversion for both seasons aligned on Thanksgiving week
    yoy = pd.read_csv(T + "yoy_season_weekly.csv")
    yoy = yoy[yoy.season_week.between(-3, 9)].copy()
    yoy["window"] = pd.cut(yoy.season_week, [-99, 1, 3, 4, 8, 99],
                           labels=["Other", "Peak", "Christmas week", "Post", "Other "]).astype(str).str.strip()
    yoy["week_label"] = yoy.season_week.map(lambda w: "Thanksgiving week" if w == 0 else f"{w:+d} wk")

    # Conversion by device by week (GA4), full weeks only
    funnel["week_start"] = funnel.session_date.dt.to_period("W-SUN").dt.start_time
    dev = (funnel.groupby(["week_start", "device"], as_index=False)[["sessions", "purchase_sessions"]].sum())
    dev = dev[(dev.week_start >= "2020-11-02") & (dev.week_start <= "2021-01-25")]
    dev["conversion_rate"] = dev.purchase_sessions / dev.sessions
    dev["device_share"] = dev.sessions / dev.groupby("week_start").sessions.transform("sum")

    # Mix vs rate effects, long format, in conversion percentage points
    d = pd.read_csv(T + "yoy_rca_decomposition.csv")
    mix = (d.groupby(["season", "dimension"], as_index=False)[["mix_effect", "rate_effect"]].sum()
             .melt(id_vars=["season", "dimension"], var_name="effect", value_name="value"))
    mix["effect"] = mix.effect.map({"mix_effect": "Mix (who visited)", "rate_effect": "Rate (how they converted)"})
    mix["points"] = mix.value * 100
    mix["dimension"] = mix.dimension.str.title()

    # Funnel step rates, peak vs post, both seasons
    f = pd.read_csv(T + "yoy_funnel_steps.csv")
    f = f[f.period.isin(["baseline", "comparison"])]
    steps = f.melt(id_vars=["season", "period"], value_vars=list(STEP_LABELS), var_name="step", value_name="rate")
    steps["period"] = steps.period.map({"baseline": "Peak", "comparison": "Post"})
    steps["step"] = steps.step.map(STEP_LABELS)
    change = (steps.pivot_table(index=["season", "step"], columns="period", values="rate").reset_index())
    change["relative_change"] = change.Post / change.Peak - 1

    with pd.ExcelWriter(T + "dashboard_data.xlsx") as xl:
        kpi.to_excel(xl, sheet_name="kpi_tiles", index=False)
        yoy.to_excel(xl, sheet_name="yoy_weekly", index=False)
        dev.to_excel(xl, sheet_name="device_weekly", index=False)
        mix.to_excel(xl, sheet_name="mix_vs_rate", index=False)
        steps.to_excel(xl, sheet_name="funnel_steps", index=False)
        change.to_excel(xl, sheet_name="funnel_change", index=False)
    print("Wrote tableau/dashboard_data.xlsx")
    print(kpi.round(4).to_string(index=False))
    print(change.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
