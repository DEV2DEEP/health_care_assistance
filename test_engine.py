from engine import respond, triage

def test_emergency():
    assert respond("I have chest pain and can't breathe").kind == "emergency"
def test_crisis():
    assert respond("I want to die").kind == "crisis"
def test_dose_refused():
    r = respond("what dose of paracetamol should I take"); assert r.kind == "medication" and r.intent == "dose_refusal"
def test_symptom():
    r = respond("I have a fever and cough"); assert r.kind == "info" and "doctor" in r.text.lower()
def test_appointment():
    assert respond("I want to book an appointment").kind == "appointment"
def test_fallback():
    assert respond("blah blah").kind == "fallback"
def test_no_substring_false_positive():
    assert respond("this is a thin cover").kind == "fallback"
def test_triage():
    assert triage(["Chest pain"], 1, 3, "Adult (18-64)", False)[0] == "emergency"
    assert triage(["Fever", "Cough"], 5, 6, "Adult (18-64)", False)[0] == "doctor_visit"
    assert triage(["Cough"], 1, 2, "Adult (18-64)", False)[0] == "self_care"

def test_food_poisoning_not_emergency():
    assert respond("food poisoning what to do").intent == "diarrhea"
def test_burning_up_is_fever():
    assert respond("my kid is burning up").intent == "fever"
def test_abstains_out_of_scope():
    assert respond("who won the match").kind == "fallback"
def test_sources_present():
    r = respond("dengue warning signs"); assert r.sources and r.confidence in ("high", "ambiguous")
def test_eval_set_no_regression():
    from eval_accuracy import run
    assert not run(verbose=False)[2]
