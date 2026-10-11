"""WasteWise - institutional canteen food-waste prototype (Streamlit + local SQLite)."""
from datetime import timedelta

import pandas as pd
import streamlit as st

from wastewise import analytics, db, recommendations, seed

st.set_page_config(page_title="WasteWise", page_icon="🍽️", layout="wide")

CONN = db.connect()
db.init_db(CONN)

st.title("🍽️ WasteWise – Canteen Food-Waste Tracker")
st.caption("Supports SDG 12.3 (halve per-capita food waste). Prototype; rule-based, no machine learning.")
st.warning(
    "**Storage notice:** data is stored in a local SQLite file. On Streamlit Community Cloud "
    "this filesystem is **not durable** – data may be lost on restart or redeploy. "
    "Download CSV exports regularly. Do not enter personal data.")

logs = db.load_logs(CONN)
counts = db.load_counts(CONN)
n_synth = int((logs["provenance"] == "synthetic").sum()) if not logs.empty else 0
if n_synth:
    st.error(f"🧪 SYNTHETIC DATA PRESENT: {n_synth} log rows are synthetic demo data, not real measurements.")

tab_dash, tab_log, tab_rec, tab_iv, tab_data = st.tabs(
    ["Dashboard", "Log waste", "Recommendations", "Interventions", "Data & export"])

# ---------- Dashboard ----------
with tab_dash:
    if logs.empty:
        st.info("No data yet. Log waste, or load synthetic demo data in the 'Data & export' tab.")
    else:
        c = st.columns(5)
        dmin, dmax = pd.to_datetime(logs["log_date"]).min().date(), pd.to_datetime(logs["log_date"]).max().date()
        start = c[0].date_input("From", dmin, key="f_from")
        end = c[1].date_input("To", dmax, key="f_to")
        meals = c[2].multiselect("Meal", db.MEALS)
        stages = c[3].multiselect("Stage", db.STAGES)
        cats = c[4].multiselect("Category", db.CATEGORIES)
        prov = st.multiselect("Provenance", db.PROVENANCE)
        f = analytics.filter_logs(logs, start=start, end=end, meals=meals, stages=stages,
                                  categories=cats, provenance=prov)
        if f.empty:
            st.info("No rows match the filters.")
        else:
            r = analytics.kg_per_meal(f, counts)
            m = st.columns(4)
            m[0].metric("Total waste (kg)", f"{r['total_kg']:.1f}")
            m[1].metric("Log entries", len(f))
            m[2].metric("Meals served (matched)", f"{r['meals_served']:,}")
            m[3].metric("kg per meal", f"{r['kg_per_meal']:.3f}" if r["kg_per_meal"] is not None
                        else "n/a – no meals-served denominator")
            if r["kg_unmatched"] > 0.0005:
                st.caption(f"{r['kg_unmatched']:.1f} kg has no matching meals-served count and is "
                           "excluded from kg/meal.")
            st.caption("Provenance of filtered kg: " + ", ".join(
                f"{k} {v:.1f} kg" for k, v in f.groupby("provenance")["kg"].sum().items()))
            a, b = st.columns(2)
            a.subheader("By stage"); a.bar_chart(analytics.summarize(f, "stage").set_index("stage")["kg"])
            b.subheader("By category"); b.bar_chart(analytics.summarize(f, "category").set_index("category")["kg"])
            a.subheader("Top items (kg)")
            a.dataframe(analytics.summarize(f, "item").head(10), hide_index=True)
            b.subheader("kg per meal, by meal (needs denominator)")
            b.dataframe(analytics.kg_per_meal_by_meal(f, counts).reindex(
                columns=["meal", "total_kg", "meals_served", "kg_per_meal"]), hide_index=True)
            st.subheader("Daily total (kg)")
            st.line_chart(analytics.daily_totals(f).set_index("log_date")["kg"])

# ---------- Log ----------
with tab_log:
    st.subheader("Log a waste entry")
    with st.form("log_form", clear_on_submit=False):
        c = st.columns(3)
        d = c[0].date_input("Date", db.today())
        sess = c[1].text_input("Session label", "Week-1")
        meal = c[2].selectbox("Meal", db.MEALS)
        c = st.columns(3)
        item = c[0].text_input("Item (e.g. Rice)")
        stage = c[1].selectbox("Stage", db.STAGES)
        cat = c[2].selectbox("Category", db.CATEGORIES, index=2)
        c = st.columns(3)
        kg = c[0].number_input("Waste (kg)", min_value=0.0, step=0.1, format="%.2f")
        method = c[1].selectbox("Measurement method", db.METHODS)
        prov = c[2].selectbox("Provenance", ["measured", "estimated"])
        notes = st.text_input("Notes (no personal data)")
        if st.form_submit_button("Save entry"):
            try:
                db.add_waste_log(CONN, log_date=d, session_label=sess, meal=meal, item=item,
                                 stage=stage, category=cat, kg=kg, method=method,
                                 provenance=prov, notes=notes)
                st.success("Saved."); st.rerun()
            except ValueError as e:
                st.error(str(e))
    st.subheader("Meals served (denominator for kg/meal)")
    with st.form("count_form"):
        c = st.columns(5)
        d2 = c[0].date_input("Date", db.today(), key="cd")
        s2 = c[1].text_input("Session label", "Week-1", key="cs")
        m2 = c[2].selectbox("Meal", db.MEALS, key="cm")
        n2 = c[3].number_input("Meals served", min_value=0, step=1)
        p2 = c[4].selectbox("Provenance", ["measured", "estimated"], key="cp")
        if st.form_submit_button("Save meals served"):
            try:
                db.upsert_meal_count(CONN, log_date=d2, session_label=s2, meal=m2,
                                     meals_served=n2, provenance=p2)
                st.success("Saved."); st.rerun()
            except ValueError as e:
                st.error(str(e))

# ---------- Recommendations ----------
with tab_rec:
    st.subheader("Rule-based recommendations")
    st.caption("Each recommendation lists the rule, thresholds and the data behind it. "
               "They are suggestions for pilots, not proven causes.")
    recs, msg = (recommendations.generate(logs) if not logs.empty
                 else ([], "No data logged yet."))
    if msg:
        st.info(msg)
    for rec in recs:
        with st.expander(f"{rec.rule_id} – {rec.title}", expanded=True):
            st.write(rec.action)
            st.markdown(f"**Evidence:** {rec.evidence_text()}")
            if rec.synthetic_basis:
                st.warning("Based partly on SYNTHETIC data.")

# ---------- Interventions ----------
with tab_iv:
    st.subheader("Intervention baseline vs follow-up")
    with st.form("iv_form"):
        name = st.text_input("Intervention name")
        desc = st.text_area("Description")
        c = st.columns(2)
        tm = c[0].selectbox("Target meal", ["All"] + db.MEALS)
        ts = c[1].selectbox("Target stage", ["All"] + db.STAGES)
        c = st.columns(4)
        t = db.today()
        b0 = c[0].date_input("Baseline start", t - timedelta(days=14))
        b1 = c[1].date_input("Baseline end", t - timedelta(days=8))
        f0 = c[2].date_input("Follow-up start", t - timedelta(days=7))
        f1 = c[3].date_input("Follow-up end", t)
        if st.form_submit_button("Save intervention"):
            try:
                db.add_intervention(CONN, name=name, description=desc, target_meal=tm,
                                    target_stage=ts, baseline_start=b0, baseline_end=b1,
                                    followup_start=f0, followup_end=f1)
                st.success("Saved."); st.rerun()
            except ValueError as e:
                st.error(str(e))
    for _, iv in db.load_interventions(CONN).iterrows():
        res = analytics.evaluate_intervention(logs, counts, iv)
        st.markdown(f"### {iv['name']}")
        st.caption(f"{iv['description']} | target: {iv['target_meal']} / {iv['target_stage']}")
        cols = st.columns(3)
        for col, key, label in ((cols[0], "baseline", "Baseline"), (cols[1], "followup", "Follow-up")):
            p = res[key]
            col.metric(f"{label} kg/meal",
                       f"{p['kg_per_meal']:.3f}" if p["kg_per_meal"] is not None else "n/a")
            col.caption(f"{p['days_logged']} days, {p['meals_served']:,} meals, {p['total_kg']:.1f} kg; "
                        f"provenance {p['provenance_mix']}")
        cols[2].metric("Change", f"{res['change_pct']:+.1f}%" if res["change_pct"] is not None else "n/a")
        if not res["sufficient"]:
            st.info("Insufficient data (need >=3 logged days and a meals-served denominator in both periods).")
        st.caption("Descriptive comparison only; other factors (menu, attendance, season) may explain the change.")
        if iv["is_synthetic"]:
            st.warning("SYNTHETIC intervention and data – illustration only.")

# ---------- Data ----------
with tab_data:
    st.subheader("Export")
    c = st.columns(2)
    c[0].download_button("Download waste logs (CSV)", logs.to_csv(index=False).encode(),
                         "wastewise_waste_logs.csv", "text/csv")
    c[1].download_button("Download meals served (CSV)", counts.to_csv(index=False).encode(),
                         "wastewise_meal_counts.csv", "text/csv")
    st.subheader("Synthetic demo data")
    st.caption("Generates 28 days of clearly labelled synthetic rows (provenance = synthetic).")
    c = st.columns(2)
    if c[0].button("Load / reload synthetic demo data"):
        info = seed.seed_demo(CONN)
        st.success(f"Seeded {info['waste_rows']} synthetic rows."); st.rerun()
    if c[1].button("Remove all synthetic data"):
        db.clear_synthetic(CONN); st.rerun()
    st.dataframe(logs, hide_index=True)
