from django.db import models
from django.conf import settings


class Organization(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)
    organization_icon = models.ImageField(upload_to="organization_icons/", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class OrganizationMember(models.Model):
    ROLE_ADMIN = "admin"
    ROLE_STAFF = "staff"

    ROLE_CHOICES = (
        (ROLE_ADMIN, "Admin"),
        (ROLE_STAFF, "Staff"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_memberships"
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="members"
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_STAFF
    )

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "organization")

    def __str__(self):
        return f"{self.user} -> {self.organization} ({self.role})"


class TelegramStaffLink(models.Model):
    """Telegram hisobini tashkilot xodimi profiliga bog'laydi.

    User.telegram_id fuqaro bot identifikatsiyasi uchun saqlanadi. Ushbu alohida
    model xodim va fuqaro rollarining bir-biriga xalaqit bermasligini ta'minlaydi.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="telegram_staff_link",
    )
    telegram_id = models.BigIntegerField(unique=True)
    linked_at = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user} <-> Telegram {self.telegram_id}"


class OrganizationPredictionFeedback(models.Model):
    """ML tavsiyasi va foydalanuvchining yakuniy tanlovini saqlaydi."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="organization_prediction_feedbacks",
    )
    report = models.ForeignKey(
        "reports.Report",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="organization_prediction_feedbacks",
    )
    text = models.TextField()
    predicted_organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prediction_hits",
    )
    selected_organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prediction_selections",
    )
    confidence = models.FloatField(default=0.0)
    accepted = models.BooleanField(default=False)
    recommendations = models.JSONField(default=list, blank=True)
    matched_keywords = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


    EXPERT_PENDING = "pending"
    EXPERT_VERIFIED = "verified"
    EXPERT_CORRECTED = "corrected"
    EXPERT_REJECTED = "rejected"
    EXPERT_STATUS_CHOICES = (
        (EXPERT_PENDING, "Tekshirilmagan"),
        (EXPERT_VERIFIED, "Tasdiqlangan"),
        (EXPERT_CORRECTED, "Tuzatilgan"),
        (EXPERT_REJECTED, "Rad etilgan"),
    )

    PRIORITY_CHOICES = (
        ("critical", "Kritik"),
        ("high", "Yuqori"),
        ("medium", "O‘rta"),
        ("low", "Past"),
    )

    expert_status = models.CharField(
        max_length=16, choices=EXPERT_STATUS_CHOICES, default=EXPERT_PENDING, db_index=True
    )
    expert_primary_problem = models.CharField(max_length=100, blank=True, default="")
    expert_secondary_problems = models.JSONField(default=list, blank=True)
    expert_primary_organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="expert_primary_feedbacks",
    )
    expert_supporting_organizations = models.JSONField(default=list, blank=True)
    expert_priority = models.CharField(
        max_length=12, choices=PRIORITY_CHOICES, blank=True, default=""
    )
    expert_note = models.TextField(blank=True, default="")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_organization_predictions",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Prediction feedback #{self.pk}: {self.accepted}"
