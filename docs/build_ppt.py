"""Builds docs/Team_No_15.pptx (seminar deck). Run: python docs/build_ppt.py"""
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "screenshots"
GREEN, DARK, GREY = RGBColor(0x1B, 0x7F, 0x4B), RGBColor(0x22, 0x2B, 0x33), RGBColor(0x66, 0x66, 0x66)

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


def text(slide, x, y, w, h, s, size=20, bold=False, color=DARK):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    lines = s if isinstance(s, list) else [s]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.font.size, p.font.bold, p.font.color.rgb = Pt(size), bold, color
        p.space_after = Pt(8)
    return tb


def slide(title, bullets=None, size=20, note=None):
    s = prs.slides.add_slide(BLANK)
    bar = s.shapes.add_shape(1, 0, 0, prs.slide_width, Inches(1.1))
    bar.fill.solid(); bar.fill.fore_color.rgb = GREEN; bar.line.fill.background()
    text(s, 0.5, 0.18, 12, 0.8, title, 30, True, RGBColor(255, 255, 255))
    if bullets:
        text(s, 0.6, 1.4, 12.1, 5.2, ["• " + b for b in bullets], size)
    text(s, 0.5, 7.0, 12.3, 0.4, "Team No 15 | WasteWise | all demo data is SYNTHETIC" +
         (f" | {note}" if note else ""), 11, False, GREY)
    return s


def shot(s, name, x, y, w):
    s.shapes.add_picture(str(SHOTS / name), Inches(x), Inches(y), width=Inches(w))


# 1 Title
s = prs.slides.add_slide(BLANK)
bg = s.shapes.add_shape(1, 0, 0, prs.slide_width, prs.slide_height)
bg.fill.solid(); bg.fill.fore_color.rgb = GREEN; bg.line.fill.background()
text(s, 0.8, 2.0, 11.5, 1.2, "WasteWise", 54, True, RGBColor(255, 255, 255))
text(s, 0.8, 3.2, 11.5, 1.0, "Canteen Food-Waste Intelligence - measure, understand, reduce", 28,
     False, RGBColor(255, 255, 255))
text(s, 0.8, 4.6, 11.5, 1.2, ["Team No 15", "Seminar presentation | Supports UN SDG 12.3"], 24, True,
     RGBColor(255, 255, 255))

slide("Problem statement", [
    "Institutional canteens and hostel messes serve hundreds of meals a day, yet waste is rarely recorded.",
    "Where it occurs (preparation, surplus, serving line, plate, spoilage) and why is unknown.",
    "Without per-meal measurement, managers cannot target fixes or check whether a fix worked.",
    "Open per-meal Indian canteen data is not available (none found), so tools cannot be tested on real data.",
], 24)

slide("Context: SDG 12.3", [
    "UN SDG Target 12.3: halve per-capita global food waste at retail and consumer level, and reduce food "
    "losses along production and supply chains, by 2030.",
    "Canteens are a practical, controllable setting for measurement and pilots.",
    "WasteWise is a prototype that turns simple logs into evidence for action.",
], 24)

s = slide("Literature 1: Plate waste in school meals (Rezekne, Latvia)", [
    "Zenodo record, DOI 10.5281/zenodo.14164542 (read).",
    "Measured plate waste: about 21.1% of food served (89 g per child) at the start of the school year, "
    "19.4% (81 g) at the end.",
    "Relevance: shows plate waste can be measured as a share of food served per meal - the same "
    "denominator logic WasteWise uses (kg per meal served).",
    "Caveat: school study in Latvia, not India. Used as context only.",
], 20)

slide("Literature 2: Food wastage in Panjab University girls' hostels", [
    "Questionnaire study, 135 respondents. DOI 10.22271/27067483.2024.v6.i1f.279 (read).",
    "Perceived most-wasted items: rice 56.25%, vegetables 30%, chapati 13.5%.",
    "Perceived reasons for leftovers: bad taste 46%, poor serving 27%, overeating 18%, nutrition 9%.",
    "Relevance: closest Indian hostel setting; motivates tracking rice and disliked sabzi, and a "
    "taste/serving-focused action.",
    "Caveat: perceptions, not measured kg.",
], 20)

slide("Literature 3: WRI - Food Loss and Waste in India: The Knowns and The Unknowns", [
    "World Resources Institute working paper, DOI 10.46830/wriwp.20.00106 (abstract and key findings read).",
    "States that empirical research on food waste in India is very scarce and existing data are not comparable.",
    "Relevance: confirms the evidence gap that standardised, per-meal logging (WasteWise) aims to address.",
    "Caveat: we cite only its abstract-level conclusions.",
], 20)

slide("Gap and our idea", [
    "Gap: little measured, comparable, per-meal canteen data in India; no easy tool for kitchens.",
    "Idea: a lightweight logging + analytics tool: structured entries, kg per meal served, "
    "evidence-linked rule-based suggestions, and baseline vs follow-up tracking.",
    "Deliberately no machine learning and no environmental-impact claims in the MVP.",
], 24)

slide("Features", [
    "Structured logging: date/session, meal, item, stage, avoidable/unavoidable/unknown, kg, method, provenance.",
    "Dashboard summaries and filters; kg/meal shown only with a meals-served denominator.",
    "Rule-based recommendations (R1-R10) with a Suggested action and Evidence (rule, thresholds, numbers).",
    "Intervention tracking: kg/meal before vs after, days covered, coverage, causation caveat.",
    "Validation: rejects weight <= 0 or > 500 kg, future dates, duplicates. CSV export. Synthetic labels.",
], 21)

slide("Architecture and stack", [
    "Streamlit UI (app.py) over Python modules: db (SQLite), analytics, recommendations, "
    "demo_data + seed.",
    "Local SQLite with initialisation, migration and a deterministic, idempotent synthetic seed.",
    "Tests: pytest, 29 passing (run locally). Deployed on Streamlit Community Cloud.",
    "Honest limitation: SQLite on Streamlit Cloud is ephemeral; data resets on restart, then the demo re-seeds.",
], 22)

slide("Synthetic demo dataset (clearly labelled)", [
    "8 weeks, hostel mess + college canteen, 24 Indian items, about 3,956 waste rows, 316 meals-served rows.",
    "Fixed RNG seed, reproducible; every row source_type = synthetic; INR prices are assumptions.",
    "Embedded patterns: dinner rice overproduction, disliked lauki sabzi, spoilage events, exam/holiday days, "
    "a mid-period intervention.",
    "Not real, not validated, not India-measured.",
], 22)

s = slide("Live demo: dashboard (deployed app, owner-captured 2026-10-11)")
shot(s, "dashboard-kpis.png", 0.6, 1.3, 6.0)
shot(s, "dashboard-tables.png", 6.9, 1.3, 6.0)

s = slide("Live demo: recommendations with action and evidence")
shot(s, "recommendations.png", 2.4, 1.3, 8.4)

s = slide("Live demo: intervention impact")
shot(s, "interventions.png", 2.4, 1.3, 8.4)
text(s, 0.6, 6.5, 12, 0.5, "Synthetic demo outcome (about -38% dinner-rice kg/meal) is built into the generator - "
     "illustration, not a finding.", 14, True, GREEN)

slide("Results, verification and limitations", [
    "Tests run: pytest 29 passed, 0 failed.",
    "Verified live by the project owner (screenshots, 2026-10-11): app loads with auto-seeded synthetic data, "
    "dashboard, recommendations, intervention impact, export tab.",
    "Not verified live: add-record submit, CSV download.",
    "Limits: synthetic data, ephemeral storage, no ML, no auth, before/after does not prove causation.",
], 21)

slide("Future work", [
    "Pilot with a real canteen using weighed logs (with consent, no personal data).",
    "Durable storage (hosted database) and authentication.",
    "Richer analysis after real data exists; compare against published ranges.",
    "Menu/attendance forecasting only once enough validated data is collected.",
], 24)

slide("Thank you - Team No 15", [
    "Repo: github.com/commanderbadie/wastewise-food-waste-intelligence",
    "Live: wastewise-food-waste-intelligence-qeykaa8immms9xxex9aoin.streamlit.app",
    "Questions?",
], 22)

out = ROOT / "docs" / "Team_No_15.pptx"
prs.save(out)
print(out, len(prs.slides._sldIdLst), "slides")
