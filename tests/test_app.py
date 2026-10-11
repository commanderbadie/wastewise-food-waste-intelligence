from pathlib import Path

from streamlit.testing.v1 import AppTest

from wastewise import db

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def test_app_renders_and_seeds(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DEFAULT_DB_PATH", str(tmp_path / "app.db"))
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    next(b for b in at.button if "Load" in b.label).click().run()
    assert not at.exception
    assert any("SYNTHETIC" in e.value for e in at.error)
    assert len(at.expander) > 0


def test_autoseed_on_empty_db_and_no_duplicates(tmp_path, monkeypatch):
    path = str(tmp_path / "auto.db")
    monkeypatch.setattr(db, "DEFAULT_DB_PATH", path)
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    assert any("SYNTHETIC DEMO DATA" in e.value for e in at.error)
    conn = db.connect(path)
    logs = db.load_logs(conn)
    n = len(logs)
    assert n > 3000
    assert (logs["provenance"] == "synthetic").all() and (logs["source_type"] == "synthetic").all()
    n_iv = len(db.load_interventions(conn))
    # second start (new session) and a rerun must not duplicate
    AppTest.from_file(APP, default_timeout=60).run()
    at.run()
    assert len(db.load_logs(conn)) == n
    assert len(db.load_interventions(conn)) == n_iv == 1


def test_no_autoseed_when_db_has_user_data(tmp_path, monkeypatch):
    from datetime import date
    path = str(tmp_path / "user.db")
    monkeypatch.setattr(db, "DEFAULT_DB_PATH", path)
    conn = db.connect(path); db.init_db(conn)
    db.add_waste_log(conn, log_date=date(2026, 9, 1), session_label="mine", meal="Lunch",
                     item="Rice", stage="Plate waste", category="unknown", kg=1,
                     method="weighed (scale)", provenance="measured")
    AppTest.from_file(APP, default_timeout=60).run()
    assert len(db.load_logs(conn)) == 1
