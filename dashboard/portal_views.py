from __future__ import annotations

import json
import csv
from collections import Counter
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.db.models import Count
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from reports.models import Report

try:
    from organizations.models import Organization
except Exception:
    Organization = None


def _safe_json(path: Path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _platform_context():
    base = Path(settings.BASE_DIR)

    total_reports = Report.objects.count()
    resolved_reports = Report.objects.filter(status="resolved").count()
    geocoded_reports = (
        Report.objects
        .exclude(latitude__isnull=True)
        .exclude(longitude__isnull=True)
        .count()
    )

    organizations_count = 0
    if Organization is not None:
        try:
            organizations_count = Organization.objects.count()
        except Exception:
            pass

    telegram_bot_url = getattr(settings, "SMARTGEOAI_TELEGRAM_BOT_URL", "").strip()
    resolved_percent = round(resolved_reports / total_reports * 100, 1) if total_reports else 0
    geo_coverage = round(geocoded_reports / total_reports * 100, 1) if total_reports else 0

    gsor_metrics = _safe_json(base / "data" / "gsor" / "gsor_evaluation.json")
    gsor_reference = int(gsor_metrics.get("records_with_reference_label") or 0)
    if gsor_reference >= 500:
        gsor_research_level = "Kuchli"
        gsor_research_class = "good"
    elif gsor_reference >= 100:
        gsor_research_level = "Yetarli"
        gsor_research_class = "warn"
    else:
        gsor_research_level = "Pilot"
        gsor_research_class = "bad"

    gsor_reference = int(gsor_metrics.get("records_with_reference_label") or 0)
    gsor_top1 = gsor_metrics.get("top1_accuracy")
    gsor_ready = bool(gsor_metrics)

    db_ok = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            db_ok = cursor.fetchone()[0] == 1
    except Exception:
        db_ok = False

    # Status scoring
    status_items = []

    if gsor_ready:
        if gsor_reference >= 100:
            level, ok, label = "good", True, f"Ready · {gsor_reference} reference"
        elif gsor_reference > 0:
            level, ok, label = "warn", True, f"Pilot · {gsor_reference} reference"
        else:
            level, ok, label = "warn", True, "Metrika bor, reference yo‘q"
    else:
        level, ok, label = "bad", False, "Dataset kutilmoqda"
    status_items.append({
        "name": "AI / GSOR Engine",
        "ok": ok,
        "level": level,
        "label": label,
        "detail": f"Top-1: {gsor_top1}" if gsor_top1 is not None else "Baholash hali bajarilmagan",
    })

    if telegram_bot_url:
        status_items.append({
            "name": "Telegram Bot",
            "ok": True,
            "level": "good",
            "label": "Ulangan",
            "detail": "Public murojaat yuborish havolasi mavjud",
        })
    else:
        status_items.append({
            "name": "Telegram Bot",
            "ok": False,
            "level": "bad",
            "label": "Sozlanmagan",
            "detail": "SMARTGEOAI_TELEGRAM_BOT_URL ni kiriting",
        })

    if geo_coverage >= 95:
        geo_level = "good"
    elif geo_coverage >= 70:
        geo_level = "warn"
    else:
        geo_level = "bad"
    status_items.append({
        "name": "GIS Monitoring",
        "ok": geo_coverage > 0,
        "level": geo_level,
        "label": f"{geo_coverage}% qamrov",
        "detail": f"{geocoded_reports}/{total_reports} murojaat koordinatali",
    })

    status_items.append({
        "name": "Database",
        "ok": db_ok,
        "level": "good" if db_ok else "bad",
        "label": "Connected" if db_ok else "Unavailable",
        "detail": "ORM va SELECT 1 tekshiruvi",
    })

    healthy_count = sum(1 for x in status_items if x["level"] == "good")
    warning_count = sum(1 for x in status_items if x["level"] == "warn")
    critical_count = sum(1 for x in status_items if x["level"] == "bad")

    return {
        "total_reports": total_reports,
        "resolved_reports": resolved_reports,
        "resolved_percent": resolved_percent,
        "organizations_count": organizations_count,
        "geo_coverage": geo_coverage,
        "telegram_bot_url": telegram_bot_url,
        "platform_status": status_items,
        "status_healthy_count": healthy_count,
        "status_warning_count": warning_count,
        "status_critical_count": critical_count,
        "gsor_metrics": gsor_metrics,
        "gsor_research_level": gsor_research_level,
        "gsor_research_class": gsor_research_class,
    }


def public_portal(request):
    return render(request, "public/portal.html", _platform_context())


def public_resolved_map_data(request):
    """
    Public map endpoint:
    - only RESOLVED;
    - coordinates rounded to 3 decimals;
    - no PII / user / phone / telegram id / attachments / internal report id.
    """
    qs = (
        Report.objects
        .filter(status="resolved")
        .exclude(latitude__isnull=True)
        .exclude(longitude__isnull=True)
        .select_related("organization")
        .order_by("-created_at")[:1000]
    )

    points = []
    category_counter = Counter()
    org_counter = Counter()

    for report in qs:
        text = (getattr(report, "description", "") or "").strip()
        category = (getattr(report, "category_ai", "") or "").strip() or "Boshqa"

        org_name = ""
        try:
            if report.organization:
                org_name = report.organization.name
        except Exception:
            pass
        org_name = org_name or "Tashkilot belgilanmagan"

        category_counter[category] += 1
        org_counter[org_name] += 1

        points.append({
            "lat": round(float(report.latitude), 3),
            "lng": round(float(report.longitude), 3),
            "category": category,
            "organization": org_name,
            "summary": text[:110] + ("…" if len(text) > 110 else ""),
            "status": "Hal qilingan",
        })

    return JsonResponse({
        "count": len(points),
        "privacy": "coordinates_rounded_3_decimals",
        "categories": [
            {"name": name, "count": count}
            for name, count in category_counter.most_common()
        ],
        "top_organizations": [
            {"name": name, "count": count}
            for name, count in org_counter.most_common(5)
        ],
        "points": points,
    })

def _analytics_period_days(value):
    try:
        days = int(value)
    except (TypeError, ValueError):
        return 30
    return days if days in (7, 30, 90) else 30


def _public_analytics_payload(days=30):
    """
    Aggregate-only analytics payload.
    No PII and no raw complaint texts.
    """
    now = timezone.now()
    start_date = now - timedelta(days=days - 1)

    period_qs = Report.objects.filter(created_at__gte=start_date)

    total_all = Report.objects.count()
    resolved_all = Report.objects.filter(status="resolved").count()

    period_total = period_qs.count()
    period_resolved = period_qs.filter(status="resolved").count()
    period_active = period_qs.exclude(status="resolved").count()

    category_rows = (
        period_qs
        .exclude(category_ai__isnull=True)
        .exclude(category_ai="")
        .values("category_ai")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    org_rows = (
        period_qs
        .filter(organization__isnull=False)
        .values("organization__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    daily = {}
    for created_at, status in period_qs.values_list("created_at", "status"):
        day_value = created_at.date() if hasattr(created_at, "date") else created_at
        key = day_value.isoformat()
        if key not in daily:
            daily[key] = {"date": key, "total": 0, "resolved": 0}
        daily[key]["total"] += 1
        if status == "resolved":
            daily[key]["resolved"] += 1

    trend = []
    for i in range(days):
        day = (start_date.date() + timedelta(days=i)).isoformat()
        trend.append(daily.get(day, {"date": day, "total": 0, "resolved": 0}))

    return {
        "period_days": days,
        "summary": {
            "period_total": period_total,
            "period_resolved": period_resolved,
            "period_active": period_active,
            "period_resolved_percent": round(period_resolved / period_total * 100, 1)
            if period_total else 0,
            "all_total": total_all,
            "all_resolved": resolved_all,
            "all_resolved_percent": round(resolved_all / total_all * 100, 1)
            if total_all else 0,
        },
        "categories": [
            {"name": row["category_ai"], "count": row["count"]}
            for row in category_rows
        ],
        "organizations": [
            {"name": row["organization__name"], "count": row["count"]}
            for row in org_rows
        ],
        "trend": trend,
        "privacy": "aggregate_only_no_pii",
    }


def public_analytics_data(request):
    days = _analytics_period_days(request.GET.get("days"))
    return JsonResponse(_public_analytics_payload(days))


def public_analytics_csv(request):
    """
    Public CSV export containing aggregated analytics only.
    """
    days = _analytics_period_days(request.GET.get("days"))
    data = _public_analytics_payload(days)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="smartgeoai_public_analytics_{days}d.csv"'
    )
    response.write("\ufeff")
    writer = csv.writer(response)

    writer.writerow(["SmartGeoAI Public Analytics"])
    writer.writerow(["Period days", days])
    writer.writerow([])
    writer.writerow(["Summary"])
    writer.writerow(["Metric", "Value"])
    for key, value in data["summary"].items():
        writer.writerow([key, value])

    writer.writerow([])
    writer.writerow(["Categories"])
    writer.writerow(["Category", "Count"])
    for row in data["categories"]:
        writer.writerow([row["name"], row["count"]])

    writer.writerow([])
    writer.writerow(["Organizations"])
    writer.writerow(["Organization", "Count"])
    for row in data["organizations"]:
        writer.writerow([row["name"], row["count"]])

    writer.writerow([])
    writer.writerow(["Daily trend"])
    writer.writerow(["Date", "Total", "Resolved"])
    for row in data["trend"]:
        writer.writerow([row["date"], row["total"], row["resolved"]])

    return response

def public_research_data(request):
    """
    Public scientific-transparency endpoint.
    Only model/dataset metadata and aggregate metrics.
    """
    base = Path(settings.BASE_DIR)
    gsor_file = base / "data" / "gsor" / "gsor_evaluation.json"
    gsor = _safe_json(gsor_file)

    reference = int(gsor.get("records_with_reference_label") or 0)

    if reference >= 500:
        level = "strong"
        level_label = "Kuchli"
        recommendation = "Ilmiy baholash uchun dataset hajmi yaxshi darajada."
    elif reference >= 100:
        level = "adequate"
        level_label = "Yetarli"
        recommendation = "Natijalar ilmiy tahlil uchun yetarli, lekin datasetni kengaytirish foydali."
    else:
        level = "pilot"
        level_label = "Pilot"
        recommendation = "Natijani yakuniy ilmiy xulosa sifatida emas, pilot baho sifatida talqin qiling."

    updated_at = None
    if gsor_file.exists():
        try:
            updated_at = timezone.datetime.fromtimestamp(
                gsor_file.stat().st_mtime,
                tz=timezone.get_current_timezone()
            ).isoformat()
        except Exception:
            updated_at = None

    latest_report_at = None
    try:
        latest = Report.objects.order_by("-created_at").values_list("created_at", flat=True).first()
        latest_report_at = latest.isoformat() if latest else None
    except Exception:
        pass

    return JsonResponse({
        "model": {
            "name": "GSOR — Geo Semantic Organization Routing",
            "purpose": "Murojaat uchun asosiy va alternativ tashkilotlarni Top-k ranking asosida aniqlash",
            "evaluation_level": level,
            "evaluation_level_label": level_label,
            "recommendation": recommendation,
        },
        "metrics": {
            "top1_accuracy": gsor.get("top1_accuracy"),
            "top3_accuracy": gsor.get("top3_accuracy"),
            "mrr": gsor.get("mrr"),
            "reference_records": reference,
            "records_total": gsor.get("records_total"),
        },
        "methodology": {
            "pipeline": [
                "Real murojaat",
                "Matn va kontekst tahlili",
                "GSOR Top-k routing",
                "Expert Validation",
                "Verified Dataset",
                "Qayta baholash"
            ],
            "principles": [
                "Human-in-the-Loop",
                "Top-k ranking",
                "MRR",
                "Cross-validation",
                "Geo-context",
                "Privacy-by-design"
            ],
        },
        "freshness": {
            "gsor_metrics_updated_at": updated_at,
            "latest_report_at": latest_report_at,
        },
        "privacy": "aggregate_and_model_metadata_only",
    })

