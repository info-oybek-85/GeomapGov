from __future__ import annotations

import csv
import json
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render

from reports.models import Report


def _json(path: Path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


@login_required
def geoai_lab(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Bu sahifa faqat superadministrator uchun.")

    base = Path(settings.BASE_DIR)

    total_reports = Report.objects.count()
    geocoded = (
        Report.objects
        .exclude(latitude__isnull=True)
        .exclude(longitude__isnull=True)
        .count()
    )

    gsor = _json(base / "data" / "gsor" / "gsor_evaluation.json")

    # Existing GeoAI model metrics, if present
    model_metrics = {}
    for candidate in (
        base / "ml" / "geoai_fusion_metrics.json",
        base / "data" / "geoai_fusion_metrics.json",
        base / "geoai" / "geoai_fusion_metrics.json",
    ):
        if candidate.exists():
            model_metrics = _json(candidate)
            break

    verified_file = base / "data" / "problem_datasets" / "verified_routing_dataset.csv"
    verified_count = 0
    if verified_file.exists():
        try:
            with verified_file.open("r", encoding="utf-8-sig", newline="") as f:
                verified_count = sum(1 for _ in csv.DictReader(f))
        except Exception:
            pass

    return render(request, "superadmin/geoai_lab.html", {
        "total_reports": total_reports,
        "geocoded": geocoded,
        "geo_coverage": round(geocoded / total_reports * 100, 1) if total_reports else 0,
        "gsor": gsor,
        "model_metrics": model_metrics,
        "verified_count": verified_count,
    })
