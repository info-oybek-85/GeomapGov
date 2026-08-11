from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

NORMALIZATION = {
    "setafor": "svetofor",
    "seftafor": "svetofor",
    "sitafor": "svetofor",
    "svitafor": "svetofor",
    "sevet": "svet",
    "musor": "chiqindi",
    "musir": "chiqindi",
    "yol": "yo'l",
    "yollar": "yo'llar",
    "kemayapti": "kelmayapti",
    "xisoblagich": "hisoblagich",
    "svet yoq": "svet yo'q",
    "gaz yoq": "gaz yo'q",
    "gaz you": "gaz yo'q",
}

PROBLEM_LEXICON = {
    "electricity": ["svet", "tok", "elektr", "transformator", "kuchlanish", "sim", "elektr ustun", "fonar", "yoritish", "chiroq"],
    "ecology": ["chiqindi", "axlat", "daraxt", "tutun", "iflos", "havo", "ariq", "oqova", "ekologiya", "ko'kalamzor"],
    "road": ["yo'l", "asfalt", "chuqur", "ko'prik", "yo'l buzilgan", "yama", "yo'l to'silgan"],
    "traffic": ["svetofor", "chorraha", "yo'l belgisi", "harakat", "tirband", "piyodalar o'tish"],
    "water": ["suv", "kanalizatsiya", "quvur", "oqova", "bosim", "suv yo'q"],
    "gas": ["gaz", "gaz yo'q", "gaz bosimi", "gaz quvur", "gaz siz"],
    "housing": ["uy-joy", "lift", "pod'ezd", "tom", "kommunal", "ko'p qavatli"],
}

ORG_BY_PROBLEM = {
    "electricity": "Hududiy elektr tarmoqlari",
    "ecology": "Ekologiya va obodonlashtirish",
    "road": "Yo'l boshqarmasi",
    "traffic": "Transport / Yo'l harakati xavfsizligi",
    "water": "Suv ta'minoti",
    "gas": "Gaz ta'minoti",
    "housing": "Uy-joy kommunal xizmatlari",
}

CONTEXT_HINTS = {
    "maktab": {"traffic": 0.08, "road": 0.05, "electricity": 0.05},
    "shifoxona": {"electricity": 0.06, "road": 0.04},
    "chorraha": {"traffic": 0.12},
    "mahalla": {"ecology": 0.03, "road": 0.03},
    "ko'cha": {"road": 0.04, "traffic": 0.03, "ecology": 0.02},
}

@dataclass
class GSORResult:
    organization: str
    problem: str
    score: float
    semantic: float
    context: float
    geo: float
    history: float
    matched_terms: List[str]

def normalize_text(text: str) -> str:
    s = (text or "").lower().strip()
    s = s.replace("ʻ", "'").replace("’", "'").replace("`", "'")
    s = re.sub(r"\s+", " ", s)
    for src, dst in sorted(NORMALIZATION.items(), key=lambda x: -len(x[0])):
        s = re.sub(rf"\b{re.escape(src)}\b", dst, s)
    return s

def _term_score(text: str, terms: Sequence[str]) -> Tuple[float, List[str]]:
    matched = []
    score = 0.0
    for term in terms:
        if term in text:
            matched.append(term)
            score += 1.0 + min(len(term) / 30.0, 0.5)
    return (1.0 - math.exp(-score / 2.2) if terms else 0.0), matched

def _context_score(text: str, problem: str) -> float:
    value = 0.0
    for hint, mapping in CONTEXT_HINTS.items():
        if hint in text:
            value += float(mapping.get(problem, 0.0))
    return min(value, 1.0)

def rank_organizations(text: str, geo_scores: Dict[str, float] | None = None,
                       history_scores: Dict[str, float] | None = None,
                       weights: Dict[str, float] | None = None, top_k: int = 3) -> List[GSORResult]:
    weights = weights or {"semantic": 0.55, "context": 0.15, "geo": 0.15, "history": 0.15}
    geo_scores = geo_scores or {}
    history_scores = history_scores or {}
    nt = normalize_text(text)
    results = []
    for problem, terms in PROBLEM_LEXICON.items():
        org = ORG_BY_PROBLEM[problem]
        sem, matched = _term_score(nt, terms)
        ctx = _context_score(nt, problem)
        geo = float(geo_scores.get(problem, geo_scores.get(org, 0.0)) or 0.0)
        hist = float(history_scores.get(problem, history_scores.get(org, 0.0)) or 0.0)
        score = (weights["semantic"]*sem + weights["context"]*ctx +
                 weights["geo"]*geo + weights["history"]*hist)
        results.append(GSORResult(org, problem, round(score,6), round(sem,6),
                                  round(ctx,6), round(geo,6), round(hist,6), matched))
    results.sort(key=lambda x: x.score, reverse=True)
    return results[:max(1, int(top_k))]

def routing_decision(results: Sequence[GSORResult]) -> str:
    if not results:
        return "expert_review"
    top = results[0].score
    if top >= 0.80:
        return "auto_recommend"
    if top >= 0.50:
        return "expert_review"
    return "citizen_clarification"
