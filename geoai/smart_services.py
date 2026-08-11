from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from typing import Iterable

from django.utils import timezone

from .models import ComplaintAnalysis


@dataclass
class SmartRecommendation:
    rank: int
    cluster: str
    risk_index: float
    risk_level: str
    complaint_count: int
    dominant_category: str
    responsible_organization: str
    action: str
    response_hours: int
    resource_share: float
    rationale: str

    def to_dict(self) -> dict:
        return asdict(self)


def _action_for(risk_level: str, category: str, count: int) -> tuple[str, int]:
    cat = (category or "").lower()
    if risk_level == "high":
        if any(x in cat for x in ("traffic", "road", "electric", "gas")):
            return "Tezkor brigadani yuborish, hududni tekshirish va xavfsizlik choralarini ko‘rish", 2
        return "Favqulodda ko‘rib chiqish va mas’ul tashkilotga zudlik bilan topshiriq berish", 4
    if risk_level == "medium":
        return "Rejali tekshiruv o‘tkazish, ijro muddatini belgilash va monitoringga olish", 24
    if count >= 5:
        return "Profilaktik monitoring va takrorlanish sabablarini tahlil qilish", 72
    return "Kuzatuvda saqlash va navbatdagi reja asosida ko‘rib chiqish", 120


def _as_aware_datetime(value: date | datetime | None) -> datetime | None:
    """DateField va DateTimeField qiymatlarini yagona aware datetime ga keltiradi.

    Loyiha BaseModel.created_at uchun DateField ishlatadi. Ushbu yordamchi funksiya
    keyinchalik DateTimeField ga o'tilganda ham kodning ishlashini saqlab qoladi.
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        result = value
    elif isinstance(value, date):
        result = datetime.combine(value, time.min)
    else:
        return None

    if timezone.is_naive(result):
        result = timezone.make_aware(result, timezone.get_current_timezone())
    return result


def _is_recent(value: date | datetime | None, *, now: datetime, seconds: int) -> bool:
    created = _as_aware_datetime(value)
    if created is None:
        return False
    delta = now - created
    # Kelajak sanalarini tasodifan "so'nggi 24 soat" deb hisoblamaymiz.
    return timedelta(0) <= delta <= timedelta(seconds=seconds)


def build_smart_dashboard(queryset: Iterable[ComplaintAnalysis]) -> dict:
    rows = list(queryset)
    cluster_rows: dict[int, list[ComplaintAnalysis]] = defaultdict(list)
    for row in rows:
        if row.cluster_label is not None and row.cluster_label >= 0:
            cluster_rows[int(row.cluster_label)].append(row)

    raw: list[dict] = []
    for label, members in cluster_rows.items():
        risk_index = max((float(x.risk_index or 0.0) for x in members), default=0.0)
        risk_level = max(
            (x.risk_level or "low" for x in members),
            key=lambda value: {"high": 3, "medium": 2, "low": 1}.get(value, 0),
        )
        categories = defaultdict(int)
        organizations = defaultdict(int)
        avg_priority = 0.0
        for item in members:
            categories[item.predicted_category or "other"] += 1
            org = item.report.organization.name if item.report.organization else "Biriktirilmagan"
            organizations[org] += 1
            avg_priority += float(item.priority_index or 0.0)
        dominant_category = max(categories, key=categories.get) if categories else "other"
        organization = max(organizations, key=organizations.get) if organizations else "Biriktirilmagan"
        action, response_hours = _action_for(risk_level, dominant_category, len(members))
        raw.append({
            "cluster": f"K{label}",
            "risk_index": risk_index,
            "risk_level": risk_level,
            "complaint_count": len(members),
            "dominant_category": dominant_category,
            "responsible_organization": organization,
            "action": action,
            "response_hours": response_hours,
            "avg_priority": avg_priority / max(len(members), 1),
        })

    raw.sort(key=lambda x: (x["risk_index"], x["complaint_count"]), reverse=True)
    total_risk = sum(max(x["risk_index"], 0.01) for x in raw) or 1.0
    recommendations: list[dict] = []
    for rank, item in enumerate(raw, start=1):
        resource_share = max(item["risk_index"], 0.01) / total_risk
        rationale = (
            f"{item['complaint_count']} ta murojaat, o‘rtacha Pᵢ={item['avg_priority']:.3f}, "
            f"Hₖ={item['risk_index']:.3f}; ustun kategoriya — {item['dominant_category']}."
        )
        recommendations.append(SmartRecommendation(
            rank=rank,
            cluster=item["cluster"],
            risk_index=round(item["risk_index"], 4),
            risk_level=item["risk_level"],
            complaint_count=item["complaint_count"],
            dominant_category=item["dominant_category"],
            responsible_organization=item["responsible_organization"],
            action=item["action"],
            response_hours=item["response_hours"],
            resource_share=round(resource_share, 4),
            rationale=rationale,
        ).to_dict())

    now = timezone.now()
    last_24h = sum(
        1 for x in rows
        if _is_recent(getattr(x.report, "created_at", None), now=now, seconds=86400)
    )
    last_7d = sum(
        1 for x in rows
        if _is_recent(getattr(x.report, "created_at", None), now=now, seconds=7 * 86400)
    )
    unresolved = sum(1 for x in rows if str(x.report.status).lower() not in {"resolved", "closed", "done"})
    urgent = sum(1 for x in rows if x.priority_level == "high" or x.risk_level == "high")
    assigned = sum(1 for x in rows if x.report.organization_id)

    return {
        "recommendations": recommendations,
        "top_recommendations": recommendations[:10],
        "last_24h": last_24h,
        "last_7d": last_7d,
        "unresolved": unresolved,
        "urgent": urgent,
        "assigned": assigned,
        "assignment_rate": round(100.0 * assigned / max(len(rows), 1), 2),
        "high_risk_clusters": sum(1 for x in raw if x["risk_level"] == "high"),
        "medium_risk_clusters": sum(1 for x in raw if x["risk_level"] == "medium"),
        "low_risk_clusters": sum(1 for x in raw if x["risk_level"] == "low"),
        "resource_labels": [x["cluster"] for x in recommendations[:10]],
        "resource_values": [round(x["resource_share"] * 100, 2) for x in recommendations[:10]],
        "generated_at": now.isoformat(),
    }
