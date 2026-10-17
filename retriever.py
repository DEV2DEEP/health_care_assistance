"""Transparent retrieval over the curated KB: keyword evidence first, BM25 as tie-breaker.
Abstains instead of guessing when there is no keyword evidence."""
import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import List

from kb import TOPICS

STOP = set("a an the is are am i my me you your do does did of to in on for with and or it its be have has had can could should would what how why when "
           "about from this that there any some very been being get got feel feeling please tell want need if at as by so than then".split())
SECTION_HINTS = {
    "seek_care": r"\b(when|should i) (to )?(see|visit|call|go|worry|seek)|red flag|warning sign|serious|danger|emergency|hospital|doctor",
    "self_care": r"\b(treat|treatment|remed|cure|manage|relief|relieve|what to do|how to (stop|ease|reduce|lower|get rid)|home care|self[- ]care|help)",
    "about": r"\b(what is|what are|causes?|why|symptoms?|signs?|meaning)\b",
    "prevention": r"\b(prevent|avoid|protect|reduce (the )?risk)",
}


def stem(w):
    for suf in ("ing", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def toks(text, keep_stop=False):
    ws = re.findall(r"[a-z0-9]+", text.lower().replace("'", ""))
    return [stem(w) for w in ws if keep_stop or w not in STOP]


# index
_KW = {}   # topic id -> list of (phrase_token_set)
_DF = Counter()
for t in TOPICS:
    phrases = [frozenset(toks(k, True)) for k in t["keywords"]] + [frozenset(toks(t["title"]))]
    _KW[t["id"]] = [p for p in phrases if p]
    for tok in set().union(*_KW[t["id"]]):
        _DF[tok] += 1
_N = len(TOPICS)
_DOCS = {t["id"]: toks(" ".join([t["title"], t["about"], t["self_care"], t["seek_care"]])) for t in TOPICS}
_AVG = sum(map(len, _DOCS.values())) / _N
_BDF = Counter(tok for d in _DOCS.values() for tok in set(d))


def _idf(tok):
    return math.log(1 + _N / (1 + _DF.get(tok, 0)))


def _bm25(q, doc, k1=1.4, b=0.75):
    tf = Counter(doc)
    s = 0.0
    for w in set(q):
        if w in tf:
            idf = math.log(1 + (_N - _BDF[w] + 0.5) / (_BDF[w] + 0.5))
            s += idf * tf[w] * (k1 + 1) / (tf[w] + k1 * (1 - b + b * len(doc) / _AVG))
    return s


@dataclass
class Hit:
    topic: dict
    kscore: float
    bm25: float
    matched: List[str]


def section_for(query):
    q = query.lower()
    for sec, rx in SECTION_HINTS.items():
        if re.search(rx, q):
            return sec
    return None


def retrieve(query, k=3) -> List[Hit]:
    query = re.sub(r"\bburning up\b", "burning up fever", query.lower())
    # "burning up" means fever, not a burn injury
    if "burning up" in query:
        query = query.replace("burning", "")
    qt = set(toks(query, True))
    qd = [w for w in toks(query)]
    hits = []
    for t in TOPICS:
        ks, matched = 0.0, []
        for ph in _KW[t["id"]]:
            if ph <= qt:
                ks += sum(_idf(x) for x in ph)
                matched.append(" ".join(sorted(ph)))
        if ks > 0:
            hits.append(Hit(t, ks, _bm25(qd, _DOCS[t["id"]]), matched))
    hits.sort(key=lambda h: (h.kscore, h.bm25), reverse=True)
    return hits[:k]


def confidence(hits):
    if not hits:
        return "none"
    top = hits[0]
    if len(hits) == 1 or top.kscore >= 1.35 * hits[1].kscore:
        return "high"
    return "ambiguous"
