from __future__ import annotations

from django.shortcuts import redirect

from .portal_views import public_portal


def smart_home(request):
    """
    SmartGeoAI unified entry point.

    Anonymous:
        public SmartGeoAI portal.

    Authenticated:
        preserves the existing operational dashboard flow.
    """
    if not request.user.is_authenticated:
        return public_portal(request)

    # Keep role-specific operational flows intact.
    try:
        membership = request.user.organization_memberships.first()
        role = getattr(membership, "role", None)
    except Exception:
        role = None

    if request.user.is_superuser:
        return redirect("dashboard:admin_home")

    if role == "staff" or getattr(request.user, "user_type", None) == "EXECUTOR":
        return redirect("dashboard:worker_tasks")

    if getattr(request.user, "user_type", None) == "DISPATCHER":
        return redirect("dashboard:org-dashboard")

    return redirect("dashboard:admin_home")
