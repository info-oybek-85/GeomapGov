import csv
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Max, Min
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.utils.dateparse import parse_date

from .models import ComplaintAnalysis
from .metrics import load_fusion_metrics
from .smart_services import build_smart_dashboard
from .report_services import build_model_results_pdf, build_system_results_pdf
from .retrain_services import latest_model_comparison, retrain_geoai_model


def _filtered_queryset(request):
    qs = ComplaintAnalysis.objects.select_related("report", "report__organization").all()
    category = (request.GET.get("category") or "").strip()
    priority = (request.GET.get("priority") or "").strip()
    risk = (request.GET.get("risk") or "").strip()
    date_from = (request.GET.get("date_from") or "").strip()
    date_to = (request.GET.get("date_to") or "").strip()
    if category:
        qs = qs.filter(predicted_category=category)
    if priority:
        qs = qs.filter(priority_level=priority)
    if risk:
        qs = qs.filter(risk_level=risk)
    # BaseModel.created_at — DateField. parse_date noto‘g‘ri qiymatlarni xavfsiz rad etadi.
    parsed_from = parse_date(date_from) if date_from else None
    parsed_to = parse_date(date_to) if date_to else None
    if parsed_from:
        qs = qs.filter(report__created_at__gte=parsed_from)
    if parsed_to:
        qs = qs.filter(report__created_at__lte=parsed_to)
    return qs, category, priority, risk, date_from, date_to


def _priority_dashboard(qs):
    rows = list(qs.order_by("report__created_at", "-priority_index"))
    level_order = ["high", "medium", "low"]
    level_labels = {"high": "Yuqori", "medium": "O‘rta", "low": "Past"}
    level_counts = {k: 0 for k in level_order}
    category_data = defaultdict(lambda: {"sum": 0.0, "count": 0})
    timeline_data = defaultdict(lambda: {"sum": 0.0, "count": 0})
    component_names = [
        ("spatial_density", "Hududiy zichlik ρᵢ"),
        ("recurrence_frequency", "Takrorlanish fᵢ"),
        ("temporal_relevance", "Dolzarblik qᵢ"),
        ("severity_weight", "Og‘irlik W(Cᵢ)"),
        ("classifier_confidence", "Ishonchlilik Confᵢ"),
        ("neighbor_influence", "Qo‘shnichilik nᵢ"),
    ]
    component_sums = {field: 0.0 for field, _ in component_names}

    histogram_edges = [0.0, 0.2, 0.4, 0.6, 0.8, 1.000001]
    histogram_labels = ["0.00–0.19", "0.20–0.39", "0.40–0.59", "0.60–0.79", "0.80–1.00"]
    histogram_values = [0] * 5

    for row in rows:
        level_counts[row.priority_level] = level_counts.get(row.priority_level, 0) + 1
        cat = row.predicted_category or "other"
        category_data[cat]["sum"] += float(row.priority_index)
        category_data[cat]["count"] += 1
        day = row.report.created_at.isoformat() if row.report.created_at else "Noma’lum"
        timeline_data[day]["sum"] += float(row.priority_index)
        timeline_data[day]["count"] += 1
        for field, _ in component_names:
            component_sums[field] += float(getattr(row, field) or 0.0)
        value = max(0.0, min(1.0, float(row.priority_index)))
        for idx in range(5):
            if histogram_edges[idx] <= value < histogram_edges[idx + 1]:
                histogram_values[idx] += 1
                break

    n = max(len(rows), 1)
    category_sorted = sorted(
        (
            {"label": label, "value": data["sum"] / data["count"], "count": data["count"]}
            for label, data in category_data.items()
        ),
        key=lambda x: x["value"],
        reverse=True,
    )
    timeline_sorted = sorted(
        ({"label": day, "value": data["sum"] / data["count"], "count": data["count"]} for day, data in timeline_data.items()),
        key=lambda x: x["label"],
    )
    return {
        "level_labels": [level_labels[k] for k in level_order],
        "level_values": [level_counts.get(k, 0) for k in level_order],
        "histogram_labels": histogram_labels,
        "histogram_values": histogram_values,
        "category_labels": [x["label"] for x in category_sorted],
        "category_values": [round(x["value"], 4) for x in category_sorted],
        "category_counts": [x["count"] for x in category_sorted],
        "timeline_labels": [x["label"] for x in timeline_sorted],
        "timeline_values": [round(x["value"], 4) for x in timeline_sorted],
        "component_labels": [label for _, label in component_names],
        "component_values": [round(component_sums[field] / n, 4) for field, _ in component_names],
        "max_priority": round(max((float(x.priority_index) for x in rows), default=0.0), 4),
        "min_priority": round(min((float(x.priority_index) for x in rows), default=0.0), 4),
    }



def _risk_dashboard(qs):
    rows = list(qs.exclude(cluster_label__isnull=True).select_related("report"))
    clusters = {}
    noise = 0
    for row in rows:
        if row.cluster_label == -1:
            noise += 1
            continue
        item = clusters.setdefault(row.cluster_label, {
            "label": row.cluster_label, "count": 0, "risk_index": float(row.risk_index),
            "risk_level": row.risk_level or "low", "kde_sum": 0.0, "priority_sum": 0.0,
            "lat_sum": 0.0, "lng_sum": 0.0, "points": [],
        })
        item["count"] += 1
        item["risk_index"] = max(item["risk_index"], float(row.risk_index))
        item["risk_level"] = row.risk_level or item["risk_level"]
        item["kde_sum"] += float(row.weighted_kde)
        item["priority_sum"] += float(row.priority_index)
        lat, lng = float(row.report.latitude), float(row.report.longitude)
        item["lat_sum"] += lat; item["lng_sum"] += lng
        item["points"].append([lat, lng])
    result=[]
    counts={"high":0,"medium":0,"low":0}
    for item in clusters.values():
        n=max(item["count"],1)
        item["center"]=[item["lat_sum"]/n,item["lng_sum"]/n]
        item["avg_kde"]=item["kde_sum"]/n
        item["avg_priority"]=item["priority_sum"]/n
        counts[item["risk_level"] if item["risk_level"] in counts else "low"] += 1
        result.append(item)
    result.sort(key=lambda x:x["risk_index"], reverse=True)
    risk_values=[x["risk_index"] for x in result]
    return {
        "clusters": result,
        "cluster_count": len(result),
        "noise_count": noise,
        "high_count": counts["high"],
        "medium_count": counts["medium"],
        "low_count": counts["low"],
        "max_risk": max(risk_values, default=0.0),
        "avg_risk": sum(risk_values)/max(len(risk_values),1),
        "risk_labels": [f"K{x['label']}" for x in result],
        "risk_values": [round(x["risk_index"],4) for x in result],
        "risk_counts": [x["count"] for x in result],
    }

@login_required
def analytics_dashboard(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Faqat superadministrator uchun")

    qs, category, priority, risk, date_from, date_to = _filtered_queryset(request)
    counts = dict(qs.values("priority_level").annotate(c=Count("id")).values_list("priority_level", "c"))
    categories = list(
        ComplaintAnalysis.objects.exclude(predicted_category="")
        .values_list("predicted_category", flat=True).distinct().order_by("predicted_category")
    )
    points = [
        {
            "id": str(a.report_id),
            "lat": float(a.report.latitude),
            "lng": float(a.report.longitude),
            "category": a.predicted_category,
            "confidence": round(a.classifier_confidence, 4),
            "priority": round(a.priority_index, 4),
            "level": a.priority_level,
            "cluster": a.cluster_label,
            "wkde": round(a.weighted_kde, 4),
            "risk": round(a.risk_index, 4),
            "risk_level": a.risk_level,
            "description": a.report.description,
            "created_at": a.report.created_at.isoformat() if a.report.created_at else "",
            "status": a.report.status,
            "organization": a.report.organization.name if a.report.organization else "Biriktirilmagan",
            "components": {
                "density": round(a.spatial_density, 4),
                "frequency": round(a.recurrence_frequency, 4),
                "recency": round(a.temporal_relevance, 4),
                "severity": round(a.severity_weight, 4),
                "neighbor": round(a.neighbor_influence, 4),
            },
        }
        for a in qs.exclude(report__latitude__isnull=True).exclude(report__longitude__isnull=True)[:1500]
    ]
    model_metrics = load_fusion_metrics()
    context = {
        "total": qs.count(),
        "avg_priority": qs.aggregate(v=Avg("priority_index"))["v"] or 0,
        "avg_confidence": qs.aggregate(v=Avg("classifier_confidence"))["v"] or 0,
        "counts": counts,
        "categories": categories,
        "selected_category": category,
        "selected_priority": priority,
        "selected_risk": risk,
        "selected_date_from": date_from,
        "selected_date_to": date_to,
        "top_reports": qs.order_by("-priority_index")[:20],
        "points": points,
        "model_metrics": model_metrics,
        "priority_stats": _priority_dashboard(qs),
        "risk_stats": _risk_dashboard(qs),
        "smart_stats": build_smart_dashboard(qs),
        "model_comparison": latest_model_comparison(),
    }
    return render(request, "geoai/analytics.html", context)


@login_required
def priority_export_csv(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()
    qs, _, _, _, _, _ = _filtered_queryset(request)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="geo_priority_results.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow([
        "ID", "Murojaat", "Kategoriya", "Conf_i", "rho_i", "f_i", "q_i",
        "W(C_i)", "n_i", "P_i", "Daraja", "Latitude", "Longitude", "Sana",
    ])
    for a in qs.order_by("-priority_index"):
        writer.writerow([
            a.report_id, a.report.description, a.predicted_category,
            f"{a.classifier_confidence:.6f}", f"{a.spatial_density:.6f}",
            f"{a.recurrence_frequency:.6f}", f"{a.temporal_relevance:.6f}",
            f"{a.severity_weight:.6f}", f"{a.neighbor_influence:.6f}",
            f"{a.priority_index:.6f}", a.get_priority_level_display(),
            a.report.latitude, a.report.longitude, a.report.created_at,
        ])
    return response


@login_required
def analytics_json(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()
    rows = ComplaintAnalysis.objects.select_related("report").order_by("-priority_index")[:500]
    return JsonResponse({"results": [
        {
            "report_id": str(x.report_id),
            "category": x.predicted_category,
            "confidence": x.classifier_confidence,
            "priority": x.priority_index,
            "priority_level": x.priority_level,
            "lat": float(x.report.latitude) if x.report.latitude is not None else None,
            "lng": float(x.report.longitude) if x.report.longitude is not None else None,
        } for x in rows
    ]})


@login_required
def smart_export_csv(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()
    qs, _, _, _, _, _ = _filtered_queryset(request)
    stats = build_smart_dashboard(qs)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="smart_online_recommendations.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow([
        "Rank", "Klaster", "H_k", "Xavf", "Murojaatlar", "Kategoriya",
        "Mas'ul tashkilot", "Tavsiya", "Javob muddati (soat)", "Resurs ulushi (%)", "Asos"
    ])
    for item in stats["recommendations"]:
        writer.writerow([
            item["rank"], item["cluster"], item["risk_index"], item["risk_level"],
            item["complaint_count"], item["dominant_category"], item["responsible_organization"],
            item["action"], item["response_hours"], round(item["resource_share"] * 100, 2), item["rationale"],
        ])
    return response


@login_required
def smart_online_json(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()
    qs, _, _, _, _, _ = _filtered_queryset(request)
    return JsonResponse(build_smart_dashboard(qs))


@login_required
def retrain_model(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()
    if request.method != "POST":
        return redirect("geoai:analytics")
    try:
        result = retrain_geoai_model()
        messages.success(
            request,
            f"Model qayta o‘qitildi: {result.get('current_version', 'yangi versiya')}. "
            f"Dataset: {result.get('dataset_size', 0)} ta yozuv.",
        )
    except Exception as exc:
        messages.error(request, f"Modelni qayta o‘qitishda xato: {exc}")
    return redirect("geoai:analytics")


@login_required
def model_results_pdf(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()
    payload = build_model_results_pdf(latest_model_comparison())
    response = HttpResponse(payload, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="GeoAI_Model_Natijalari.pdf"'
    return response


@login_required
def system_results_pdf(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()
    qs, _, _, _, _, _ = _filtered_queryset(request)
    priority_stats = _priority_dashboard(qs)
    risk_stats = _risk_dashboard(qs)
    payload = build_system_results_pdf(qs, priority_stats, risk_stats)
    response = HttpResponse(payload, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="GeoAI_Tizim_Natijalari.pdf"'
    return response
