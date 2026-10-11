# WasteWise - Project Report

Repo: https://github.com/commanderbadie/wastewise-food-waste-intelligence  
Live URL: https://wastewise-food-waste-intelligence-qeykaa8immms9xxex9aoin.streamlit.app/

## Problem and SDG 12.3
Institutional canteens and hostel messes waste food at preparation, serving and plate stages, but rarely record where, why or per meal served. SDG 12.3 targets halving per-capita food waste at retail/consumer level and reducing losses along supply chains; WasteWise is a small tool to make canteen waste measurable.

## Approach
Structured logging (date/session, meal, item, stage, avoidable/unavoidable/unknown, kg, measurement method, provenance), dashboards, transparent rule-based recommendations that show their evidence, and baseline/follow-up intervention tracking. No machine learning. kg/meal is shown only where a meals-served denominator exists.

## Architecture
Streamlit UI (pp.py) over wastewise/ modules: db (SQLite schema, validation, migration), nalytics (filters, kg/meal, intervention evaluation, assumed-price cost), ecommendations (rules R1-R10), demo_data + seed (deterministic synthetic generator).

## Features
Logging forms, meals-served counts, filters, kg/meal with denominator, INR value using assumed prices, recommendations with evidence, interventions, CSV export, synthetic-data labels, auto-seed of the demo set on an empty database plus a manual reload button.

## Synthetic data statement
All demo data is synthetic (provenance and source_type = 'synthetic', notes prefixed SYNTHETIC). No open per-meal Indian canteen/hostel dataset was found. Cited studies (Rezekne Latvia school study, Panjab University hostel questionnaire, WRI India report) are context only. See README for the data dictionary.

## Test results
python -m pytest -q in the project venv: **29 passed, 0 failed** (after the validation/intervention upgrade, run 2026-10-11).

## Live-test results (only what was verified)
- Earlier build (commits up to a2d75bb), Playwright on the live URL: banners, seeding, dashboard, Meal filter, recommendations with evidence, interventions list and creation, test row appearing in the CSV export.
- Not verified: live behaviour of commits 0e72c68, dfaaae4 and 1387993 (large dataset, R8-R10, auto-seed). After those pushes the live URL redirected to Streamlit sign-in for the automated browser, and the app frame never loaded.
- A user reported an AttributeError on the live app after dfaaae4; it could not be reproduced locally (fresh DB, populated DB, old-schema DB, real streamlit run). The probable cause (not confirmed) is a stale cached module after hot redeploy, addressed in 1387993; a reboot may be needed.

## Limitations
SQLite on Streamlit Community Cloud is ephemeral (reset on restart/redeploy, then re-seeded with synthetic data); no ML; no auth; single-file DB. The synthetic intervention result (about -38% dinner-rice kg/meal) is a demo outcome built into the generator, not a finding.

