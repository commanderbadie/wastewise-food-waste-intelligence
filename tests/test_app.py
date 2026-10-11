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
