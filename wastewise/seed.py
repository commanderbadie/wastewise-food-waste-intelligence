"""Synthetic demo data. Every row is tagged provenance='synthetic'. Not real canteen data."""
from __future__ import annotations

import random
from datetime import date, timedelta

from . import db

ITEMS = {
    "Breakfast": ["Idli", "Poha", "Bread slices", "Porridge"],
    "Lunch": ["Rice", "Dal", "Mixed vegetable curry", "Chapati", "Salad"],
    "Snacks": ["Samosa", "Tea biscuits", "Fruit"],
    "Dinner": ["Rice", "Dal", "Paneer curry", "Chapati"],
}
STAGE_W = [("Preparation", 0.2), ("Serving/Buffet", 0.25), ("Plate waste", 0.5), ("Storage", 0.05)]
SESSION = "DEMO-SYNTHETIC"


def seed_demo(conn, *, days: int = 28, end: date | None = None, rng_seed: int = 42) -> dict:
    """Idempotent: clears prior synthetic rows first. The synthetic intervention at the
    midpoint reduces lunch plate waste by construction (demo only)."""
    rng = random.Random(rng_seed)
    end = end or date.today()
    start = end - timedelta(days=days - 1)
    db.clear_synthetic(conn)
    switch = start + timedelta(days=days // 2)
    n = 0
    for d in range(days):
        day = start + timedelta(days=d)
        for meal, items in ITEMS.items():
            served = rng.randint(180, 260) if meal != "Snacks" else rng.randint(80, 140)
            db.upsert_meal_count(conn, log_date=day, session_label=SESSION, meal=meal,
                                 meals_served=served, provenance="synthetic")
            for item in items:
                for stage, w in STAGE_W:
                    if rng.random() > 0.55:
                        continue
                    kg = rng.uniform(0.3, 3.0) * w * (served / 200) * 2
                    if stage == "Plate waste" and meal == "Lunch" and day >= switch:
                        kg *= 0.7
                    cat = rng.choices(["avoidable", "unavoidable", "unknown"], [0.55, 0.3, 0.15])[0]
                    db.add_waste_log(conn, log_date=day, session_label=SESSION, meal=meal,
                                     item=item, stage=stage, category=cat, kg=round(kg, 2),
                                     method="weighed (scale)", provenance="synthetic",
                                     notes="synthetic demo row")
                    n += 1
    db.add_intervention(
        conn, name="[SYNTHETIC] Smaller lunch plates",
        description="Demo only: smaller default plate portions at lunch.",
        target_meal="Lunch", target_stage="Plate waste",
        baseline_start=start, baseline_end=switch - timedelta(days=1),
        followup_start=switch, followup_end=end, is_synthetic=True)
    return {"waste_rows": n, "days": days}
