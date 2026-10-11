"""Transparent rule-based recommendations. Every output carries its evidence."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

MIN_ENTRIES = 5       # minimum log rows behind any recommendation
MIN_DAYS = 3          # minimum distinct days
PLATE_SHARE = 40.0    # % of total kg
PRECONSUMER_SHARE = 50.0
AVOIDABLE_SHARE = 50.0
UNKNOWN_SHARE = 25.0
ITEM_SHARE = 25.0
MEAL_SHARE = 40.0
MEASURED_MIN = 50.0


@dataclass
class Recommendation:
    rule_id: str
    title: str
    action: str
    evidence: dict = field(default_factory=dict)
    rows: int = 0
    synthetic_basis: bool = False

    def evidence_text(self) -> str:
        return "; ".join(f"{k}: {v}" for k, v in self.evidence.items())


def _ev(df: pd.DataFrame, **extra) -> dict:
    return {"log entries": len(df), "days": int(df["log_date"].nunique()),
            "kg in subset": round(float(df["kg"].sum()), 1), **extra,
            "provenance mix": df["provenance"].value_counts().to_dict()}


def generate(logs: pd.DataFrame) -> tuple[list[Recommendation], str | None]:
    """Return (recommendations, message-if-none)."""
    if len(logs) < MIN_ENTRIES or logs["log_date"].nunique() < MIN_DAYS:
        return [], (f"Not enough data: need at least {MIN_ENTRIES} entries over "
                    f"{MIN_DAYS} days to generate recommendations.")
    total = float(logs["kg"].sum())
    if total <= 0:
        return [], "Total logged waste is 0 kg; nothing to recommend."
    recs: list[Recommendation] = []

    def add(rule, title, action, subset, **extra):
        recs.append(Recommendation(rule, title, action, _ev(subset, **extra), len(subset),
                                   bool((subset["provenance"] == "synthetic").any())))

    plate = logs[logs["stage"] == "Plate waste"]
    s = plate["kg"].sum() / total * 100
    if s >= PLATE_SHARE:
        add("R1-PLATE", "Plate waste dominates",
            "Pilot smaller default portions or 'take less, return for more', then track "
            "it as an intervention.", plate,
            **{"plate-waste share of kg": f"{s:.0f}% (threshold {PLATE_SHARE:.0f}%)"})

    pre = logs[logs["stage"].isin(["Preparation", "Serving/Buffet", "Storage"])]
    s = pre["kg"].sum() / total * 100
    if s >= PRECONSUMER_SHARE:
        add("R2-PRODUCTION", "Pre-consumer waste is high",
            "Compare production quantities with meals served; consider batch cooking "
            "or staggered replenishment.", pre,
            **{"pre-consumer share of kg": f"{s:.0f}% (threshold {PRECONSUMER_SHARE:.0f}%)"})

    avoid = logs[logs["category"] == "avoidable"]
    s = avoid["kg"].sum() / total * 100
    if s >= AVOIDABLE_SHARE:
        add("R3-AVOIDABLE", "Majority of waste is avoidable",
            "Prioritise the top avoidable items for portioning or menu review.", avoid,
            **{"avoidable share of kg": f"{s:.0f}% (threshold {AVOIDABLE_SHARE:.0f}%)"})

    unk = logs[logs["category"] == "unknown"]
    s = unk["kg"].sum() / total * 100
    if s >= UNKNOWN_SHARE:
        add("R4-CLASSIFY", "Too much waste is unclassified",
            "Train staff to tag waste as avoidable/unavoidable so priorities are reliable.",
            unk, **{"unknown share of kg": f"{s:.0f}% (threshold {UNKNOWN_SHARE:.0f}%)"})

    items = logs.groupby("item")["kg"].sum().sort_values(ascending=False)
    top, kg = items.index[0], float(items.iloc[0])
    if kg / total * 100 >= ITEM_SHARE:
        add("R5-TOP-ITEM", f"'{top}' is the largest single waste item",
            f"Review recipe, portion size and demand for '{top}'.", logs[logs["item"] == top],
            **{"item share of kg": f"{kg / total * 100:.0f}% (threshold {ITEM_SHARE:.0f}%)"})

    meals = logs.groupby("meal")["kg"].sum().sort_values(ascending=False)
    if len(meals) > 1:
        m, kg = meals.index[0], float(meals.iloc[0])
        if kg / total * 100 >= MEAL_SHARE:
            add("R6-MEAL", f"{m} generates the most waste",
                f"Focus the first pilot on {m} service.", logs[logs["meal"] == m],
                **{"meal share of kg": f"{kg / total * 100:.0f}% (threshold {MEAL_SHARE:.0f}%)",
                   "caveat": "raw kg, not normalised by meals served"})

    meas = (logs["provenance"] == "measured").mean() * 100
    if meas < MEASURED_MIN:
        add("R7-MEASURE", "Improve measurement quality",
            "Weigh waste with a scale where possible; most entries are estimated or synthetic.",
            logs, **{"measured entries": f"{meas:.0f}% (threshold {MEASURED_MIN:.0f}%)"})
    if not recs:
        return [], "No rule threshold was triggered by the current filtered data."
    return recs, None
