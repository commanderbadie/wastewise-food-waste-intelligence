from datetime import date, timedelta

import pytest

from wastewise import analytics, db, recommendations, seed


@pytest.fixture
def conn(tmp_path):
    c = db.connect(str(tmp_path / "t.db"))
    db.init_db(c)
    yield c
    c.close()


def log(conn, d, kg=1.0, meal="Lunch", stage="Plate waste", cat="avoidable",
        prov="measured", item="Rice"):
    db.add_waste_log(conn, log_date=d, session_label="s", meal=meal, item=item, stage=stage,
                     category=cat, kg=kg, method="weighed (scale)", provenance=prov)


def test_validation(conn):
    with pytest.raises(ValueError):
        log(conn, date.today(), kg=-1)
    with pytest.raises(ValueError):
        db.add_waste_log(conn, log_date=date.today(), session_label="s", meal="Lunch", item=" ",
                         stage="Plate waste", category="unknown", kg=1, method="x",
                         provenance="measured")
    with pytest.raises(ValueError):
        db.upsert_meal_count(conn, log_date=date.today(), session_label="s", meal="Lunch",
                             meals_served=0, provenance="measured")


def test_kg_per_meal_requires_denominator(conn):
    d = date(2025, 1, 1)
    log(conn, d, 10)
    r = analytics.kg_per_meal(db.load_logs(conn), db.load_counts(conn))
    assert r["kg_per_meal"] is None and r["kg_unmatched"] == 10
    db.upsert_meal_count(conn, log_date=d, session_label="s", meal="Lunch", meals_served=100,
                         provenance="measured")
    r = analytics.kg_per_meal(db.load_logs(conn), db.load_counts(conn))
    assert r["kg_per_meal"] == pytest.approx(0.1)


def test_unmatched_kg_excluded(conn):
    d = date(2025, 1, 1)
    log(conn, d, 10)
    log(conn, d, 5, meal="Dinner")
    db.upsert_meal_count(conn, log_date=d, session_label="s", meal="Lunch", meals_served=100,
                         provenance="measured")
    r = analytics.kg_per_meal(db.load_logs(conn), db.load_counts(conn))
    assert r["kg_per_meal"] == pytest.approx(0.1) and r["kg_unmatched"] == 5


def test_filters(conn):
    log(conn, date(2025, 1, 1), 1, meal="Lunch")
    log(conn, date(2025, 1, 2), 2, meal="Dinner", prov="estimated")
    df = db.load_logs(conn)
    assert len(analytics.filter_logs(df, meals=["Dinner"])) == 1
    assert len(analytics.filter_logs(df, provenance=["measured"])) == 1
    assert len(analytics.filter_logs(df, start="2025-01-02")) == 1


def test_recommendations_insufficient(conn):
    log(conn, date(2025, 1, 1))
    recs, msg = recommendations.generate(db.load_logs(conn))
    assert recs == [] and "Not enough data" in msg


def test_recommendations_evidence(conn):
    for i in range(6):
        log(conn, date(2025, 1, 1) + timedelta(days=i), 2)
    recs, msg = recommendations.generate(db.load_logs(conn))
    ids = {r.rule_id for r in recs}
    assert {"R1-PLATE", "R3-AVOIDABLE", "R5-TOP-ITEM"} <= ids
    assert all(r.evidence["log entries"] > 0 and r.evidence_text() for r in recs)


def test_synthetic_flagged(conn):
    seed.seed_demo(conn, days=14, end=date(2025, 3, 1))
    recs, _ = recommendations.generate(db.load_logs(conn))
    assert recs and all(r.synthetic_basis for r in recs)


def test_seed_idempotent_and_labelled(conn):
    seed.seed_demo(conn, days=14, end=date(2025, 3, 1))
    n1 = len(db.load_logs(conn))
    seed.seed_demo(conn, days=14, end=date(2025, 3, 1))
    logs = db.load_logs(conn)
    assert len(logs) == n1 and set(logs["provenance"]) == {"synthetic"}
    assert len(db.load_interventions(conn)) == 1


def test_intervention_eval(conn):
    seed.seed_demo(conn, days=28, end=date(2025, 3, 1))
    iv = db.load_interventions(conn).iloc[0]
    res = analytics.evaluate_intervention(db.load_logs(conn), db.load_counts(conn), iv)
    assert res["sufficient"] and res["change_pct"] < 0


def test_intervention_date_order(conn):
    with pytest.raises(ValueError):
        db.add_intervention(conn, name="x", description="", target_meal="All",
                            target_stage="All", baseline_start="2025-01-05",
                            baseline_end="2025-01-10", followup_start="2025-01-08",
                            followup_end="2025-01-20")


def test_csv_export_roundtrip(conn):
    log(conn, date(2025, 1, 1), 1.5)
    csv = db.load_logs(conn).to_csv(index=False)
    assert "provenance" in csv.splitlines()[0] and "1.5" in csv
