from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q, Exists, OuterRef
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from users.models import User
from users.choices import UserChoices
from reports.models import Report, ReportAssignment
from organizations.models import Organization, OrganizationMember
from django.utils import timezone
from datetime import datetime, date, time, timedelta
from django.db.models import Count, Avg, F, ExpressionWrapper, DurationField
import json


def _as_aware_datetime(value):
    """Date yoki datetime qiymatini timezone-aware datetime ga aylantiradi."""
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


def org_admin_required(view_func):
    @login_required
    def _wrapped(request, *args, **kwargs):
        print(request.user.user_type)
        print(getattr(request.user, "user_type", None))
        if getattr(request.user, "user_type", None) != UserChoices.DISPATCHER:
            return HttpResponseForbidden("Forbidden")
        return view_func(request, *args, **kwargs)
    return _wrapped


def get_my_organization(user: User):
    """
    Org admin qaysi organization ga tegishli ekanini topish.
    Sizning loyihangizda qanday bog'langan bo'lsa shunga moslab o'zgartirasiz.
    """
    # 1) user.organization FK bo'lsa:
    org = getattr(user, "organization", None)
    if org:
        return org

    # 2) user.organizations m2m bo'lsa:
    orgs = getattr(user, "organizations", None)
    if orgs and hasattr(orgs, "first"):
        return orgs.first()

    return None


def get_org_members_manager(org: Organization):
    """
    Organization ichidagi reporterlar manager'i.
    Sizda qaysi field bo'lsa shuni qoldiring: members/users/reporters...
    """
    for attr in ("members", "users", "reporters"):
        manager = getattr(org, attr, None)
        if manager is not None and hasattr(manager, "all") and hasattr(manager, "add") and hasattr(manager, "remove"):
            return manager
    raise AttributeError(
        "Organization modelida reporterlar uchun ManyToMany topilmadi. "
        "Organization.members yoki Organization.users kabi field qo'shing."
    )


@login_required
def org_users_list(request):
    # =========================
    # 1. Organization ADMIN tekshiruvi
    # =========================
    admin_membership = (
        OrganizationMember.objects
        .filter(user=request.user, role__iexact=OrganizationMember.ROLE_ADMIN)
        .select_related("organization")
        .first()
    )

    if not admin_membership:
        # (diagnostika uchun) userning barcha membershiplarini ko'rsatamiz
        my_roles = list(
            OrganizationMember.objects
            .filter(user=request.user)
            .select_related("organization")
            .values_list("organization__name", "role")
        )
        return HttpResponseForbidden(f"Siz organization admin emassiz. Membershiplar: {my_roles}")

    org = admin_membership.organization

    # =========================
    # 2. POST: biriktirish / chiqarish
    # =========================
    if request.method == "POST":
        action = request.POST.get("action")
        user_id = request.POST.get("user_id")

        target = get_object_or_404(User, pk=user_id)

        if action == "assign":
            # faqat reporter
            if target.user_type != UserChoices.REPORTER:
                messages.error(request, "Faqat reporterlarni biriktirish mumkin")
                return redirect("dashboard:org_users")

            # oldin report yuborgan bo‘lsa -> YO‘Q
            if Report.objects.filter(user=target).exists():
                messages.error(
                    request,
                    "Bu reporter oldin report yuborgan, biriktirib bo‘lmaydi"
                )
                return redirect("dashboard:org_users")

            # allaqachon a’zo bo‘lsa
            if OrganizationMember.objects.filter(
                user=target,
                organization=org
            ).exists():
                messages.info(request, "Bu reporter allaqachon a’zo")
                return redirect("dashboard:org_users")

            with transaction.atomic():
                OrganizationMember.objects.create(
                    user=target,
                    organization=org,
                    role=OrganizationMember.ROLE_STAFF
                )
                # ✅ darrov executer ga o‘tkazamiz
                target.user_type = UserChoices.EXECUTOR   # <-- sizdagi choices nomiga mos bo‘lsin
                target.save(update_fields=["user_type"])
            messages.success(request, "Reporter organizationga biriktirildi")

        elif action == "remove":
            with transaction.atomic():
                OrganizationMember.objects.filter(user=target, organization=org).delete()

                # ✅ agar boshqa orglarda ham a’zo bo‘lmasa reporterga qaytaramiz
                still_member_somewhere = OrganizationMember.objects.filter(user=target).exists()
                if not still_member_somewhere:
                    target.user_type = UserChoices.REPORTER
                    target.save(update_fields=["user_type"])

            messages.success(request, "Foydalanuvchi organizationdan chiqarildi")

        return redirect("dashboard:org_users")

    # =========================
    # 3. TAB
    # =========================
    tab = request.GET.get("tab", "reporters")

    # =========================
    # 4. REPORTERS TAB
    # =========================
    rq = (request.GET.get("rq") or "").strip()
    rpage = request.GET.get("rpage", 1)

    reporters_qs = User.objects.filter(
        user_type=UserChoices.REPORTER
    ).annotate(
        has_reports=Exists(
            Report.objects.filter(user_id=OuterRef("pk"))
        ),
        is_member=Exists(
            OrganizationMember.objects.filter(
                user_id=OuterRef("pk"),
                organization=org
            )
        )
    ).filter(
        has_reports=False,   # ✅ report yuborganlar ko'rinmaydi
        is_member=False      # ✅ allaqachon a'zo bo'lganlar ham ko'rinmaydi
    ).order_by("-date_joined")


    if rq:
        reporters_qs = reporters_qs.filter(
            Q(username__icontains=rq) |
            Q(first_name__icontains=rq) |
            Q(last_name__icontains=rq)
        )

    reporters_page_obj = Paginator(reporters_qs, 10).get_page(rpage)

    # =========================
    # 5. MEMBERS TAB
    # =========================
    mq = (request.GET.get("mq") or "").strip()
    mpage = request.GET.get("mpage", 1)

    members_qs = User.objects.filter(
        organization_memberships__organization=org
    ).exclude(
        pk=request.user.pk
    ).order_by("-date_joined")


    if mq:
        members_qs = members_qs.filter(
            Q(username__icontains=mq) |
            Q(first_name__icontains=mq) |
            Q(last_name__icontains=mq)
        )

    members_page_obj = Paginator(members_qs, 10).get_page(mpage)

    return render(request, "organization_admin/users_list.html", {
        "org": org,
        "tab": tab,
        "reporters_page_obj": reporters_page_obj,
        "members_page_obj": members_page_obj,
        "rq": rq,
        "mq": mq,
    })


def _org_admin_membership(user):
    return OrganizationMember.objects.filter(
        user=user,
        role=OrganizationMember.ROLE_ADMIN
    ).select_related("organization").first()


def _full_name(u):
    s = f"{u.first_name} {u.last_name}".strip()
    return s if s else u.username


def _staff_role_list():
    """
    Sizdagi OrganizationMember role constantlari turlicha bo‘lishi mumkin.
    Shuning uchun bor bo‘lsa qo‘shib ketamiz.
    """
    roles = []

    # Admin / Staff
    for attr in ("ROLE_ADMIN", "ROLE_STAFF"):
        if hasattr(OrganizationMember, attr):
            roles.append(getattr(OrganizationMember, attr))

    # Executor variantlari (projectlarda turlicha yoziladi)
    for attr in ("ROLE_EXECUTOR", "ROLE_EXECUTER", "ROLE_EXECUTANT", "ROLE_WORKER", "ROLE_EMPLOYEE"):
        if hasattr(OrganizationMember, attr):
            roles.append(getattr(OrganizationMember, attr))

    # dublikatlarni olib tashlash
    return list(dict.fromkeys([r for r in roles if r]))




def _is_org_admin(user):
    if not user or not user.is_authenticated:
        return False
    # ✅ superuser ham kiradi
    if user.is_superuser:
        return True
    # ✅ Dispatcher ham org-admin hisoblanadi
    return (getattr(user, "user_type", "") or "").lower() == "dispatcher"



def _get_user_organization(user):
    if not user or not user.is_authenticated:
        return None

    # ✅ 1) Avval membership orqali topamiz (sizdagi real bog‘lanish shu)
    m = (
        OrganizationMember.objects
        .filter(user=user)
        .select_related("organization")
        .first()
    )
    if m and m.organization:
        return m.organization

    # ✅ 2) Fallback: user.organization FK bo'lsa
    org = getattr(user, "organization", None)
    if org:
        return org

    # ✅ 3) Fallback: user.organization_id bo'lsa
    org_id = getattr(user, "organization_id", None)
    if org_id:
        return Organization.objects.filter(id=org_id).first()

    return None


@login_required
@user_passes_test(_is_org_admin, login_url="/login/")
def organization_admin_dashboard(request):
    org = _get_user_organization(request.user)
    if not org:
        # organization topilmasa - dashboard'ni ochmasin
        return render(request, "organization_admin/no_organization.html", status=403)

    # ---- Filters (org fixed) ----
    q = (request.GET.get("q") or "").strip()
    selected_statuses = request.GET.getlist("status")  # bo'sh bo'lsa -> hammasi

    reports = Report.objects.select_related("user", "organization").filter(organization=org)

    if q:
        reports = reports.filter(
            Q(description__icontains=q)
            | Q(user__username__icontains=q)
            | Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(user__phone_number__icontains=q)
        )

    if selected_statuses:
        reports = reports.filter(status__in=selected_statuses)

    # ---- KPI ----
    now = timezone.localtime()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    total_count = reports.count()
    today_count = reports.filter(created_at__gte=today_start).count()
    week_count = reports.filter(created_at__gte=week_start).count()

    # SLA va ijro tezligi ko‘rsatkichlari
    active_statuses = ["new", "sent", "read", "accepted", "assigned", "in_progress", "reopened"]
    overdue_count = reports.filter(deadline_at__lt=now, status__in=active_statuses).count()
    pending_confirmation_count = reports.filter(status="pending_confirmation").count()
    resolved_today_count = reports.filter(status="resolved", resolved_at__gte=today_start).count()

    accept_minutes = []
    execution_minutes = []
    total_minutes = []
    for item in reports:
        created_at = _as_aware_datetime(item.created_at)
        accepted_at = _as_aware_datetime(item.accepted_at)
        work_started_at = _as_aware_datetime(item.work_started_at)
        work_completed_at = _as_aware_datetime(item.work_completed_at)
        resolved_at = _as_aware_datetime(item.resolved_at)

        if accepted_at and created_at and accepted_at >= created_at:
            accept_minutes.append((accepted_at - created_at).total_seconds() / 60)
        if work_started_at and work_completed_at and work_completed_at >= work_started_at:
            execution_minutes.append((work_completed_at - work_started_at).total_seconds() / 60)
        if resolved_at and created_at and resolved_at >= created_at:
            total_minutes.append((resolved_at - created_at).total_seconds() / 60)

    avg_accept_minutes = round(sum(accept_minutes) / len(accept_minutes), 1) if accept_minutes else 0
    avg_execution_minutes = round(sum(execution_minutes) / len(execution_minutes), 1) if execution_minutes else 0
    avg_total_minutes = round(sum(total_minutes) / len(total_minutes), 1) if total_minutes else 0

    status_counts_global_qs = reports.values("status").annotate(c=Count("id"))
    status_counts_global = {row["status"]: row["c"] for row in status_counts_global_qs}

    # ---- Rahbar monitoringi va xodimlar samaradorligi ----
    assignments = (
        ReportAssignment.objects
        .filter(organization=org)
        .select_related("assigned_to", "report")
    )

    worker_stats = []
    worker_ids = assignments.values_list("assigned_to_id", flat=True).distinct()
    for worker_id in worker_ids:
        worker_assignments = assignments.filter(assigned_to_id=worker_id)
        worker = worker_assignments.first().assigned_to
        assigned_total = worker_assignments.count()
        completed_total = worker_assignments.filter(report__status="resolved").count()
        in_progress_total = worker_assignments.filter(report__status="in_progress").count()
        overdue_total = worker_assignments.filter(
            deadline_at__lt=now,
            report__status__in=active_statuses,
        ).count()
        completion_rate = round((completed_total / assigned_total) * 100, 1) if assigned_total else 0

        durations = []
        for assignment in worker_assignments:
            start = assignment.started_at or assignment.report.work_started_at
            finish = assignment.completed_at or assignment.report.work_completed_at
            if start and finish:
                durations.append((finish - start).total_seconds() / 60)
        avg_minutes = round(sum(durations) / len(durations), 1) if durations else 0

        worker_stats.append({
            "id": str(worker.id),
            "name": worker.get_full_name() or worker.username,
            "username": worker.username,
            "assigned_total": assigned_total,
            "completed_total": completed_total,
            "in_progress_total": in_progress_total,
            "overdue_total": overdue_total,
            "completion_rate": completion_rate,
            "avg_minutes": avg_minutes,
        })

    worker_stats.sort(
        key=lambda x: (x["completion_rate"], x["completed_total"], -x["overdue_total"]),
        reverse=True,
    )
    top_workers = worker_stats[:5]

    urgent_assignments = []
    deadline_qs = (
        assignments
        .filter(deadline_at__isnull=False, report__status__in=active_statuses)
        .order_by("deadline_at")[:8]
    )
    for assignment in deadline_qs:
        seconds_left = (assignment.deadline_at - now).total_seconds()
        urgent_assignments.append({
            "report_id": str(assignment.report_id),
            "title": assignment.report.title or assignment.report.description[:70],
            "worker": assignment.assigned_to.get_full_name() or assignment.assigned_to.username,
            "deadline_at": assignment.deadline_at,
            "minutes_left": max(0, round(seconds_left / 60)),
            "minutes_overdue": max(0, round(abs(seconds_left) / 60)) if seconds_left < 0 else 0,
            "is_overdue": seconds_left < 0,
            "status_label": assignment.report.get_status_uz(),
        })

    # Oddiy, tushunarli AI/qaror tavsiyalari: mavjud ko‘rsatkichlardan avtomatik shakllanadi.
    ai_recommendations = []
    if overdue_count:
        ai_recommendations.append({
            "level": "danger",
            "title": "Kechikkan murojaatlarga zudlik bilan resurs ajrating",
            "text": f"{overdue_count} ta faol murojaat belgilangan muddatdan o‘tgan. Mas’ul xodimlar va brigadalar yuklamasini qayta taqsimlash tavsiya etiladi.",
        })
    if pending_confirmation_count:
        ai_recommendations.append({
            "level": "warning",
            "title": "Fuqaro tasdig‘ini tezlashtiring",
            "text": f"{pending_confirmation_count} ta murojaat fuqaro tasdig‘ini kutmoqda. Dispetcherlar fuqarolar bilan bog‘lanib yakuniy natijani qayd etishi kerak.",
        })
    new_count = status_counts_global.get("new", 0) + status_counts_global.get("sent", 0)
    if new_count:
        ai_recommendations.append({
            "level": "primary",
            "title": "Yangi murojaatlarni navbatdan chiqaring",
            "text": f"{new_count} ta yangi yoki yuborilgan murojaat bor. Ularni qabul qilish va mas’ul xodimga biriktirish tavsiya etiladi.",
        })
    if avg_accept_minutes and avg_accept_minutes > 60:
        ai_recommendations.append({
            "level": "warning",
            "title": "Qabul qilish vaqtini qisqartiring",
            "text": f"O‘rtacha qabul qilish vaqti {avg_accept_minutes} daqiqa. Ichki reglament va navbatchilik jadvalini qayta ko‘rib chiqish foydali.",
        })
    if not ai_recommendations:
        ai_recommendations.append({
            "level": "success",
            "title": "Operatsion holat barqaror",
            "text": "Hozircha kritik kechikish yoki navbat aniqlanmadi. Joriy ish sur’atini saqlash tavsiya etiladi.",
        })

    resolved_count = status_counts_global.get("resolved", 0)
    resolution_rate = round((resolved_count / total_count) * 100, 1) if total_count else 0
    sla_compliance_rate = round(((total_count - overdue_count) / total_count) * 100, 1) if total_count else 100

    # ---- Status options (sizdagi choice/label'ga mos) ----
    # Agar Report modelida status choices bo'lsa:
    status_options = getattr(Report, "STATUS_CHOICES", None) or getattr(Report, "status_choices", None)

    # fallback: modeldan choices olib ketamiz
    if not status_options:
        try:
            status_options = Report._meta.get_field("status").choices
        except Exception:
            status_options = [
                ("new", "Yangi"),
                ("sent", "Yuborildi"),
                ("read", "O‘qildi"),
                ("accepted", "Qabul qilindi"),
                ("assigned", "Biriktirildi"),
                ("in_progress", "Jarayonda"),
                ("resolved", "Hal qilingan"),
                ("rejected", "Rad etilgan"),
                ("redirected", "Yo‘naltirilgan"),
            ]

    # ---- Points (Leaflet uchun) ----
    points = []
    for r in reports:
        # status label (agar get_status_uz bo'lsa ishlatamiz, bo'lmasa display)
        if hasattr(r, "get_status_uz"):
            status_label = r.get_status_uz()
        else:
            try:
                status_label = r.get_status_display()
            except Exception:
                status_label = r.status

        u = r.user
        points.append(
            {
                "id": str(r.id),
                "lat": float(r.latitude) if r.latitude is not None else None,
                "lng": float(r.longitude) if r.longitude is not None else None,
                "status": r.status,
                "status_label": status_label,
                "description": r.description or "",
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "org": org.name,

                "user_username": getattr(u, "username", "") if u else "",
                "user_full_name": (f"{getattr(u,'first_name','') or ''} {getattr(u,'last_name','') or ''}").strip() if u else "",
                "user_phone": getattr(u, "phone_number", "") if u else "",
                "user": getattr(u, "username", "") if u else "",
            }
        )

    # ---- Charts ----
    # Status chart (labels/values) - filtered holat bo'yicha
    chart_status_labels = [lbl for key, lbl in status_options]
    chart_status_values_filtered = [status_counts_global.get(key, 0) for key, _lbl in status_options]

    # 7 kunlik trend
    days = []
    day_labels = []
    for i in range(6, -1, -1):
        d = today_start - timedelta(days=i)
        days.append(d)
        day_labels.append(d.strftime("%d/%m"))

    day_values = []
    for d in days:
        d2 = d + timedelta(days=1)
        day_values.append(reports.filter(created_at__gte=d, created_at__lt=d2).count())

    context = {
        "org": org,

        "q": q,
        "selected_statuses": selected_statuses,
        "status_options": status_options,

        "total_count": total_count,
        "today_count": today_count,
        "week_count": week_count,
        "overdue_count": overdue_count,
        "pending_confirmation_count": pending_confirmation_count,
        "resolved_today_count": resolved_today_count,
        "avg_accept_minutes": avg_accept_minutes,
        "avg_execution_minutes": avg_execution_minutes,
        "avg_total_minutes": avg_total_minutes,
        "status_counts_global": status_counts_global,
        "top_workers": top_workers,
        "urgent_assignments": urgent_assignments,
        "ai_recommendations": ai_recommendations,
        "resolution_rate": resolution_rate,
        "sla_compliance_rate": sla_compliance_rate,

        "points": json.dumps(points, ensure_ascii=False),

        "chart_status_labels": json.dumps(chart_status_labels, ensure_ascii=False),
        "chart_status_values_filtered": json.dumps(chart_status_values_filtered, ensure_ascii=False),
        "chart_days_labels": json.dumps(day_labels, ensure_ascii=False),
        "chart_days_values": json.dumps(day_values, ensure_ascii=False),
    }
    return render(request, "organization_admin/dashboard.html", context)


@login_required
def worker_tasks(request):
    membership = (
        OrganizationMember.objects.filter(user=request.user)
        .select_related("organization")
        .first()
    )
    if not membership:
        return HttpResponseForbidden("Siz tashkilot xodimi emassiz")

    base_assignments = (
        ReportAssignment.objects.filter(
            organization=membership.organization,
            assigned_to=request.user,
        )
        .select_related("report", "report__user", "organization")
        .order_by("-assigned_at")
    )

    period = (request.GET.get("period") or "all").strip().lower()
    task_filter = (request.GET.get("task_filter") or "active").strip().lower()
    q = (request.GET.get("q") or "").strip()
    today = timezone.localdate()
    assignments = base_assignments

    if period == "day":
        assignments = assignments.filter(assigned_at__date=today)
    elif period == "week":
        assignments = assignments.filter(assigned_at__date__gte=today - timedelta(days=6))
    elif period == "month":
        assignments = assignments.filter(assigned_at__year=today.year, assigned_at__month=today.month)
    elif period == "year":
        assignments = assignments.filter(assigned_at__year=today.year)

    now = timezone.now()
    if task_filter == "resolved":
        assignments = assignments.filter(report__status="resolved")
    elif task_filter == "in_progress":
        assignments = assignments.filter(report__status="in_progress")
    elif task_filter == "pending":
        assignments = assignments.filter(report__status="pending_confirmation")
    elif task_filter == "overdue":
        assignments = assignments.filter(deadline_at__lt=now).exclude(report__status="resolved")
    elif task_filter == "unfinished":
        assignments = assignments.exclude(report__status="resolved").filter(deadline_at__lt=now)
    elif task_filter == "all":
        pass
    else:
        assignments = assignments.exclude(report__status="resolved")
        task_filter = "active"

    if q:
        assignments = assignments.filter(
            Q(report__title__icontains=q)
            | Q(report__description__icontains=q)
            | Q(report__user__first_name__icontains=q)
            | Q(report__user__last_name__icontains=q)
            | Q(report__user__phone_number__icontains=q)
        )

    points = []
    for item in assignments:
        report = item.report
        if report.latitude is None or report.longitude is None:
            continue
        points.append({
            "id": str(report.id),
            "lat": float(report.latitude),
            "lng": float(report.longitude),
            "status": report.status,
            "status_label": report.get_status_uz(),
            "description": report.description,
            "citizen_name": report.user.get_full_name() or report.user.username,
            "citizen_phone": report.user.phone_number or "",
            "deadline": timezone.localtime(item.deadline_at).strftime("%d.%m.%Y %H:%M") if item.deadline_at else None,
            "detail_url": f"/org-admin/reports/{report.id}/",
        })

    active_qs = base_assignments.exclude(report__status="resolved")
    context = {
        "org": membership.organization,
        "assignments": assignments,
        "points": json.dumps(points, ensure_ascii=False),
        "selected_period": period,
        "selected_filter": task_filter,
        "q": q,
        "filtered_count": assignments.count(),
        "total_count": base_assignments.count(),
        "active_count": active_qs.count(),
        "resolved_count": base_assignments.filter(report__status="resolved").count(),
        "overdue_count": active_qs.filter(deadline_at__lt=now).count(),
        "in_progress_count": base_assignments.filter(report__status="in_progress").count(),
        "pending_count": base_assignments.filter(report__status="pending_confirmation").count(),
        "day_count": base_assignments.filter(assigned_at__date=today).count(),
        "week_count": base_assignments.filter(assigned_at__date__gte=today - timedelta(days=6)).count(),
        "month_count": base_assignments.filter(assigned_at__year=today.year, assigned_at__month=today.month).count(),
        "year_count": base_assignments.filter(assigned_at__year=today.year).count(),
    }
    return render(request, "organization_admin/worker_tasks.html", context)


@login_required
def worker_resolved(request):
    membership = OrganizationMember.objects.filter(user=request.user).select_related("organization").first()
    if not membership:
        return HttpResponseForbidden("Siz tashkilot xodimi emassiz")
    assignments = (ReportAssignment.objects.filter(
        organization=membership.organization, assigned_to=request.user, report__status="resolved"
    ).select_related("report", "report__user", "organization").order_by("-report__resolved_at", "-assigned_at"))
    q = (request.GET.get("q") or "").strip()
    if q:
        assignments = assignments.filter(Q(report__description__icontains=q) | Q(report__title__icontains=q))
    return render(request, "organization_admin/worker_resolved.html", {
        "org": membership.organization, "assignments": assignments, "q": q, "total_count": assignments.count()
    })
