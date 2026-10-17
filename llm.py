"""Optional grounded generation. The model may ONLY rephrase the retrieved KB passages.
Disabled unless ANTHROPIC_API_KEY is set. Safety layers (emergency/crisis/dose) never reach this."""
import os

MODEL = os.environ.get("HEALTH_LLM_MODEL", "claude-sonnet-5-5")
SYSTEM = (
    "You are a health information assistant. Answer ONLY using the SOURCE PASSAGES provided. "
    "If the passages do not contain the answer, reply exactly: I don't have reliable information on that. "
    "Never diagnose, never give medicine doses or recommend specific medicines, never add facts that are not in the passages. "
    "Keep it under 150 words, plain language, and end by advising to consult a doctor for personal advice."
)


def available():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def grounded_answer(question, topics):
    """Return rephrased answer grounded in `topics` (KB dicts), or None on any failure."""
    if not available() or not topics:
        return None
    try:
        import anthropic
        passages = "\n\n".join(
            f"[{t['title']} | sources: {', '.join(t['sources'])}]\n{t['about']} {t['self_care']} Seek care: {t['seek_care']}" for t in topics)
        msg = anthropic.Anthropic().messages.create(
            model=MODEL, max_tokens=400, temperature=0, system=SYSTEM,
            messages=[{"role": "user", "content": f"SOURCE PASSAGES:\n{passages}\n\nQUESTION: {question}"}])
        return msg.content[0].text.strip()
    except Exception:
        return None
