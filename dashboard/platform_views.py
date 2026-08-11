from __future__ import annotations

import csv
import json
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import OperationalError, ProgrammingError
from django.http import HttpResponseForbidden
from django.shortcuts import render

from reports.models import Report

try:
    from organizations.models import OrganizationPredictionFeedback
except Exception:
    OrganizationPredictionFeedback = None


def _require_superuser(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Bu sahifa faqat superadministrator uchun.")
    return None


def _feedback_stats():
    """
    Expert Validation jadvali hali migrate qilinmagan bo'lsa ham
    Platform Center 500 bermasligi uchun xavfsiz statistik wrapper.
    """
    result = {"pending": 0, "verified": 0, "available": False}
    if OrganizationPredictionFeedback is None:
        return result
    try:
        result["pending"] = OrganizationPredictionFeedback.objects.filter(
            expert_status="pending"
        ).count()
        result["verified"] = OrganizationPredictionFeedback.objects.filter(
            expert_status__in=["verified", "corrected"]
        ).count()
        result["available"] = True
    except (OperationalError, ProgrammingError):
        pass
    except Exception:
        pass
    return result


@login_required
def platform_center(request):
    denied = _require_superuser(request)
    if denied:
        return denied

    total_reports = Report.objects.count()
    geo_reports = (
        Report.objects
        .exclude(latitude__isnull=True)
        .exclude(longitude__isnull=True)
        .count()
    )
    feedback = _feedback_stats()

    gsor_file = Path(settings.BASE_DIR) / "data" / "gsor" / "gsor_evaluation.json"
    gsor = {}
    if gsor_file.exists():
        try:
            gsor = json.loads(gsor_file.read_text(encoding="utf-8"))
        except Exception:
            gsor = {}

    return render(request, "superadmin/platform_center.html", {
        "total_reports": total_reports,
        "geo_reports": geo_reports,
        "geo_coverage": round(geo_reports / total_reports * 100, 1) if total_reports else 0,
        "pending_expert": feedback["pending"],
        "verified_expert": feedback["verified"],
        "expert_available": feedback["available"],
        "gsor": gsor,
    })


@login_required
def gsor_center(request):
    denied = _require_superuser(request)
    if denied:
        return denied

    base = Path(settings.BASE_DIR)
    metrics_file = base / "data" / "gsor" / "gsor_evaluation.json"
    predictions_file = base / "data" / "gsor" / "gsor_predictions.csv"
    verified_file = base / "data" / "problem_datasets" / "verified_routing_dataset.csv"

    metrics = {}
    if metrics_file.exists():
        try:
            metrics = json.loads(metrics_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    predictions = []
    if predictions_file.exists():
        try:
            with predictions_file.open("r", encoding="utf-8-sig", newline="") as f:
                predictions = list(csv.DictReader(f))[:50]
        except Exception:
            pass

    verified_count = 0
    if verified_file.exists():
        try:
            with verified_file.open("r", encoding="utf-8-sig", newline="") as f:
                verified_count = sum(1 for _ in csv.DictReader(f))
        except Exception:
            pass

    return render(request, "superadmin/gsor_center.html", {
        "metrics": metrics,
        "predictions": predictions,
        "verified_count": verified_count,
        "has_evaluation": bool(metrics),
    })
