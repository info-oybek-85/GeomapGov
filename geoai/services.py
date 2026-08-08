from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from math import asin, cos, exp, log, radians, sin, sqrt
from typing import Iterable
from pathlib import Path

import joblib
import pandas as pd
from scipy.sparse import csr_matrix, hstack

from django.utils import timezone

from reports.ai_service import load_model

FUSION_MODEL_PATH = Path(__file__).resolve().parent.parent / "ml" / "geoai_fusion_model.pkl"
_fusion_bundle = None


CATEGORY_SEVERITY = {
    "emergency": 1.00,
    "traffic": 0.95,
    "electricity": 0.90,
    "gas": 0.85,
    "water": 0.80,
    "road": 0.75,
    "sewerage": 0.65,
    "waste": 0.60,
    "ecology": 0.55,
    "utility": 0.50,
    "other": 0.40,
}

PRIORITY_WEIGHTS = {
    "density": 0.22,
    "frequency": 0.18,
    "recency": 0.18,
    "severity": 0.20,
    "confidence": 0.12,
    "neighbor": 0.10,
}


@dataclass(frozen=True)
class ReportPoint:
    report_id: object
    text: str
    lat: float
    lon: float
    created_at: datetime
    stored_category: str | None = None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    p1, p2 = radians(lat1), radians(lat2)
    dp = radians(lat2 - lat1)
    dl = radians(lon2 - lon1)
    a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * radius * asin(min(1.0, sqrt(a)))


def _load_fusion_bundle():
    global _fusion_bundle
    if _fusion_bundle is None and FUSION_MODEL_PATH.exists():
        _fusion_bundle = joblib.load(FUSION_MODEL_PATH)
    return _fusion_bundle


def _fusion_dense_row(point: ReportPoint) -> list[float]:
    ts = pd.to_datetime(point.created_at)
    month = float(ts.month)
    dow = float(ts.dayofweek)
    day = float(ts.day)
    from math import pi
    return [
        float(point.lat), float(point.lon),
        sin(2 * pi * month / 12.0), cos(2 * pi * month / 12.0),
        sin(2 * pi * dow / 7.0), cos(2 * pi * dow / 7.0),
        day / 31.0,
    ]


def classify_with_confidence(point: ReportPoint) -> tuple[str, float]:
    text = (point.text or "").strip()
    if not text:
        return "other", 0.0

    bundle = _load_fusion_bundle()
    if bundle:
        vectorizer = bundle["vectorizer"]
        scaler = bundle["scaler"]
        classifier = bundle["classifier"]
        x_text = vectorizer.transform([text])
        x_dense = scaler.transform([_fusion_dense_row(point)])
        x = hstack([x_text, csr_matrix(x_dense)], format="csr")
        category = str(classifier.predict(x)[0])
        probabilities = classifier.predict_proba(x)[0]
        confidence = float(max(probabilities))
        return category, max(0.0, min(1.0, confidence))

    # Backward-compatible text-only fallback.
    model = load_model()
    category = str(model.predict([text])[0])
    confidence = 1.0
    if hasattr(model, "predict_proba"):
        confidence = float(max(model.predict_proba([text])[0]))
    return category, max(0.0, min(1.0, confidence))


def temporal_relevance(created_at: datetime | date, now: datetime | None = None, half_life_days: float = 7.0) -> float:
    now = now or timezone.now()
    if isinstance(created_at, date) and not isinstance(created_at, datetime):
        created_at = datetime.combine(created_at, time.min)
    if timezone.is_naive(created_at):
        created_at = timezone.make_aware(created_at, timezone.get_current_timezone())
    age_days = max(0.0, (now - created_at).total_seconds() / 86400.0)
    decay = log(2.0) / max(half_life_days, 0.001)
    return float(exp(-decay * age_days))


def minmax(values: list[float]) -> list[float]:
    if not values:
        return []
    low, high = min(values), max(values)
    if high == low:
        return [1.0 if high > 0 else 0.0 for _ in values]
    return [(v - low) / (high - low) for v in values]


def priority_level(value: float) -> str:
    if value >= 0.70:
        return "high"
    if value >= 0.40:
        return "medium"
    return "low"


def analyze_points(points: Iterable[ReportPoint], radius_km: float = 0.5, frequency_days: int = 30) -> list[dict]:
    """2-ilmiy yangilikning ishlaydigan hisoblash yadrosi.

    rho_i: radius ichidagi mahalliy zichlik;
    f_i: shu kategoriya va vaqt oynasidagi takrorlanish;
    q_i: eksponensial vaqt dolzarbligi;
    s_i = W(C_i);
    Conf_i: klassifikator ehtimoli;
    n_i: yaqin qo‘shnilarning dastlabki ta'siri.
    """
    pts = list(points)
    now = timezone.now()
    classified: list[dict] = []
    for p in pts:
        category, confidence = classify_with_confidence(p)
        classified.append({
            "point": p,
            "category": category,
            "confidence": confidence,
            "recency": temporal_relevance(p.created_at, now),
            "severity": CATEGORY_SEVERITY.get(category.lower(), CATEGORY_SEVERITY["other"]),
        })

    raw_density: list[float] = []
    raw_frequency: list[float] = []
    raw_neighbor: list[float] = []
    frequency_seconds = frequency_days * 86400

    for i, item in enumerate(classified):
        p = item["point"]
        density = 0
        frequency = 0
        neighbor_sum = 0.0
        neighbor_weights = 0.0
        for j, other in enumerate(classified):
            if i == j:
                continue
            q = other["point"]
            distance = haversine_km(p.lat, p.lon, q.lat, q.lon)
            if distance <= radius_km:
                density += 1
                if (
                    other["category"] == item["category"]
                    and abs((p.created_at - q.created_at).total_seconds()) <= frequency_seconds
                ):
                    frequency += 1
                spatial_weight = 1.0 / max(distance, 0.05)
                proxy = 0.55 * other["severity"] + 0.45 * other["recency"]
                neighbor_sum += spatial_weight * proxy
                neighbor_weights += spatial_weight
        raw_density.append(float(density))
        raw_frequency.append(float(frequency))
        raw_neighbor.append(neighbor_sum / neighbor_weights if neighbor_weights else 0.0)

    density_norm = minmax(raw_density)
    frequency_norm = minmax(raw_frequency)
    neighbor_norm = minmax(raw_neighbor)

    results: list[dict] = []
    for idx, item in enumerate(classified):
        priority = (
            PRIORITY_WEIGHTS["density"] * density_norm[idx]
            + PRIORITY_WEIGHTS["frequency"] * frequency_norm[idx]
            + PRIORITY_WEIGHTS["recency"] * item["recency"]
            + PRIORITY_WEIGHTS["severity"] * item["severity"]
            + PRIORITY_WEIGHTS["confidence"] * item["confidence"]
            + PRIORITY_WEIGHTS["neighbor"] * neighbor_norm[idx]
        )
        priority = max(0.0, min(1.0, float(priority)))
        results.append({
            "report_id": item["point"].report_id,
            "category": item["category"],
            "confidence": item["confidence"],
            "density": density_norm[idx],
            "frequency": frequency_norm[idx],
            "recency": item["recency"],
            "severity": item["severity"],
            "neighbor": neighbor_norm[idx],
            "priority": priority,
            "priority_level": priority_level(priority),
        })
    return results
