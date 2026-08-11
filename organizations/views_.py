from rest_framework import generics, permissions
from rest_framework.pagination import PageNumberPagination
from .models import Organization
from .serializers import OrganizationListSerializer

class OrgPagination(PageNumberPagination):
    page_size = 8                # keyboard uchun qulay
    page_size_query_param = "page_size"
    max_page_size = 50

class OrganizationListApiView(generics.ListAPIView):
    serializer_class = OrganizationListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = OrgPagination

    def get_queryset(self):
        qs = Organization.objects.all().order_by("name")
        # agar sizda is_active bo‘lsa:
        # qs = qs.filter(is_active=True)
        return qs

from django.contrib.auth import authenticate
from django.utils import timezone
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from reports.models import ReportAssignment
from .models import OrganizationMember, TelegramStaffLink


class TelegramStaffLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""
        telegram_id = request.data.get("telegram_id")
        if not username or not password or not telegram_id:
            return Response({"detail": "Login, parol va Telegram ID majburiy."}, status=400)

        user = authenticate(request=request, username=username, password=password)
        if not user or not user.is_active:
            return Response({"detail": "Login yoki parol noto‘g‘ri."}, status=401)

        membership = OrganizationMember.objects.filter(user=user).select_related("organization").first()
        if not membership:
            return Response({"detail": "Bu foydalanuvchi tashkilot xodimi emas."}, status=403)

        # Bitta Telegram hisobi faqat bitta faol xodim profiliga ulanadi.
        TelegramStaffLink.objects.filter(telegram_id=telegram_id).exclude(user=user).delete()
        link, _ = TelegramStaffLink.objects.update_or_create(
            user=user,
            defaults={"telegram_id": int(telegram_id), "is_active": True},
        )
        link.last_login_at = timezone.now()
        link.save(update_fields=["last_login_at"])

        return Response({
            "tokens": user.token(),
            "user": {
                "id": str(user.id),
                "username": user.username,
                "full_name": user.get_full_name() or user.username,
            },
            "organization": {"id": membership.organization_id, "name": membership.organization.name},
            "role": membership.role,
        })


def _staff_assignments_queryset(user):
    """Bot ro'yxati va geoxarita uchun yagona, xavfsiz queryset."""
    membership = (
        OrganizationMember.objects
        .filter(user=user)
        .select_related("organization")
        .first()
    )
    if not membership:
        return None, None

    qs = (
        ReportAssignment.objects
        .filter(assigned_to=user)
        .select_related("report", "report__user", "organization")
        .order_by("-assigned_at")
    )
    return membership, qs


def _filter_staff_assignments(qs, period="all", task_filter="all"):
    period = (period or "all").lower()
    task_filter = (task_filter or "all").lower()
    today = timezone.localdate()

    if period == "day":
        qs = qs.filter(assigned_at__date=today)
    elif period == "week":
        qs = qs.filter(assigned_at__date__gte=today - timedelta(days=6))
    elif period == "month":
        qs = qs.filter(assigned_at__year=today.year, assigned_at__month=today.month)
    elif period == "year":
        qs = qs.filter(assigned_at__year=today.year)

    if task_filter == "active":
        qs = qs.exclude(report__status="resolved")
    elif task_filter == "resolved":
        qs = qs.filter(report__status="resolved")
    elif task_filter == "in_progress":
        qs = qs.filter(report__status="in_progress")
    elif task_filter == "pending":
        qs = qs.filter(report__status="pending_confirmation")
    elif task_filter == "assigned":
        qs = qs.filter(report__status="assigned")
    elif task_filter in {"overdue", "unfinished"}:
        qs = qs.filter(deadline_at__lt=timezone.now()).exclude(report__status="resolved")
    return qs


class TelegramStaffTasksView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        membership, qs = _staff_assignments_queryset(request.user)
        if not membership:
            return Response({"detail": "Siz tashkilot xodimi emassiz."}, status=403)

        period = (request.query_params.get("period") or "all").lower()
        task_filter = (request.query_params.get("status") or "all").lower()
        qs = _filter_staff_assignments(qs, period, task_filter)

        items = []
        for a in qs[:100]:
            r = a.report
            items.append({
                "assignment_id": a.id,
                "report_id": str(r.id),
                "title": r.title,
                "description": r.description,
                "status": r.status,
                "status_label": r.get_status_uz(),
                "assigned_at": a.assigned_at.isoformat(),
                "deadline_at": a.deadline_at.isoformat() if a.deadline_at else None,
                "latitude": float(r.latitude) if r.latitude is not None else None,
                "longitude": float(r.longitude) if r.longitude is not None else None,
            })
        return Response({"period": period, "status": task_filter, "count": qs.count(), "results": items})


class TelegramStaffTaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, report_id):
        assignment = ReportAssignment.objects.select_related("report", "organization").filter(
            report_id=report_id, assigned_to=request.user
        ).order_by("-assigned_at").first()
        if not assignment:
            return Response({"detail": "Bu murojaat sizga biriktirilmagan."}, status=403)
        r = assignment.report
        citizen_name = r.user.get_full_name() or r.user.username
        return Response({
            "report_id": str(r.id), "title": r.title, "description": r.description,
            "status": r.status, "status_label": r.get_status_uz(),
            "organization": assignment.organization.name,
            "citizen_name": citizen_name,
            "citizen_phone": r.user.phone_number or "",
            "assigned_at": assignment.assigned_at.isoformat(),
            "deadline_at": assignment.deadline_at.isoformat() if assignment.deadline_at else None,
            "completion_note": r.completion_note,
            "latitude": float(r.latitude) if r.latitude is not None else None,
            "longitude": float(r.longitude) if r.longitude is not None else None,
        })

from rest_framework.parsers import MultiPartParser, FormParser
from reports.models import ReportWorkEvidence
from reports.choices import ReportStatus
from utils.telegram import send_telegram_message


def _staff_assignment(user, report_id):
    return ReportAssignment.objects.select_related(
        "report", "report__user", "organization"
    ).filter(report_id=report_id, assigned_to=user).order_by("-assigned_at").first()


class TelegramStaffTaskStartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, report_id):
        assignment = _staff_assignment(request.user, report_id)
        if not assignment:
            return Response({"detail": "Bu murojaat sizga biriktirilmagan."}, status=403)
        report = assignment.report
        if report.status not in (ReportStatus.ASSIGNED, ReportStatus.REOPENED):
            return Response({"detail": "Ushbu murojaatda ishni boshlash mumkin emas."}, status=409)
        now = timezone.now()
        assignment.started_at = assignment.started_at or now
        assignment.save(update_fields=["started_at"])
        report.work_started_at = report.work_started_at or now
        report.status = ReportStatus.IN_PROGRESS
        report.save(update_fields=["work_started_at", "status", "updated_at"])
        if getattr(report.user, "telegram_id", None):
            send_telegram_message(
                report.user.telegram_id,
                f"▶️ Murojaatingiz bo‘yicha xodim ishni boshladi.\nTashkilot: {assignment.organization.name}",
            )
        return Response({"detail": "Ish boshlandi.", "status": report.status})


class TelegramStaffTaskCompleteView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, report_id):
        assignment = _staff_assignment(request.user, report_id)
        if not assignment:
            return Response({"detail": "Bu murojaat sizga biriktirilmagan."}, status=403)
        report = assignment.report
        if report.status != ReportStatus.IN_PROGRESS:
            return Response({"detail": "Avval ishni boshlash kerak."}, status=409)
        note = (request.data.get("completion_note") or "").strip()
        if len(note) < 10:
            return Response({"detail": "Bajarilgan ish haqida kamida 10 ta belgi yozing."}, status=400)
        files = request.FILES.getlist("evidence_files")
        if not files:
            return Response({"detail": "Kamida bitta foto yoki dalil fayli yuboring."}, status=400)
        now = timezone.now()
        for uploaded in files:
            if uploaded.size > 15 * 1024 * 1024:
                return Response({"detail": f"{uploaded.name}: 15 MB dan katta."}, status=400)
            ReportWorkEvidence.objects.create(
                report=report,
                assignment=assignment,
                uploaded_by=request.user,
                file=uploaded,
                original_name=uploaded.name,
                mime_type=getattr(uploaded, "content_type", "") or "",
                file_size=uploaded.size,
            )
        assignment.started_at = assignment.started_at or now
        assignment.completed_at = now
        assignment.completion_note = note
        assignment.save(update_fields=["started_at", "completed_at", "completion_note"])
        report.work_started_at = report.work_started_at or now
        report.work_completed_at = now
        report.completion_note = note
        report.status = ReportStatus.PENDING_CONFIRMATION
        report.save(update_fields=[
            "work_started_at", "work_completed_at", "completion_note", "status", "updated_at"
        ])
        if getattr(report.user, "telegram_id", None):
            send_telegram_message(
                report.user.telegram_id,
                "✅ Murojaatingiz bo‘yicha ish bajarildi. Natijani botdagi “Hal bo‘ldi” tugmasi orqali tasdiqlang yoki rad eting.",
            )
        return Response({"detail": "Ish fuqaro tasdig‘iga yuborildi.", "status": report.status})


from django.core import signing
from django.shortcuts import render
from django.urls import reverse
from django.contrib.auth import get_user_model

class TelegramStaffMapLinkView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        membership, qs = _staff_assignments_queryset(request.user)
        if not membership:
            return Response({"detail": "Siz tashkilot xodimi emassiz."}, status=403)

        # Telegram orqali bog'langan aynan shu xodim profilini imzolaymiz.
        token = signing.dumps(
            {"uid": str(request.user.id)},
            salt="staff-mobile-map",
            compress=True,
        )
        path = reverse("staff-mobile-map") + "?token=" + token + "&status=all&period=all"
        return Response({"url": request.build_absolute_uri(path), "assignment_count": qs.count()})


def staff_mobile_map(request):
    token = request.GET.get("token", "")
    try:
        payload = signing.loads(token, salt="staff-mobile-map", max_age=60 * 60 * 12)
        user = get_user_model().objects.get(id=payload["uid"], is_active=True)
    except Exception:
        return render(
            request,
            "webapp/staff_map.html",
            {"invalid": True, "points": "[]"},
            status=403,
        )

    membership, base_qs = _staff_assignments_queryset(user)
    if not membership:
        return render(
            request,
            "webapp/staff_map.html",
            {"invalid": True, "points": "[]"},
            status=403,
        )

    period = (request.GET.get("period") or "all").lower()
    st = (request.GET.get("status") or "all").lower()
    qs = _filter_staff_assignments(base_qs, period, st)

    import json

    points = []
    without_location = 0
    status_counts = {
        "all": qs.count(),
        "assigned": qs.filter(report__status="assigned").count(),
        "in_progress": qs.filter(report__status="in_progress").count(),
        "pending_confirmation": qs.filter(report__status="pending_confirmation").count(),
        "resolved": qs.filter(report__status="resolved").count(),
    }

    for assignment in qs:
        report = assignment.report
        if report.latitude is None or report.longitude is None:
            without_location += 1
            continue

        points.append({
            "id": str(report.id),
            "lat": float(report.latitude),
            "lng": float(report.longitude),
            "status": report.status,
            "status_label": report.get_status_uz(),
            "title": report.title or "Murojaat",
            "description": report.description or "",
            "phone": report.user.phone_number or "",
            "name": report.user.get_full_name() or report.user.username,
            "deadline": (
                timezone.localtime(assignment.deadline_at).strftime("%d.%m.%Y %H:%M")
                if assignment.deadline_at else "-"
            ),
        })

    return render(
        request,
        "webapp/staff_map.html",
        {
            "invalid": False,
            "points": json.dumps(points, ensure_ascii=False),
            "token": token,
            "period": period,
            "status": st,
            "count": len(points),
            "assignment_count": qs.count(),
            "without_location": without_location,
            "status_counts": status_counts,
        },
    )

