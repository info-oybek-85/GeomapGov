from organizations.models import OrganizationMember


def user_permissions(request):
    """
    Template'larda foydalanish uchun user rollarini aniqlaydi.

    is_effective_org_admin:
        - user_type == "DISPATCHER" (legacy)
        - YOKI OrganizationMember role=admin bo'lsa
    """
    user = getattr(request, "user", None)
    is_effective_org_admin = False

    if user and user.is_authenticated and not user.is_superuser:
        user_type = (getattr(user, "user_type", "") or "").lower()
        if user_type == "dispatcher":
            is_effective_org_admin = True
        elif OrganizationMember.objects.filter(
            user=user, role__iexact=OrganizationMember.ROLE_ADMIN
        ).exists():
            is_effective_org_admin = True

    return {"is_effective_org_admin": is_effective_org_admin}
