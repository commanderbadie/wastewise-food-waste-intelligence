# WasteWise – Canteen Food-Waste Intelligence

A small, transparent Streamlit prototype for logging and analysing food waste in an
institutional canteen (university, hospital, workplace), with local SQLite storage.

> **Status:** working prototype. **No live deployment exists yet** – see
> [Deployment](#deployment-streamlit-community-cloud). No live URL is claimed.

## Context: SDG 12.3

UN Sustainable Development Goal target 12.3 aims to halve per-capita global food waste at
retail and consumer level and reduce food losses along production and supply chains by 2030.
Canteens can contribute only if they *measure* waste consistently. WasteWise gives a canteen
team a low-cost way to record where, when and why food is wasted, and to test whether a change
helped. It makes no claims about environmental impact (CO₂, water, cost): none are computed.

## Problem

Canteens often know they waste food but not **which meals, items or stages** drive it, how
reliable the numbers are, or whether an intervention worked.

## Features

- **Structured logging:** date/session, meal, item, stage (storage, preparation, serving, plate),
  avoidable / unavoidable / unknown, kg, measurement method, and provenance
  (`measured` / `estimated` / `synthetic`).
- **Meals-served denominator:** `kg/meal` is shown **only** where a meals-served count exists for
  the same date/session/meal; unmatched kg is reported and excluded, never guessed.
- **Dashboard:** totals, by stage/category/item/meal, daily trend, filters (dates, meal, stage,
  category, provenance), provenance breakdown.
- **Rule-based recommendations (no ML):** seven documented rules with thresholds
  (`wastewise/recommendations.py`). Each shows its evidence: entry count, days, kg, share vs
  threshold, provenance mix. Minimum data is required (≥5 entries over ≥3 days).
- **Interventions:** define baseline and follow-up periods (optionally for a meal/stage) and
  compare kg/meal. The comparison is descriptive, not causal.
- **CSV export** of waste logs and meal counts.
- **Synthetic demo seed:** 28 days of generated data, every row tagged `synthetic`, with
  prominent banners wherever it appears. The demo intervention's improvement is built into the
  generator and demonstrates the UI only – it is not evidence.

## Stack

Python 3.10+, Streamlit, pandas, SQLite (stdlib), pytest.

## Architecture

```
app.py                     Streamlit UI (tabs: dashboard, log, recommendations, interventions, data)
wastewise/db.py            SQLite schema, validation, CRUD
wastewise/analytics.py     filters, aggregation, kg/meal with denominator, intervention comparison
wastewise/recommendations.py  rule engine with evidence
wastewise/seed.py          synthetic demo data
tests/                     unit tests + Streamlit AppTest smoke test
```

Tables: `waste_logs`, `meal_counts`, `interventions`. DB path: `WASTEWISE_DB` env var
(default `wastewise.db`, git-ignored).

## Setup

```powershell
py -m venv .venv ; .\.venv\Scripts\Activate.ps1     # macOS/Linux: python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q
streamlit run app.py
```

Open the **Data & export** tab and click *Load / reload synthetic demo data* to explore.

## Screenshots

Not yet captured. After running the app locally, add images under `docs/` and link them here.

## Deployment (Streamlit Community Cloud)

The repo is deployment-ready (`app.py` entrypoint, `requirements.txt`, no secrets).
Deployment must be done by the repository owner, who must authorise Streamlit with GitHub:

1. Sign in at <https://share.streamlit.io> with GitHub and grant access to this repository.
2. *Create app* → repo `commanderbadie/wastewise-food-waste-intelligence`, branch `main`,
   main file `app.py` → Deploy.
3. Record the real URL below once it exists.

**Live URL:** _none – not deployed. `https://wastewise-food-waste-intelligence.streamlit.app`
returned HTTP 404 when probed on 2026-10-11, so no app exists there._

### ⚠️ Persistence warning

SQLite writes to the container filesystem. On Streamlit Community Cloud this is **not durable**:
data can be lost when the app restarts, sleeps, or is redeployed. A cloud deployment is suitable
for demos only. Use the CSV export regularly, or run locally / on a host with a persistent
volume or external database for real data.

### Deployment acceptance checklist

- [ ] App URL loads publicly without login (or access policy is intentionally documented)
- [ ] Storage warning and synthetic-data banner visible
- [ ] Load synthetic demo data → dashboard, filters and kg/meal render
- [ ] Log a waste entry and a meals-served count → appear in dashboard
- [ ] kg/meal shows "n/a" for data lacking a denominator
- [ ] Recommendations show evidence; insufficient data shows a message
- [ ] Create an intervention → baseline/follow-up comparison renders
- [ ] CSV downloads open and contain provenance column
- [ ] README updated with the real URL and the date of verification

## Limitations

- Not durable on Streamlit Community Cloud; single-file SQLite, no auth, no multi-user safety.
- Data quality depends on staff; estimated entries are less reliable than weighed ones.
- Rules are simple thresholds, not validated; recommendations are hypotheses to pilot.
- Intervention comparison ignores confounders (menu, attendance, season); no significance tests.
- No cost, carbon or water calculations. Synthetic data is illustrative only.
- Do not enter personal data.
