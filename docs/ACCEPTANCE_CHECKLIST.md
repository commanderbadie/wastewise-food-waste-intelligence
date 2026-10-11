# Acceptance checklist

| Item | Status | Evidence |
|---|---|---|
| Unit/app tests pass | Verified | pytest -q: 27 passed (local, 2026-10-11) |
| App runs locally (streamlit run, all tabs, old-schema DB) | Verified | Playwright on localhost: no error on 5 tabs |
| Deterministic, idempotent synthetic seed; all rows flagged | Verified | tests/test_demo_dataset.py |
| Auto-seed on empty DB, no duplicates | Verified (local) | tests/test_app.py |
| Rules R8-R10 fire on demo data | Verified (local) | tests/test_demo_dataset.py |
| Live app loads (earlier build a2d75bb) | Verified (earlier session) | Playwright; screenshots 01-06 |
| Live: filter, recommendations, intervention, CSV, add row (earlier build) | Verified | screenshots 01-06 |
| Live: latest commit, large dataset, auto-seed, R8-R10 | **Not verified** | live URL redirected to sign-in / no frame for my browser |
| Live: no AttributeError after latest fix | **Not verified** | needs owner reboot and check |
| Persistence across restart | Not durable (by design) | README warning |

| Add-record validation (<=0, >500 kg, future date, duplicate) | Verified (local) | tests/test_demo_dataset.py, pytest 29 passed |
| Intervention coverage/days/caveat, recommendation action+evidence cards | Verified (local tests/AppTest); not verified live | pytest 29 passed |


**Live verification by the project owner, 2026-10-11 (screenshots in docs/screenshots/: dashboard-kpis, dashboard-tables, log-waste, recommendations, interventions, export), commit 727fe05:** the app loads with auto-seeded synthetic data; dashboard KPIs and tables/daily chart; Log waste form; recommendations with suggested action and evidence; intervention impact with coverage and caveat; Data & export tab. NOT shown/verified live: submitting an add-record entry, CSV download.

