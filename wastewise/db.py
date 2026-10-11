"""SQLite storage layer for WasteWise."""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import date

import pandas as pd

DEFAULT_DB_PATH = os.environ.get("WASTEWISE_DB", "wastewise.db")

MEALS = ["Breakfast", "Lunch", "Snacks", "Dinner"]
STAGES = ["Storage", "Preparation", "Serving/Buffet", "Plate waste"]
CATEGORIES = ["avoidable", "unavoidable", "unknown"]
METHODS = ["weighed (scale)", "visual estimate", "container count", "other"]
PROVENANCE = ["measured", "estimated", "synthetic"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS waste_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_date TEXT NOT NULL,
    session_label TEXT NOT NULL,
    meal TEXT NOT NULL,
    item TEXT NOT NULL,
    stage TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('avoidable','unavoidable','unknown')),
    kg REAL NOT NULL CHECK (kg >= 0),
    method TEXT NOT NULL,
    provenance TEXT NOT NULL CHECK (provenance IN ('measured','estimated','synthetic')),
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS meal_counts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_date TEXT NOT NULL,
    session_label TEXT NOT NULL,
    meal TEXT NOT NULL,
    meals_served INTEGER NOT NULL CHECK (meals_served > 0),
    provenance TEXT NOT NULL CHECK (provenance IN ('measured','estimated','synthetic')),
    UNIQUE (log_date, session_label, meal)
);
CREATE TABLE IF NOT EXISTS interventions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    target_meal TEXT DEFAULT 'All',
    target_stage TEXT DEFAULT 'All',
    baseline_start TEXT NOT NULL,
    baseline_end TEXT NOT NULL,
    followup_start TEXT NOT NULL,
    followup_end TEXT NOT NULL,
    is_synthetic INTEGER NOT NULL DEFAULT 0
);
"""


def connect(path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or DEFAULT_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


@contextmanager
def session(path: str | None = None):
    conn = connect(path)
    try:
        init_db(conn)
        yield conn
    finally:
        conn.close()


def add_waste_log(conn, *, log_date, session_label, meal, item, stage, category,
                  kg, method, provenance, notes="") -> int:
    if meal not in MEALS or stage not in STAGES:
        raise ValueError("invalid meal or stage")
    if category not in CATEGORIES:
        raise ValueError("invalid category")
    if provenance not in PROVENANCE:
        raise ValueError("invalid provenance")
    if kg is None or float(kg) < 0:
        raise ValueError("kg must be >= 0")
    if not str(item).strip():
        raise ValueError("item is required")
    cur = conn.execute(
        "INSERT INTO waste_logs (log_date, session_label, meal, item, stage, category,"
        " kg, method, provenance, notes) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (str(log_date), session_label.strip() or "default", meal, item.strip(), stage,
         category, float(kg), method, provenance, notes),
    )
    conn.commit()
    return cur.lastrowid


def upsert_meal_count(conn, *, log_date, session_label, meal, meals_served, provenance) -> None:
    if int(meals_served) <= 0:
        raise ValueError("meals_served must be > 0")
    conn.execute(
        "INSERT INTO meal_counts (log_date, session_label, meal, meals_served, provenance)"
        " VALUES (?,?,?,?,?) ON CONFLICT(log_date, session_label, meal)"
        " DO UPDATE SET meals_served=excluded.meals_served, provenance=excluded.provenance",
        (str(log_date), session_label.strip() or "default", meal, int(meals_served), provenance),
    )
    conn.commit()


def add_intervention(conn, *, name, description, target_meal, target_stage,
                     baseline_start, baseline_end, followup_start, followup_end,
                     is_synthetic=False) -> int:
    b0, b1, f0, f1 = (str(x) for x in (baseline_start, baseline_end, followup_start, followup_end))
    if not (b0 <= b1 < f0 <= f1):
        raise ValueError("Require baseline_start <= baseline_end < followup_start <= followup_end")
    if not name.strip():
        raise ValueError("name is required")
    cur = conn.execute(
        "INSERT INTO interventions (name, description, target_meal, target_stage, baseline_start,"
        " baseline_end, followup_start, followup_end, is_synthetic) VALUES (?,?,?,?,?,?,?,?,?)",
        (name.strip(), description, target_meal, target_stage, b0, b1, f0, f1, int(is_synthetic)),
    )
    conn.commit()
    return cur.lastrowid


def load_logs(conn) -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM waste_logs ORDER BY log_date, id", conn)


def load_counts(conn) -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM meal_counts ORDER BY log_date", conn)


def load_interventions(conn) -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM interventions ORDER BY id", conn)


def clear_synthetic(conn) -> None:
    conn.execute("DELETE FROM waste_logs WHERE provenance='synthetic'")
    conn.execute("DELETE FROM meal_counts WHERE provenance='synthetic'")
    conn.execute("DELETE FROM interventions WHERE is_synthetic=1")
    conn.commit()


def today() -> date:
    return date.today()
