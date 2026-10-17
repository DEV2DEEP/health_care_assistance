"""Rule-based healthcare assistant engine (no ML, deterministic, testable).

General information only. Not a diagnosis or a substitute for a clinician.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional

from kb import SOURCES
from retriever import confidence, retrieve, section_for

DISCLAIMER = ("I share general health information only. I can't diagnose or prescribe. "
              "For personal medical advice, please consult a qualified doctor.")

EMERGENCY_TEXT = (
    "**This may be an emergency.** Call your local emergency number now "
    "(India: **112**, ambulance **108**) or go to the nearest emergency department. "
    "Don't wait for an online answer, and don't drive yourself if you feel faint or unwell."
)
CRISIS_TEXT = (
    "I'm really sorry you're feeling this way. You deserve support right now. "
    "Please contact someone immediately: in India, **Tele-MANAS 14416** (free, 24x7) or "
    "emergency **112**; elsewhere, your local crisis line. If you're in immediate danger, "
    "call emergency services or reach a trusted person near you."
)

EMERGENCY_PATTERNS = [
    r"chest (pain|pressure|tightness)", r"(can'?t|cannot|unable to|difficulty|trouble) breath",
    r"short(ness)? of breath", r"(face|arm) (is )?droop", r"slurred speech", r"sudden (weakness|numbness|confusion)",
    r"(?<!heat )(?<!sun)\bstroke\b", r"heart attack", r"unconscious|passed out|not responding|fainted", r"seizure|convulsion",
    r"(severe|heavy|uncontrolled) bleeding", r"overdose|(?<!food )poison(ed|ing)?", r"anaphyla|throat (is )?swelling",
    r"coughing (up )?blood|vomiting blood", r"severe allergic",
]
CRISIS_PATTERNS = [r"suicid", r"kill myself", r"end my life", r"want to die", r"self[- ]harm", r"hurt myself"]

APPOINTMENT_WORDS = ["appointment", "book a doctor", "schedule a visit", "see a doctor", "consultation"]
MED_WORDS = ["medication", "medicine", "tablet", "pill", "dose", "dosage", "drug", "prescription", "antibiotic", "antibiotics", "painkiller", "paracetamol", "ibuprofen", "aspirin"]
DOSE_WORDS = ["dose", "dosage", "how much", "how many", "overdose", "mg", "which", "should i take", "can i take"]
GREET = ["hello", "hi", "hey", "good morning", "good evening", "namaste"]
THANKS = ["thank", "thanks", "thx"]


@dataclass
class Reply:
    text: str
    kind: str  # emergency | crisis | info | appointment | medication | smalltalk | fallback
    intent: Optional[str] = None
    matched: List[str] = field(default_factory=list)
    confidence: str = "n/a"  # high | ambiguous | none | n/a
    sources: List[str] = field(default_factory=list)
    context: List[dict] = field(default_factory=list)  # retrieved topics (for optional grounded LLM)


def _norm(t):
    return re.sub(r"\s+", " ", t.lower().strip())


def _has(text, words):
    hits = []
    for w in words:
        if re.search(r"(?<!\w)" + re.escape(w.strip()) + r"(?!\w)", text):
            hits.append(w.strip())
    return hits


def respond(user_input: str) -> Reply:
    t = _norm(user_input)
    if not t:
        return Reply("Please type a question.", "fallback")
    for p in CRISIS_PATTERNS:
        if re.search(p, t):
            return Reply(CRISIS_TEXT, "crisis", "crisis", [p])
    for p in EMERGENCY_PATTERNS:
        if re.search(p, t):
            return Reply(EMERGENCY_TEXT, "emergency", "emergency", [p])
    if _has(t, APPOINTMENT_WORDS):
        return Reply("I can help with that. Open the **Appointments** tab to pick a department, date and time.",
                     "appointment", "appointment")
    meds = _has(t, MED_WORDS)
    if meds:
        if _has(t, DOSE_WORDS):
            return Reply("I can't recommend specific medicines or doses, since the right choice depends on age, weight, other conditions, "
                         "allergies and interactions. Please check the label, or ask your doctor or pharmacist.",
                         "medication", "dose_refusal", meds)
        return Reply("Take medicines exactly as prescribed, at the same times each day, and don't stop or change them "
                     "without your doctor's advice. Ask your pharmacist about side effects or interactions. "
                     "The **Reminders** tab can help you stay on schedule.", "medication", "medication", meds)
    hits = retrieve(t)
    if hits:
        conf = confidence(hits)
        top = hits[0].topic
        sec = section_for(t)
        parts = {"about": top["about"], "self_care": top["self_care"], "seek_care": top["seek_care"], "prevention": top["prevention"]}
        if sec and parts.get(sec):
            body = f"**{top['title']}**\n\n{parts[sec]}"
            if sec != "seek_care" and top["seek_care"]:
                body += f"\n\n**See a doctor promptly if:** {top['seek_care']}"
        else:
            body = f"**{top['title']}**\n\n{top['about']}\n\n**What helps:** {top['self_care']}"
            if top["seek_care"]:
                body += f"\n\n**See a doctor promptly if:** {top['seek_care']}"
        if conf == "ambiguous":
            body += "\n\n_Your message may relate to more than one topic: " + ", ".join(h.topic["title"] for h in hits[1:]) + ". Ask about each for details._"
        body += f"\n\n_{DISCLAIMER}_"
        return Reply(body, "info", top["id"], hits[0].matched, conf, top["sources"], [h.topic for h in hits])
    if _has(t, THANKS):
        return Reply("You're welcome. Take care!", "smalltalk", "thanks")
    if _has(t, GREET) and len(t.split()) <= 4:
        return Reply("Hello! I can answer general health questions, check symptoms, book appointments and set medicine reminders.",
                     "smalltalk", "greet")
    return Reply("I'm not sure I understood. Try asking about a symptom (fever, cough, headache, stomach upset...), "
                 "or use the **Symptom Checker**. For anything urgent, contact a doctor or call 112.", "fallback", None, [], "none")


# ---------------------------------------------------------------- triage
CHECKER_SYMPTOMS = ["Fever", "Cough", "Sore throat", "Headache", "Body ache", "Nausea/vomiting", "Diarrhea",
                    "Shortness of breath", "Chest pain", "Rash", "Fatigue", "Loss of smell/taste"]
RED_SYMPTOMS = {"Shortness of breath", "Chest pain"}


def triage(symptoms, days, severity, age_group, chronic):
    """Return (level, reasons). Transparent rules; levels: emergency, doctor_soon (within 24h), doctor_visit (book a visit), self_care."""
    why = []
    if RED_SYMPTOMS & set(symptoms):
        return "emergency", [f"{s} is a red-flag symptom" for s in sorted(RED_SYMPTOMS & set(symptoms))]
    score = 0
    if severity >= 8:
        score += 3; why.append("severity 8 or higher")
    elif severity >= 5:
        score += 1; why.append("moderate severity")
    if days >= 7:
        score += 2; why.append("symptoms for a week or longer")
    elif days >= 3:
        score += 1; why.append("symptoms for 3 or more days")
    if len(symptoms) >= 4:
        score += 1; why.append("several symptoms together")
    if "Fever" in symptoms and days >= 3:
        score += 1; why.append("fever persisting 3 or more days")
    if age_group in ("Infant/child (<5)", "Older adult (65+)"):
        score += 2; why.append(f"age group: {age_group}")
    if chronic:
        score += 1; why.append("existing chronic condition")
    if score >= 4:
        return "doctor_soon", why
    if score >= 2:
        return "doctor_visit", why
    return "self_care", why or ["no risk factors selected"]
