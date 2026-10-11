from datetime import date

import pandas as pd
import pytest

from wastewise import analytics, db, recommendations, seed
from wastewise.demo_data import DEMO_START, generate_dataset


@pytest.fixture(scope="module")
def ds():
    return generate_dataset()


@pytest.fixture
def seeded(tmp_path):
    c = db.connect(str(tmp_path / "d.db"))
    db.init_db(c)
    seed.seed_demo(c)
    yield c
    c.close()


def test_demo_start_is_monday_and_size(ds):
    assert DEMO_START.weekday() == 0
    assert 3000 < len(ds["waste_logs"]) < 6000
    assert len(ds["meal_counts"]) > 250


def test_deterministic():
    assert generate_dataset() == generate_dataset()
    assert generate_dataset(rng_seed=1) != generate_dataset(rng_seed=2)


def test_nonnegative_and_valid_values(ds):
    for r in ds["waste_logs"]:
        assert r["kg"] > 0
        assert r["meal"] in db.MEALS and r["stage"] in db.STAGES
        assert r["category"] in db.CATEGORIES and r["method"] in db.METHODS
    assert all(c["meals_served"] > 0 for c in ds["meal_counts"])
    assert all(c["inr_per_kg"] >= 0 for c in ds["item_costs"])


def test_every_row_flagged_synthetic(ds):
    for r in ds["waste_logs"]:
        assert r["provenance"] == "synthetic" and r["source_type"] == "synthetic"
        assert r["notes"].startswith("SYNTHETIC")
    for r in ds["meal_counts"] + ds["item_costs"]:
        assert r["source_type"] == "synthetic"
    assert all(i["is_synthetic"] and i["name"].startswith("[SYNTHETIC]")
               for i in ds["interventions"])
    assert all(c["is_assumption"] == 1 for c in ds["item_costs"])


def test_referential_integrity(ds):
    priced = {c["item"] for c in ds["item_costs"]}
    assert {r["item"] for r in ds["waste_logs"]} <= priced
    waste_keys = {(r["log_date"], r["session_label"], r["meal"]) for r in ds["waste_logs"]}
    count_keys = [(r["log_date"], r["session_label"], r["meal"]) for r in ds["meal_counts"]]
    assert set(count_keys) <= waste_keys
    assert len(count_keys) == len(set(count_keys))
    dates = {r["log_date"] for r in ds["waste_logs"]}
    iv = ds["interventions"][0]
    assert min(dates) <= str(iv["baseline_start"]) and str(iv["followup_end"]) >= max(dates)


def test_realism_features(ds):
    waste = pd.DataFrame(ds["waste_logs"])
    keys = {(r["log_date"], r["session_label"], r["meal"]) for r in ds["meal_counts"]}
    all_keys = set(zip(waste.log_date, waste.session_label, waste.meal))
    assert 0 < len(all_keys - keys) < 0.2 * len(all_keys)  # some missing denominators
    assert {"weighed (scale)", "visual estimate", "container count"} <= set(waste.method)
    assert {"avoidable", "unavoidable", "unknown"} == set(waste.category)
    assert {"Surplus/Overproduction", "Spoilage", "Plate waste", "Preparation"} <= set(waste.stage)
    assert waste.session_label.nunique() == 2
    wk = pd.to_datetime(waste.log_date).dt.weekday
    assert (wk >= 5).any() and (wk < 5).any()


def test_seed_idempotent_and_clears_old(seeded):
    n = len(db.load_logs(seeded))
    seed.seed_demo(seeded)
    assert len(db.load_logs(seeded)) == n
    assert len(db.load_interventions(seeded)) == 1
    assert len(db.load_item_costs(seeded)) == len(generate_dataset()["item_costs"])
    db.clear_synthetic(seeded)
    assert db.load_logs(seeded).empty and db.load_item_costs(seeded).empty


def test_user_rows_survive_reseed(seeded):
    db.add_waste_log(seeded, log_date=date(2026, 9, 1), session_label="mine", meal="Lunch",
                     item="Rice", stage="Plate waste", category="unknown", kg=1,
                     method="weighed (scale)", provenance="measured")
    seed.seed_demo(seeded)
    logs = db.load_logs(seeded)
    assert (logs["source_type"] == "user").sum() == 1


def test_patterns_trigger_recommendations(seeded):
    logs, counts = db.load_logs(seeded), db.load_counts(seeded)
    recs, _ = recommendations.generate(logs, counts)
    by_id = {r.rule_id: r for r in recs}
    assert {"R8-OVERPROD", "R9-DISLIKED", "R10-SPOILAGE"} <= set(by_id)
    assert "Rice at Dinner" in by_id["R8-OVERPROD"].title
    assert "Lauki sabzi" in by_id["R9-DISLIKED"].title
    assert all(r.synthetic_basis and r.evidence_text() for r in recs)


def test_intervention_reduces_target(seeded):
    iv = db.load_interventions(seeded).iloc[0]
    res = analytics.evaluate_intervention(db.load_logs(seeded), db.load_counts(seeded), iv)
    assert res["sufficient"] and res["change_pct"] < -20


def test_cost_uses_assumed_prices(seeded):
    cost = analytics.estimate_cost(db.load_logs(seeded), db.load_item_costs(seeded))
    assert cost["inr"] > 0 and cost["kg_unpriced"] == 0


def test_old_database_is_migrated(tmp_path):
    import sqlite3
    path = str(tmp_path / "old.db")
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE waste_logs (id INTEGER PRIMARY KEY, log_date TEXT, session_label TEXT,"
              " meal TEXT, item TEXT, stage TEXT, category TEXT, kg REAL, method TEXT,"
              " provenance TEXT, notes TEXT, created_at TEXT)")
    c.execute("CREATE TABLE meal_counts (id INTEGER PRIMARY KEY, log_date TEXT, session_label TEXT,"
              " meal TEXT, meals_served INTEGER, provenance TEXT,"
              " UNIQUE (log_date, session_label, meal))")
    c.commit(); c.close()
    with db.session(path) as conn:
        seed.seed_demo(conn, weeks=2)
        assert len(db.load_logs(conn)) > 0
