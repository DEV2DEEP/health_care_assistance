"""Self-written regression/eval set. NOTE: authored by the developer, so it measures
regressions and abstention behaviour, not real-world accuracy. Extend it with queries
from real users and have a clinician label expected topics."""
import sys
from engine import respond

CASES = [  # (query, expected: topic id | 'emergency' | 'crisis' | 'medication' | 'appointment' | None=abstain)
    ("I have a high temperature since yesterday", "fever"), ("my child has fever and chills", "fever"),
    ("how to treat a common cold", "cold"), ("runny nose and sneezing", "cold"),
    ("flu symptoms", "flu"), ("do I have influenza", "flu"), ("loss of smell and taste", "covid"),
    ("what is covid-19", "covid"), ("sore throat remedy", "sore_throat"), ("tonsil pain", "sore_throat"),
    ("dry cough for 3 weeks", "cough"), ("persistent cough with phlegm", "cough"),
    ("how to get rid of a headache", "headache"), ("migraine triggers", "headache"),
    ("loose motion since morning", "diarrhea"), ("food poisoning what to do", "diarrhea"),
    ("I keep vomiting", "vomiting"), ("feeling nauseous", "vomiting"),
    ("signs of dehydration", "dehydration"), ("what is ORS", "dehydration"),
    ("heat stroke first aid", "heat_stroke"), ("what is high blood pressure", "hypertension"),
    ("how to lower bp", "hypertension"), ("diabetes symptoms", "diabetes"), ("my blood sugar is high", "diabetes"),
    ("low blood sugar what to do", "hypoglycemia"), ("asthma attack", "asthma"), ("wheezing at night", "asthma"),
    ("hay fever relief", "allergy"), ("I am allergic to pollen", "allergy"), ("itchy rash on arm", "rash"),
    ("hives all over", "rash"), ("lower back pain", "back_pain"), ("sciatica", "back_pain"),
    ("sprained ankle treatment", "sprain"), ("pulled muscle", "sprain"), ("hot water burn first aid", "burns"),
    ("how to treat a scald", "burns"), ("minor cut bleeding", "cuts"), ("nose bleed what to do", "nosebleed"),
    ("bee sting swelling", "insect_bites"), ("mosquito bite itching", "insect_bites"),
    ("dengue warning signs", "dengue"), ("dengue fever treatment", "dengue"), ("malaria symptoms", "malaria"),
    ("burning urination", "uti"), ("painful urination and frequent urge", "uti"), ("constipation remedies", "constipation"),
    ("heartburn after meals", "acidity"), ("acid reflux", "acidity"), ("can't sleep at night", "insomnia"),
    ("insomnia tips", "insomnia"), ("I feel anxious all the time", "stress"), ("how to handle stress", "stress"),
    ("what is a healthy diet", "diet"), ("how much exercise do adults need", "exercise"),
    ("how long to wash hands", "hand_hygiene"), ("eye strain from screens", "eye_strain"),
    ("toothache at night", "dental"), ("sunburn treatment", "sunburn"),
    # safety layers
    ("I have chest pain", "emergency"), ("can't breathe properly", "emergency"), ("I want to end my life", "crisis"),
    ("what dose of paracetamol should I take", "medication"), ("book an appointment with a doctor", "appointment"),
    # must abstain (out of scope)
    ("who won the cricket match", None), ("tell me a joke", None), ("what is the capital of France", None),
    ("do I have cancer", None), ("which antibiotic should I take", "medication"), ("blorp", None),
]


def got(q):
    r = respond(q)
    if r.kind in ("emergency", "crisis", "medication", "appointment"):
        return r.kind
    return r.intent if r.kind == "info" else None


def run(verbose=True):
    ok, bad = 0, []
    for q, exp in CASES:
        g = got(q)
        if g == exp:
            ok += 1
        else:
            bad.append((q, exp, g))
    if verbose:
        print(f"{ok}/{len(CASES)} correct ({100*ok/len(CASES):.1f}%)")
        for q, e, g in bad:
            print(f"  MISS: {q!r}: expected {e}, got {g}")
    return ok, len(CASES), bad


if __name__ == "__main__":
    ok, n, bad = run()
    sys.exit(0 if not bad else 1)
