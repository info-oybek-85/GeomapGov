from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import Organization, OrganizationPredictionFeedback


def _is_expert(user):
    return bool(user.is_authenticated and (user.is_superuser or user.is_staff))


expert_required = user_passes_test(_is_expert, login_url="dashboard:login")


PROBLEM_CHOICES = [
    ("ELEC_OUTAGE", "Elektr uzilishi"),
    ("ELEC_TRANSFORMER", "Transformator nosozligi"),
    ("ELEC_WIRE", "Elektr simi xavfi"),
    ("ELEC_POLE", "Elektr ustuni"),
    ("ELEC_STREET_LIGHT", "Ko‘cha yoritgichi"),
    ("ELEC_VOLTAGE", "Kuchlanish muammosi"),
    ("ECO_WASTE", "Chiqindi"),
    ("ECO_TREE_FALL", "Daraxt qulashi"),
    ("ECO_ILLEGAL_DUMP", "Noqonuniy chiqindi"),
    ("ECO_AIR", "Havo ifloslanishi"),
    ("ECO_WATER_POLLUTION", "Suv ifloslanishi"),
    ("ROAD_DAMAGE", "Yo‘l nosozligi"),
    ("TRAFFIC_LIGHT", "Svetofor"),
    ("WATER_SUPPLY", "Ichimlik suvi"),
    ("SEWERAGE", "Kanalizatsiya"),
    ("GAS_SUPPLY", "Gaz ta’minoti"),
    ("HOUSING_COMMUNAL", "Uy-joy kommunal"),
    ("OTHER", "Boshqa"),
]


@expert_required
def expert_validation_queue(request):
    qs = OrganizationPredictionFeedback.objects.select_related(
        "predicted_organization", "selected_organization", "expert_primary_organization", "user"
    ).order_by("-created_at")

    status_value = (request.GET.get("status") or "pending").strip()
    q = (request.GET.get("q") or "").strip()
    accepted = (request.GET.get("accepted") or "").strip()

    if status_value != "all":
        qs = qs.filter(expert_status=status_value)
    if accepted == "yes":
        qs = qs.filter(accepted=True)
    elif accepted == "no":
        qs = qs.filter(accepted=False)
    if q:
        qs = qs.filter(
            Q(text__icontains=q)
            | Q(predicted_organization__name__icontains=q)
            | Q(selected_organization__name__icontains=q)
            | Q(expert_primary_problem__icontains=q)
        )

    totals = OrganizationPredictionFeedback.objects.aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(expert_status="pending")),
        verified=Count("id", filter=Q(expert_status="verified")),
        corrected=Count("id", filter=Q(expert_status="corrected")),
        rejected=Count("id", filter=Q(expert_status="rejected")),
    )
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page") or 1)
    return render(request, "expert_validation/queue.html", {
        "page_obj": page_obj,
        "totals": totals,
        "status_value": status_value,
        "accepted": accepted,
        "q": q,
    })


@expert_required
@require_http_methods(["GET", "POST"])
def expert_validation_detail(request, pk):
    item = get_object_or_404(
        OrganizationPredictionFeedback.objects.select_related(
            "predicted_organization", "selected_organization", "expert_primary_organization", "report", "user"
        ),
        pk=pk,
    )
    organizations = Organization.objects.filter(is_active=True).order_by("name")

    if request.method == "POST":
        action = (request.POST.get("action") or "save").strip()
        primary_problem = (request.POST.get("primary_problem") or "").strip()
        secondary = [x.strip() for x in (request.POST.get("secondary_problems") or "").split(",") if x.strip()]
        supporting = [x for x in request.POST.getlist("supporting_organizations") if x]
        priority = (request.POST.get("priority") or "").strip()
        note = (request.POST.get("expert_note") or "").strip()
        primary_org_id = request.POST.get("primary_organization") or None
        primary_org = Organization.objects.filter(pk=primary_org_id).first() if primary_org_id else None

        if action == "reject":
            item.expert_status = OrganizationPredictionFeedback.EXPERT_REJECTED
        else:
            if not primary_problem:
                messages.error(request, "Asosiy muammo turini tanlang.")
                return redirect("dashboard:expert_validation_detail", pk=item.pk)
            if not primary_org:
                messages.error(request, "Asosiy tashkilotni tanlang.")
                return redirect("dashboard:expert_validation_detail", pk=item.pk)
            prediction_matches = (
                item.predicted_organization_id == primary_org.id
                and (not item.expert_primary_problem or item.expert_primary_problem == primary_problem)
            )
            item.expert_status = (
                OrganizationPredictionFeedback.EXPERT_VERIFIED
                if action == "confirm" and prediction_matches
                else OrganizationPredictionFeedback.EXPERT_CORRECTED
            )

        item.expert_primary_problem = primary_problem
        item.expert_secondary_problems = secondary
        item.expert_primary_organization = primary_org
        item.expert_supporting_organizations = supporting
        item.expert_priority = priority
        item.expert_note = note
        item.reviewed_by = request.user
        item.reviewed_at = timezone.now()
        item.save(update_fields=[
            "expert_status", "expert_primary_problem", "expert_secondary_problems",
            "expert_primary_organization", "expert_supporting_organizations",
            "expert_priority", "expert_note", "reviewed_by", "reviewed_at",
        ])
        messages.success(request, "Ekspert xulosasi saqlandi.")
        next_pending = OrganizationPredictionFeedback.objects.filter(
            expert_status=OrganizationPredictionFeedback.EXPERT_PENDING
        ).exclude(pk=item.pk).order_by("created_at").first()
        if request.POST.get("save_next") and next_pending:
            return redirect("dashboard:expert_validation_detail", pk=next_pending.pk)
        return redirect("dashboard:expert_validation_queue")

    initial_org = item.expert_primary_organization or item.selected_organization or item.predicted_organization
    return render(request, "expert_validation/detail.html", {
        "item": item,
        "organizations": organizations,
        "problem_choices": PROBLEM_CHOICES,
        "initial_org_id": initial_org.id if initial_org else "",
        "secondary_text": ", ".join(item.expert_secondary_problems or []),
        "supporting_ids": {str(x) for x in (item.expert_supporting_organizations or [])},
    })
