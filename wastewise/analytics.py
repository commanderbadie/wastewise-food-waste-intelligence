"""Aggregations. kg/meal is only reported where a meals-served denominator exists."""
from __future__ import annotations

import pandas as pd

KEYS = ["log_date", "session_label", "meal"]


def filter_logs(logs: pd.DataFrame, *, start=None, end=None, meals=None, stages=None,
                categories=None, provenance=None) -> pd.DataFrame:
    df = logs
    if df.empty:
        return df
    if start:
        df = df[df["log_date"] >= str(start)]
    if end:
        df = df[df["log_date"] <= str(end)]
    for col, vals in (("meal", meals), ("stage", stages), ("category", categories),
                      ("provenance", provenance)):
        if vals:
            df = df[df[col].isin(vals)]
    return df


def kg_per_meal(logs: pd.DataFrame, counts: pd.DataFrame) -> dict:
    """kg/meal using only (date, session, meal) groups that have a denominator.

    Also reports kg that could not be normalised, so nothing is silently dropped.
    """
    total_kg = float(logs["kg"].sum()) if not logs.empty else 0.0
    if logs.empty or counts.empty:
        return {"total_kg": total_kg, "kg_matched": 0.0, "meals_served": 0,
                "kg_per_meal": None, "kg_unmatched": total_kg}
    waste = logs.groupby(KEYS, as_index=False)["kg"].sum()
    m = waste.merge(counts[KEYS + ["meals_served"]], on=KEYS, how="left")
    matched = m[m["meals_served"].notna()]
    meals = int(matched["meals_served"].sum())
    kg_m = float(matched["kg"].sum())
    return {"total_kg": total_kg, "kg_matched": kg_m, "meals_served": meals,
            "kg_per_meal": (kg_m / meals) if meals > 0 else None,
            "kg_unmatched": total_kg - kg_m}


def kg_per_meal_by_meal(logs: pd.DataFrame, counts: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if not logs.empty:
        for meal, sub in logs.groupby("meal"):
            r = kg_per_meal(sub, counts[counts["meal"] == meal])
            r["meal"] = meal
            rows.append(r)
    return pd.DataFrame(rows)


def summarize(logs: pd.DataFrame, by: str) -> pd.DataFrame:
    if logs.empty:
        return pd.DataFrame(columns=[by, "kg", "share_pct"])
    s = logs.groupby(by, as_index=False)["kg"].sum().sort_values("kg", ascending=False)
    total = s["kg"].sum()
    s["share_pct"] = (s["kg"] / total * 100).round(1) if total > 0 else 0.0
    return s


def daily_totals(logs: pd.DataFrame) -> pd.DataFrame:
    if logs.empty:
        return pd.DataFrame(columns=["log_date", "kg"])
    return logs.groupby("log_date", as_index=False)["kg"].sum()


def evaluate_intervention(logs, counts, iv) -> dict:
    """Compare baseline vs follow-up. Descriptive only; not a causal estimate."""
    def period(a, b):
        sub = filter_logs(logs, start=a, end=b)
        c = counts
        if not sub.empty:
            if iv["target_meal"] != "All":
                sub = sub[sub["meal"] == iv["target_meal"]]
            if iv["target_stage"] != "All":
                sub = sub[sub["stage"] == iv["target_stage"]]
        if not c.empty:
            c = c[(c["log_date"] >= a) & (c["log_date"] <= b)]
            if iv["target_meal"] != "All":
                c = c[c["meal"] == iv["target_meal"]]
        res = kg_per_meal(sub, c)
        keys = ["log_date", "session_label", "meal"]
        svc = sub[keys].drop_duplicates() if not sub.empty else None
        n_svc = 0 if svc is None else len(svc)
        n_cov = 0 if svc is None or c.empty else len(svc.merge(c[keys].drop_duplicates(), on=keys))
        res["services_logged"] = n_svc
        res["services_with_meals_served"] = n_cov
        res["coverage_pct"] = round(n_cov / n_svc * 100, 1) if n_svc else None
        res["days_logged"] = int(sub["log_date"].nunique()) if not sub.empty else 0
        res["provenance_mix"] = (sub["provenance"].value_counts().to_dict()
                                 if not sub.empty else {})
        return res

    base = period(iv["baseline_start"], iv["baseline_end"])
    follow = period(iv["followup_start"], iv["followup_end"])
    change = None
    if base["kg_per_meal"] and follow["kg_per_meal"] is not None:
        change = (follow["kg_per_meal"] - base["kg_per_meal"]) / base["kg_per_meal"] * 100
    return {"baseline": base, "followup": follow, "change_pct": change,
            "sufficient": base["days_logged"] >= 3 and follow["days_logged"] >= 3
            and change is not None}


def estimate_cost(logs: pd.DataFrame, costs: pd.DataFrame) -> dict:
    """Waste value in INR using assumed per-kg prices; unpriced items are reported, not guessed."""
    if logs.empty or costs.empty:
        return {"inr": None, "kg_priced": 0.0, "kg_unpriced": float(logs["kg"].sum())}
    m = logs.merge(costs[["item", "inr_per_kg"]], on="item", how="left")
    priced = m[m["inr_per_kg"].notna()]
    return {"inr": float((priced["kg"] * priced["inr_per_kg"]).sum()),
            "kg_priced": float(priced["kg"].sum()),
            "kg_unpriced": float(m[m["inr_per_kg"].isna()]["kg"].sum())}
