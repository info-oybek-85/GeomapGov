from __future__ import annotations

from dataclasses import dataclass
from math import cos, exp, pi, radians, sqrt
from typing import Iterable

import numpy as np
from scipy.spatial import ConvexHull
from sklearn.cluster import DBSCAN

from .models import ComplaintAnalysis
from .services import haversine_km, minmax

EARTH_RADIUS_KM = 6371.0088
RISK_WEIGHTS = {
    "density": 0.28,
    "priority": 0.27,
    "severity": 0.18,
    "trend": 0.15,
    "spread": 0.12,
}


@dataclass
class ClusterSummary:
    label: int
    count: int
    center_lat: float
    center_lng: float
    density: float
    priority: float
    severity: float
    trend: float
    spread: float
    risk_index: float
    risk_level: str
    polygon: list[list[float]]


def _risk_level(value: float) -> str:
    if value >= 0.70:
        return "high"
    if value >= 0.40:
        return "medium"
    return "low"


def _weighted_kde(rows: list[ComplaintAnalysis], bandwidth_km: float) -> list[float]:
    """Priority-weighted Gaussian KDE evaluated at complaint locations."""
    if not rows:
        return []
    weights = np.asarray([max(float(r.priority_index), 0.01) for r in rows], dtype=float)
    denom = max(float(weights.sum()), 1e-9) * 2.0 * pi * bandwidth_km**2
    values: list[float] = []
    for i, row in enumerate(rows):
        total = 0.0
        for j, other in enumerate(rows):
            d = haversine_km(
                float(row.report.latitude), float(row.report.longitude),
                float(other.report.latitude), float(other.report.longitude),
            )
            total += weights[j] * exp(-(d * d) / (2.0 * bandwidth_km * bandwidth_km))
        values.append(total / denom)
    return minmax(values)


def _cluster_polygon(cluster_rows: list[ComplaintAnalysis]) -> list[list[float]]:
    pts = np.asarray([[float(r.report.longitude), float(r.report.latitude)] for r in cluster_rows])
    if len(pts) < 3:
        return [[float(r.report.latitude), float(r.report.longitude)] for r in cluster_rows]
    try:
        hull = ConvexHull(pts)
        return [[float(pts[i][1]), float(pts[i][0])] for i in hull.vertices]
    except Exception:
        return [[float(r.report.latitude), float(r.report.longitude)] for r in cluster_rows]


def _spread_area_proxy(cluster_rows: list[ComplaintAnalysis]) -> float:
    if len(cluster_rows) < 2:
        return 0.0
    lats = [float(r.report.latitude) for r in cluster_rows]
    lngs = [float(r.report.longitude) for r in cluster_rows]
    mean_lat = sum(lats) / len(lats)
    height = (max(lats) - min(lats)) * 111.32
    width = (max(lngs) - min(lngs)) * 111.32 * max(cos(radians(mean_lat)), 0.1)
    return max(0.0, height * width)


def analyze_risk(
    queryset: Iterable[ComplaintAnalysis],
    eps_km: float = 35.0,
    min_samples: int = 3,
    bandwidth_km: float = 45.0,
    eta: float = 0.70,
) -> tuple[list[ClusterSummary], int]:
    rows = list(queryset)
    if not rows:
        return [], 0

    coords_rad = np.radians(np.asarray([
        [float(r.report.latitude), float(r.report.longitude)] for r in rows
    ]))
    labels = DBSCAN(
        eps=eps_km / EARTH_RADIUS_KM,
        min_samples=min_samples,
        metric="haversine",
        algorithm="ball_tree",
    ).fit_predict(coords_rad)

    kde_values = _weighted_kde(rows, max(bandwidth_km, 0.1))
    for row, label, kde in zip(rows, labels, kde_values):
        row.cluster_label = int(label)
        row.weighted_kde = float(kde)

    cluster_labels = sorted({int(x) for x in labels if int(x) >= 0})
    raw_density: list[float] = []
    raw_priority: list[float] = []
    raw_severity: list[float] = []
    raw_trend: list[float] = []
    raw_spread: list[float] = []
    grouped: list[list[ComplaintAnalysis]] = []

    for label in cluster_labels:
        members = [r for r in rows if r.cluster_label == label]
        grouped.append(members)
        raw_density.append(sum(float(r.weighted_kde) for r in members) / len(members))
        avg_p = sum(float(r.priority_index) for r in members) / len(members)
        max_p = max(float(r.priority_index) for r in members)
        raw_priority.append(eta * avg_p + (1.0 - eta) * max_p)
        p_sum = sum(max(float(r.priority_index), 0.001) for r in members)
        raw_severity.append(sum(float(r.priority_index) * float(r.severity_weight) for r in members) / p_sum)

        dates = sorted(r.report.created_at for r in members if r.report.created_at)
        if dates:
            midpoint = dates[0] + (dates[-1] - dates[0]) / 2
            previous = sum(1 for d in dates if d < midpoint)
            current = sum(1 for d in dates if d >= midpoint)
            growth = (current - previous) / max(previous, 1)
            raw_trend.append(1.0 / (1.0 + exp(-growth)))
        else:
            raw_trend.append(0.5)
        raw_spread.append(_spread_area_proxy(members))

    density_n = minmax(raw_density)
    priority_n = minmax(raw_priority)
    severity_n = minmax(raw_severity)
    trend_n = minmax(raw_trend)
    spread_n = minmax(raw_spread)

    summaries: list[ClusterSummary] = []
    for idx, members in enumerate(grouped):
        risk = (
            RISK_WEIGHTS["density"] * density_n[idx]
            + RISK_WEIGHTS["priority"] * priority_n[idx]
            + RISK_WEIGHTS["severity"] * severity_n[idx]
            + RISK_WEIGHTS["trend"] * trend_n[idx]
            + RISK_WEIGHTS["spread"] * spread_n[idx]
        )
        risk = max(0.0, min(1.0, float(risk)))
        level = _risk_level(risk)
        center_lat = sum(float(r.report.latitude) for r in members) / len(members)
        center_lng = sum(float(r.report.longitude) for r in members) / len(members)
        summary = ClusterSummary(
            label=cluster_labels[idx], count=len(members), center_lat=center_lat, center_lng=center_lng,
            density=density_n[idx], priority=priority_n[idx], severity=severity_n[idx],
            trend=trend_n[idx], spread=spread_n[idx], risk_index=risk, risk_level=level,
            polygon=_cluster_polygon(members),
        )
        summaries.append(summary)
        for row in members:
            row.risk_index = risk
            row.risk_level = level
            row.algorithm_version = "geoai-risk-4.0"

    noise_count = 0
    for row in rows:
        if row.cluster_label == -1:
            noise_count += 1
            row.risk_index = 0.0
            row.risk_level = "noise"
            row.algorithm_version = "geoai-risk-4.0"
        row.save(update_fields=[
            "cluster_label", "weighted_kde", "risk_index", "risk_level",
            "algorithm_version", "calculated_at",
        ])

    summaries.sort(key=lambda x: x.risk_index, reverse=True)
    return summaries, noise_count
