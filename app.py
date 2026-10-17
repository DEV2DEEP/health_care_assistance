"""Healthcare Assistant (Streamlit). General information only, not medical advice."""
import uuid
from datetime import date, datetime, time, timedelta

import streamlit as st

import llm
from engine import CHECKER_SYMPTOMS, DISCLAIMER, respond, triage
from kb import REVIEW_STATUS, SOURCES

st.set_page_config(page_title="Healthcare Assistant", page_icon="🩺", layout="centered")

DEPARTMENTS = ["General Medicine", "Pediatrics", "Cardiology", "Dermatology", "Orthopedics", "ENT", "Gynecology", "Psychiatry"]
SLOTS = [time(h, m) for h in range(9, 17) for m in (0, 30)]

ss = st.session_state
ss.setdefault("chat", [{"role": "assistant", "content": "Hello! Ask me a general health question, or use the tabs above."}])
ss.setdefault("appointments", [])
ss.setdefault("reminders", [])


with st.sidebar:
    st.header("Settings")
    use_llm = st.toggle("Grounded AI rewording", value=False, disabled=not llm.available(),
                        help="Needs ANTHROPIC_API_KEY. The AI may only rephrase vetted passages and can't add facts.")
    st.caption("Answers come from a curated knowledge base with cited sources. If the assistant isn't sure, it says so instead of guessing. "
               "Emergencies, doses and crises are always handled by fixed safety rules.")
    if st.button("Clear chat"):
        ss.chat = ss.chat[:1]
        st.rerun()
    st.divider()
    st.markdown("**Emergency (India):** 112 · Ambulance 108 · Tele-MANAS 14416")
    st.caption(f"Content status: {REVIEW_STATUS}")

st.title("🩺 Healthcare Assistant")
st.warning(DISCLAIMER)
tab_chat, tab_check, tab_appt, tab_rem = st.tabs(["💬 Chat", "🔍 Symptom Checker", "📅 Appointments", "💊 Reminders"])

# ------------------------------------------------------------------ chat
with tab_chat:
    for m in ss.chat:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
    if prompt := st.chat_input("Describe your symptom or ask a question"):
        ss.chat.append({"role": "user", "content": prompt})
        r = respond(prompt)
        text = r.text
        if r.kind == "info":
            if use_llm:
                g = llm.grounded_answer(prompt, r.context[:2])
                if g and "don't have reliable information" not in g:
                    text = g + f"\n\n_{DISCLAIMER}_"
            text += "\n\n" + " · ".join(f"[{s}]({SOURCES[s]})" for s in r.sources)
            text += f"\n\n`confidence: {r.confidence}`"
        ss.chat.append({"role": "assistant", "content": text})
        st.rerun()

# ------------------------------------------------------- symptom checker
with tab_check:
    st.subheader("Symptom checker")
    st.caption("Transparent rule-based triage. It shows why it gave its result.")
    with st.form("checker"):
        syms = st.multiselect("Symptoms", CHECKER_SYMPTOMS)
        c1, c2 = st.columns(2)
        days = c1.number_input("Days with symptoms", 0, 60, 1)
        sev = c2.slider("Severity (1-10)", 1, 10, 3)
        age = st.selectbox("Age group", ["Infant/child (<5)", "Child/teen (5-17)", "Adult (18-64)", "Older adult (65+)"], index=2)
        chronic = st.checkbox("I have a chronic condition (diabetes, heart, lung, kidney disease, etc.)")
        go = st.form_submit_button("Check")
    if go:
        if not syms:
            st.info("Select at least one symptom.")
        else:
            level, why = triage(syms, days, sev, age, chronic)
            msg = {"emergency": ("error", "Seek emergency care now (India: 112 / 108)."),
                   "doctor_soon": ("warning", "See a doctor within 24 hours."),
                   "doctor_visit": ("info", "Book a doctor visit in the next few days."),
                   "self_care": ("success", "Home care is likely reasonable. Monitor and seek care if you worsen.")}[level]
            getattr(st, msg[0])(msg[1])
            st.markdown("**Why:** " + "; ".join(why))
            st.caption("Triage guidance only, not a diagnosis.")

# ---------------------------------------------------------- appointments
with tab_appt:
    st.subheader("Book an appointment")
    with st.form("appt", clear_on_submit=True):
        name = st.text_input("Patient name")
        dept = st.selectbox("Department", DEPARTMENTS)
        d = st.date_input("Date", min_value=date.today(), value=date.today() + timedelta(days=1))
        booked = {(a["date"], a["time"], a["dept"]) for a in ss.appointments}
        free = [t for t in SLOTS if (d, t, dept) not in booked]
        slot = st.selectbox("Time slot", free, format_func=lambda t: t.strftime("%I:%M %p")) if free else None
        reason = st.text_input("Reason (optional)")
        ok = st.form_submit_button("Book")
    if ok:
        if not name.strip():
            st.error("Please enter the patient name.")
        elif d.weekday() == 6:
            st.error("Clinic is closed on Sundays. Choose another date.")
        elif slot is None:
            st.error("No free slots for that day.")
        else:
            ss.appointments.append({"id": uuid.uuid4().hex[:6].upper(), "name": name.strip(), "dept": dept,
                                    "date": d, "time": slot, "reason": reason})
            st.success("Appointment booked.")
    if ss.appointments:
        st.markdown("**Your appointments** (demo: stored for this session only)")
        for a in sorted(ss.appointments, key=lambda x: (x["date"], x["time"])):
            c1, c2 = st.columns([5, 1])
            c1.write(f"`{a['id']}` · {a['name']} · {a['dept']} · {a['date']:%d %b %Y} {a['time']:%I:%M %p}")
            if c2.button("Cancel", key="c" + a["id"]):
                ss.appointments.remove(a)
                st.rerun()

# ------------------------------------------------------------- reminders
with tab_rem:
    st.subheader("Medicine reminders")
    st.caption("Enter the medicine and timing exactly as your doctor prescribed. This app never suggests doses.")
    with st.form("rem", clear_on_submit=True):
        med = st.text_input("Medicine name")
        times = st.multiselect("Times of day", [time(h).strftime("%I:00 %p") for h in range(5, 24)])
        note = st.text_input("Note (e.g. after food)")
        add = st.form_submit_button("Add reminder")
    if add:
        if med.strip() and times:
            ss.reminders.append({"id": uuid.uuid4().hex[:6], "med": med.strip(), "times": times, "note": note})
        else:
            st.error("Enter a medicine name and at least one time.")
    for r in list(ss.reminders):
        c1, c2 = st.columns([5, 1])
        c1.write(f"💊 **{r['med']}** at {', '.join(r['times'])} {('· ' + r['note']) if r['note'] else ''}")
        if c2.button("Remove", key="r" + r["id"]):
            ss.reminders.remove(r)
            st.rerun()
    nxt = [(datetime.combine(date.today(), datetime.strptime(t, "%I:%M %p").time()), r["med"])
           for r in ss.reminders for t in r["times"]]
    upcoming = sorted(x for x in nxt if x[0] > datetime.now())[:1]
    if upcoming:
        st.info(f"Next today: {upcoming[0][1]} at {upcoming[0][0]:%I:%M %p}")
