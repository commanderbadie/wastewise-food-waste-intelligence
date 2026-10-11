"""Deterministic SYNTHETIC demo dataset: an invented Indian hostel mess + college canteen.

Nothing here is real, measured, validated or India-measured. Every row carries
provenance='synthetic' and source_type='synthetic', and notes start with 'SYNTHETIC'.
All magnitudes are assumptions chosen to be plausible and to embed the documented
patterns below (see README, "Synthetic demo dataset").

Embedded patterns (so rule-based recommendations fire with evidence):
  P1  Recurring dinner rice overproduction at the hostel mess (surplus stage), worse on
      weekends. Halved after the intervention date.
  P2  Plate-waste spike on a disliked sabzi ("Lauki sabzi", served Tue and Fri lunch).
  P3  Occasional spoilage events (fixed list, SPOILAGE_EVENTS).
  P4  Exam week (attendance falls at the canteen, forecasts not adjusted -> more surplus)
      and two assumed holidays (canteen closed, hostel attendance falls).
  P5  Mid-period intervention: "dinner rice: cook in two batches" (day index weeks*7//2).
"""
from __future__ import annotations

import random
from datetime import date, timedelta

DEMO_START = date(2026, 8, 17)  # a Monday; 8 weeks -> ends Sunday 2026-10-11
DEMO_SEED = 42
HOSTEL, CANTEEN = "Hostel Mess", "College Canteen"
SOURCE = "synthetic"

# name: (portion kg/serving, plate-waste fraction, preparation-trim fraction,
#        serving-line fraction, base surplus fraction, assumed INR per kg)
ITEMS = {
    "Rice": (0.16, 0.14, 0.0, 0.012, 0.05, 18),
    "Dal": (0.12, 0.13, 0.0, 0.010, 0.05, 35),
    "Roti": (0.07, 0.09, 0.0, 0.010, 0.06, 30),
    "Sambar": (0.10, 0.12, 0.01, 0.010, 0.05, 22),
    "Idli": (0.10, 0.07, 0.0, 0.008, 0.06, 25),
    "Poha": (0.12, 0.12, 0.01, 0.010, 0.05, 30),
    "Upma": (0.12, 0.20, 0.01, 0.010, 0.05, 28),
    "Aloo paratha": (0.10, 0.10, 0.01, 0.010, 0.05, 55),
    "Bread and butter": (0.06, 0.08, 0.0, 0.005, 0.04, 45),
    "Aloo gobi": (0.10, 0.20, 0.03, 0.010, 0.05, 28),
    "Bhindi masala": (0.10, 0.26, 0.03, 0.010, 0.05, 32),
    "Mixed veg": (0.10, 0.22, 0.03, 0.010, 0.05, 28),
    "Lauki sabzi": (0.10, 0.46, 0.03, 0.010, 0.05, 20),  # P2: disliked
    "Chole": (0.12, 0.12, 0.01, 0.010, 0.05, 50),
    "Rajma": (0.12, 0.12, 0.01, 0.010, 0.05, 55),
    "Paneer butter masala": (0.08, 0.12, 0.01, 0.010, 0.05, 150),
    "Kadhi": (0.10, 0.16, 0.0, 0.010, 0.05, 30),
    "Khichdi": (0.15, 0.10, 0.01, 0.010, 0.05, 25),
    "Curd": (0.08, 0.08, 0.0, 0.010, 0.04, 60),
    "Salad": (0.04, 0.35, 0.06, 0.010, 0.05, 25),
    "Samosa": (0.08, 0.05, 0.0, 0.005, 0.05, 70),
    "Pakora": (0.07, 0.06, 0.0, 0.005, 0.05, 80),
    "Tea biscuits": (0.03, 0.04, 0.0, 0.005, 0.03, 120),
    "Banana": (0.12, 0.20, 0.0, 0.005, 0.04, 50),
}
SABZI_LUNCH = ["Aloo gobi", "Lauki sabzi", "Paneer butter masala", "Bhindi masala",
               "Lauki sabzi", "Chole", "Rajma"]  # Mon..Sun
SABZI_DINNER = ["Mixed veg", "Kadhi", "Chole", "Paneer butter masala", "Mixed veg",
                "Khichdi", "Aloo gobi"]
BREAKFAST = [["Poha"], ["Idli", "Sambar"], ["Aloo paratha", "Curd"], ["Upma"],
             ["Idli", "Sambar"], ["Poha"], ["Aloo paratha", "Curd"]]
SNACKS = [["Samosa", "Tea biscuits"], ["Pakora", "Tea biscuits"], ["Banana", "Tea biscuits"],
          ["Samosa", "Tea biscuits"], ["Pakora", "Tea biscuits"], ["Banana", "Tea biscuits"],
          ["Tea biscuits"]]

# Base meals served, (weekday, weekend) for the hostel; weekday only for the canteen.
HOSTEL_COUNTS = {"Breakfast": (360, 220), "Lunch": (390, 300), "Snacks": (250, 200),
                 "Dinner": (410, 330)}
CANTEEN_COUNTS = {"Breakfast": 260, "Lunch": 650, "Snacks": 480}

# P3: (day offset from start, outlet, meal, item, kg, note)
SPOILAGE_EVENTS = [
    (5, HOSTEL, "Dinner", "Curd", 6.5, "power cut, curd soured"),
    (12, HOSTEL, "Dinner", "Rice", 14.0, "cooked rice stored overnight, discarded"),
    (17, HOSTEL, "Breakfast", "Bread and butter", 3.8, "mould on bread"),
    (24, CANTEEN, "Snacks", "Banana", 5.2, "over-ripe stock"),
    (33, HOSTEL, "Breakfast", "Idli", 4.0, "batter over-fermented"),
    (43, HOSTEL, "Dinner", "Curd", 7.0, "fridge failure"),
    (51, CANTEEN, "Snacks", "Samosa", 6.0, "unsold, spoiled in hot weather"),
]

PATTERNS = {
    "P1": "Recurring dinner rice overproduction (hostel mess), worse at weekends",
    "P2": "Plate-waste spike on disliked Lauki sabzi (Tue/Fri lunch)",
    "P3": "Occasional spoilage events",
    "P4": "Exam week and assumed holidays change attendance; forecasts not adjusted",
    "P5": "Intervention from mid-period: dinner rice cooked in two batches",
}


def _method(rng, stage, kg):
    r = rng.random()
    if stage == "Plate waste":
        m = "weighed (scale)" if r < 0.60 else "visual estimate"
    elif stage in ("Surplus/Overproduction", "Spoilage"):
        m = ("weighed (scale)" if r < 0.55 else
             "container count" if r < 0.85 else "visual estimate")
    elif stage == "Preparation":
        m = "weighed (scale)" if r < 0.80 else "visual estimate"
    else:
        m = "weighed (scale)" if r < 0.50 else "visual estimate"
    if m == "container count" and kg < 5:
        m = "visual estimate"
    return m


def _apply_method(rng, method, kg):
    if method == "weighed (scale)":
        return round(kg, 2)
    if method == "container count":  # assumed 5 kg container
        return float(max(5, round(kg / 5) * 5))
    kg = kg * rng.uniform(0.85, 1.15)
    return max(0.25, round(kg / 0.25) * 0.25)


def _category(rng, stage):
    r = rng.random()
    if stage == "Preparation":
        return "unavoidable" if r < 0.88 else "unknown"
    if stage == "Surplus/Overproduction":
        return "avoidable" if r < 0.85 else "unknown"
    if stage == "Serving/Buffet":
        return "avoidable" if r < 0.60 else "unknown"
    if stage == "Spoilage":
        return "avoidable"
    return "avoidable" if r < 0.62 else ("unavoidable" if r < 0.80 else "unknown")


def generate_dataset(start: date = DEMO_START, weeks: int = 8, rng_seed: int = DEMO_SEED) -> dict:
    """Pure function: same arguments -> identical output."""
    rng = random.Random(rng_seed)
    days = weeks * 7
    switch = days // 2
    exam = range(14, 21)
    holidays = {21, 46}
    waste, counts = [], []
    spoil = {(d, o, m, i): (kg, n) for d, o, m, i, kg, n in SPOILAGE_EVENTS if d < days}

    def add(day, outlet, meal, item, stage, kg, tag=""):
        if kg < 0.05:
            return
        method = _method(rng, stage, kg)
        kg = _apply_method(rng, method, kg)
        note = "SYNTHETIC demo row" + (f"; {tag}" if tag else "")
        waste.append({"log_date": day.isoformat(), "session_label": outlet, "meal": meal,
                      "item": item, "stage": stage, "category": _category(rng, stage),
                      "kg": kg, "method": method, "provenance": "synthetic",
                      "notes": note, "source_type": SOURCE})

    def noise():
        return max(0.3, rng.gauss(1.0, 0.18))

    for d in range(days):
        day = start + timedelta(days=d)
        wd = day.weekday()
        weekend = wd >= 5
        is_exam, is_hol = d in exam, d in holidays
        services = []
        for meal, (wk, we) in HOSTEL_COUNTS.items():
            mult = 1.05 if is_exam else (0.65 if is_hol else 1.0)
            services.append((HOSTEL, meal, (we if weekend else wk) * mult))
        if not weekend and not is_hol:
            for meal, base in CANTEEN_COUNTS.items():
                services.append((CANTEEN, meal, base * (0.75 if is_exam else 1.0)))
        for outlet, meal, base in services:
            served = max(20, round(base * (1 + rng.gauss(0, 0.05))))
            if rng.random() > 0.07:  # ~7% of services have no meals-served count
                counts.append({"log_date": day.isoformat(), "session_label": outlet,
                               "meal": meal, "meals_served": served,
                               "provenance": "synthetic", "source_type": SOURCE})
            if meal == "Breakfast":
                menu = BREAKFAST[wd] + ["Bread and butter"]
            elif meal == "Snacks":
                menu = SNACKS[wd]
            elif meal == "Lunch":
                menu = ["Rice", "Dal", "Roti", SABZI_LUNCH[wd], "Curd", "Salad"]
            else:
                menu = ["Rice", "Dal", "Roti", SABZI_DINNER[wd]]
                if wd in (1, 4):
                    menu.append("Curd")
            for item in menu:
                portion, plate, prep, serve, over, _ = ITEMS[item]
                tag = []
                if item == "Rice" and meal == "Dinner" and outlet == HOSTEL:
                    over = 0.36 if weekend else 0.28
                    if d >= switch:
                        over *= 0.5
                    tag.append("P1 dinner-rice-overproduction")
                if item == "Lauki sabzi":
                    tag.append("P2 disliked-sabzi")
                forecast = 1.0
                if is_exam or is_hol:
                    forecast = 1.4 if is_exam else 1.5
                    tag.append("P4 exam-week" if is_exam else "P4 holiday")
                tagtxt = "; ".join(tag)
                food = served * portion
                if prep:
                    add(day, outlet, meal, item, "Preparation", food * prep * noise(), tagtxt)
                add(day, outlet, meal, item, "Surplus/Overproduction",
                    food * over * forecast * noise(), tagtxt)
                add(day, outlet, meal, item, "Serving/Buffet", food * serve * noise(), tagtxt)
                add(day, outlet, meal, item, "Plate waste", food * plate * noise(), tagtxt)
        for (sd, o, m, i), (kg, note) in spoil.items():
            if sd == d:
                add(day, o, m, i, "Spoilage", kg, f"P3 spoilage: {note}")

    costs = [{"item": k, "inr_per_kg": float(v[5]), "is_assumption": 1, "source_type": SOURCE}
             for k, v in ITEMS.items()]
    end = start + timedelta(days=days - 1)
    mid = start + timedelta(days=switch)
    interventions = [dict(
        name="[SYNTHETIC] Dinner rice: cook in two batches",
        description="Synthetic demo intervention: cook hostel dinner rice in two batches "
                    "instead of one. The effect is built into the generator.",
        target_meal="Dinner", target_stage="Surplus/Overproduction",
        baseline_start=start, baseline_end=mid - timedelta(days=1),
        followup_start=mid, followup_end=end, is_synthetic=True)]
    return {"waste_logs": waste, "meal_counts": counts, "item_costs": costs,
            "interventions": interventions}
