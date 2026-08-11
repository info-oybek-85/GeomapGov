from __future__ import annotations

import json
import math
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Iterable

from django.conf import settings
from reports.ai_service import load_model

from .models import Organization


_APOSTROPHE_RE = re.compile(r"[ʻʼ’`´]")
_NON_WORD_RE = re.compile(r"[^a-z0-9а-яёқғҳў\s]+", re.IGNORECASE)
_SPACE_RE = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    text = _APOSTROPHE_RE.sub("'", (value or "").lower())
    text = _NON_WORD_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", text).strip()


@dataclass(frozen=True)
class Profile:
    organization_name_tokens: tuple[str, ...]
    keywords: dict[str, float]
    model_categories: dict[str, float]


PROFILES: tuple[Profile, ...] = (
    Profile(
        organization_name_tokens=("energetika", "elektr"),
        keywords={
            "svet yo'q": 6.0, "svet yoq": 6.0, "chiroq yo'q": 5.5,
            "elektr yo'q": 6.0, "tok yo'q": 6.0, "tok o'chdi": 5.5,
            "transformator": 5.0, "elektr sim": 5.0, "sim uzildi": 5.0,
            "sim yerga tushdi": 6.0, "elektr ustun": 4.0, "podstansiya": 5.0,
            "kuchlanish": 4.0, "hisoblagich": 3.0, "elektr energiya": 5.0,
            "svetofor": 1.0,
        },
        model_categories={"electricity": 5.0, "energy": 5.0},
    ),
    Profile(
        organization_name_tokens=("ekologiya", "atrof muhit", "obodonlashtirish"),
        keywords={
            "chiqindi": 5.0, "axlat": 5.0, "musor": 5.0, "tozalanmayapti": 4.0,
            "daraxt qulab": 5.0, "daraxt kes": 4.0, "havo iflos": 5.0,
            "tutun": 4.0, "badbo'y": 4.0, "kanal iflos": 4.0,
            "obodonlashtirish": 5.0, "ekologiya": 5.0, "yashil hudud": 4.0,
            "noqonuniy chiqindi": 6.0,
        },
        model_categories={"waste": 5.0, "ecology": 5.0},
    ),
    Profile(
        organization_name_tokens=("transport",),
        keywords={
            "yo'l chuqur": 6.0, "yo'l buzilgan": 5.0, "asfalt": 4.0,
            "avtobus": 4.0, "bekat": 4.0, "transport": 4.0,
            "svetofor": 5.0, "tirbandlik": 5.0, "yo'l belgisi": 4.0,
            "piyodalar yo'lagi": 4.0, "ko'prik": 4.0,
        },
        model_categories={"road": 5.0, "traffic": 5.0},
    ),
    Profile(
        organization_name_tokens=("suv xo'jaligi", "suv"),
        keywords={
            "suv yo'q": 6.0, "ichimlik suv": 5.0, "quvur yorildi": 5.0,
            "suv oqyapti": 4.0, "kanalizatsiya": 4.0, "ariq": 3.0,
            "suv bosdi": 4.0, "suv ta'minoti": 5.0,
        },
        model_categories={"water": 5.0},
    ),
    Profile(
        organization_name_tokens=("sog'liqni saqlash",),
        keywords={
            "shifoxona": 4.0, "poliklinika": 4.0, "tez yordam": 5.0,
            "dori": 3.0, "doktor": 3.0, "tibbiyot": 4.0, "kasalxona": 4.0,
        },
        model_categories={"health": 5.0},
    ),
    Profile(
        organization_name_tokens=("maktabgacha", "maktab ta'limi"),
        keywords={
            "maktab": 4.0, "bog'cha": 4.0, "o'qituvchi": 3.0,
            "darslik": 3.0, "maktabgacha": 4.0, "o'quvchi": 3.0,
        },
        model_categories={"education": 5.0},
    ),
    Profile(
        organization_name_tokens=("oliy ta'lim",),
        keywords={
            "universitet": 4.0, "institut": 4.0, "talaba": 3.0,
            "kontrakt": 3.0, "yotoqxona": 3.0, "oliy ta'lim": 5.0,
        },
        model_categories={"higher_education": 5.0},
    ),
    Profile(
        organization_name_tokens=("ichki ishlar",),
        keywords={
            "o'g'irlik": 5.0, "bezorilik": 4.0, "jinoyat": 5.0,
            "yo'l patrul": 4.0, "profilaktika inspektori": 4.0,
            "ichki ishlar": 5.0, "politsiya": 4.0,
        },
        model_categories={"police": 5.0},
    ),
    Profile(
        organization_name_tokens=("favqulodda vaziyat",),
        keywords={
            "yong'in": 6.0, "portlash": 6.0, "gaz sizib": 5.0,
            "bino qulash": 5.0, "suv toshqin": 5.0, "favqulodda": 5.0,
        },
        model_categories={"emergency": 5.0},
    ),
    Profile(
        organization_name_tokens=("raqamli texnologiyalar",),
        keywords={
            "internet": 5.0, "aloqa": 4.0, "mobil tarmoq": 4.0,
            "telefon tarmog'i": 4.0, "raqamli xizmat": 4.0,
        },
        model_categories={"telecom": 5.0, "digital": 5.0},
    ),
)


def _model_prediction(text: str) -> tuple[str, float]:
    try:
        model = load_model()
        label = str(model.predict([text])[0])
        confidence = 0.0
        if hasattr(model, "predict_proba"):
            probabilities = model.predict_proba([text])[0]
            confidence = float(max(probabilities))
        return label.lower(), confidence
    except Exception:
        return "other", 0.0


def _profile_for_org(name: str) -> Profile | None:
    normalized_name = normalize_text(name)
    for profile in PROFILES:
        if any(normalize_text(token) in normalized_name for token in profile.organization_name_tokens):
            return profile
    return None



_DIRECT_MODEL_CACHE = {"mtime": None, "model": None, "meta": None}


def _direct_model_paths() -> tuple[Path, Path]:
    model_path = Path(settings.BASE_DIR) / "ml" / "organization_classifier.pkl"
    meta_path = Path(settings.BASE_DIR) / "ml" / "organization_classifier_meta.json"
    return model_path, meta_path


def _load_direct_model():
    """Feedback asosida o'qitilgan bevosita text -> organization modelini yuklaydi."""
    model_path, meta_path = _direct_model_paths()
    if not model_path.exists():
        return None, None

    mtime = model_path.stat().st_mtime
    if _DIRECT_MODEL_CACHE["model"] is not None and _DIRECT_MODEL_CACHE["mtime"] == mtime:
        return _DIRECT_MODEL_CACHE["model"], _DIRECT_MODEL_CACHE["meta"]

    try:
        import joblib
        model = joblib.load(model_path)
        meta = {}
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        _DIRECT_MODEL_CACHE.update({"mtime": mtime, "model": model, "meta": meta})
        return model, meta
    except Exception:
        return None, None


def _predict_with_direct_model(text: str, organizations: Iterable[Organization]) -> dict | None:
    model, meta = _load_direct_model()
    if model is None or not hasattr(model, "predict_proba"):
        return None

    org_by_id = {str(org.id): org for org in organizations}
    try:
        probabilities = model.predict_proba([text])[0]
        classes = [str(value) for value in model.classes_]
    except Exception:
        return None

    ranked = sorted(zip(classes, probabilities), key=lambda item: float(item[1]), reverse=True)
    recommendations = []
    for org_id, probability in ranked:
        organization = org_by_id.get(org_id)
        if not organization:
            continue
        recommendations.append({
            "id": str(organization.id),
            "name": organization.name,
            "confidence": round(float(probability), 4),
            "matched_keywords": [],
            "explanations": ["Tasdiqlangan murojaatlar asosida o‘qitilgan ML modeli"],
        })
        if len(recommendations) == 3:
            break

    if not recommendations:
        return None

    top = recommendations[0]
    return {
        "organization": {"id": top["id"], "name": top["name"]},
        "recommendations": recommendations,
        "confidence": top["confidence"],
        "category": "organization_ml",
        "category_confidence": top["confidence"],
        "matched_keywords": [],
        "explanations": top["explanations"],
        "method": "feedback_tfidf_logistic_regression",
        "model_meta": meta or {},
    }


def predict_organization(text: str, organizations: Iterable[Organization] | None = None) -> dict:
    normalized = normalize_text(text)
    if len(normalized) < 3:
        return {
            "organization": None,
            "recommendations": [],
            "confidence": 0.0,
            "category": "other",
            "matched_keywords": [],
            "explanations": [],
            "method": "hybrid_ml_rules",
        }

    organizations = list(organizations or Organization.objects.filter(is_active=True).order_by("name"))

    direct_result = _predict_with_direct_model(text, organizations)
    if direct_result and direct_result.get("confidence", 0.0) >= 0.45:
        return direct_result

    category, category_confidence = _model_prediction(text)

    scored: list[tuple[float, Organization, list[str]]] = []
    for organization in organizations:
        if normalize_text(organization.name) == "bilmayman":
            continue
        profile = _profile_for_org(organization.name)
        if not profile:
            continue

        score = 0.0
        matched: list[str] = []
        for phrase, weight in profile.keywords.items():
            if normalize_text(phrase) in normalized:
                score += weight
                matched.append(phrase)

        category_weight = profile.model_categories.get(category, 0.0)
        if category_weight:
            score += category_weight * max(category_confidence, 0.35)

        if score > 0:
            scored.append((score, organization, matched))

    if not scored:
        return {
            "organization": None,
            "recommendations": [],
            "confidence": round(category_confidence * 0.25, 4),
            "category": category,
            "category_confidence": round(category_confidence, 4),
            "matched_keywords": [],
            "explanations": [],
            "method": "hybrid_ml_rules",
        }

    scored.sort(key=lambda item: item[0], reverse=True)
    top_score = scored[0][0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0

    strength = 1.0 - math.exp(-top_score / 6.0)
    margin = (top_score - second_score) / max(top_score, 1.0)
    top_confidence = min(0.99, max(0.0, 0.58 * strength + 0.42 * margin))

    recommendations = []
    for index, (score, organization, matched) in enumerate(scored[:3]):
        if index == 0:
            confidence = top_confidence
        else:
            ratio = score / max(top_score, 1.0)
            confidence = min(top_confidence * 0.92, max(0.05, top_confidence * ratio * 0.78))
        explanations = []
        if matched:
            explanations.append("Matnda mos iboralar topildi: " + ", ".join(matched[:5]))
        if category and category != "other":
            explanations.append(f"ML kategoriya: {category}")
        recommendations.append({
            "id": str(organization.id),
            "name": organization.name,
            "confidence": round(confidence, 4),
            "matched_keywords": matched[:8],
            "explanations": explanations,
        })

    top = recommendations[0]
    return {
        "organization": {"id": top["id"], "name": top["name"]},
        "recommendations": recommendations,
        "confidence": top["confidence"],
        "category": category,
        "category_confidence": round(category_confidence, 4),
        "matched_keywords": top["matched_keywords"],
        "explanations": top["explanations"],
        "method": "hybrid_ml_rules",
    }
