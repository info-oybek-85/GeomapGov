from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("organizations", "0004_organizationpredictionfeedback"),
    ]

    operations = [
        migrations.AddField(
            model_name="organizationpredictionfeedback",
            name="expert_status",
            field=models.CharField(
                choices=[
                    ("pending", "Tekshirilmagan"),
                    ("verified", "Tasdiqlangan"),
                    ("corrected", "Tuzatilgan"),
                    ("rejected", "Rad etilgan"),
                ],
                db_index=True,
                default="pending",
                max_length=16,
            ),
        ),
        migrations.AddField(model_name="organizationpredictionfeedback", name="expert_primary_problem", field=models.CharField(blank=True, default="", max_length=100)),
        migrations.AddField(model_name="organizationpredictionfeedback", name="expert_secondary_problems", field=models.JSONField(blank=True, default=list)),
        migrations.AddField(model_name="organizationpredictionfeedback", name="expert_supporting_organizations", field=models.JSONField(blank=True, default=list)),
        migrations.AddField(
            model_name="organizationpredictionfeedback",
            name="expert_priority",
            field=models.CharField(
                blank=True,
                choices=[("critical", "Kritik"), ("high", "Yuqori"), ("medium", "O‘rta"), ("low", "Past")],
                default="",
                max_length=12,
            ),
        ),
        migrations.AddField(model_name="organizationpredictionfeedback", name="expert_note", field=models.TextField(blank=True, default="")),
        migrations.AddField(model_name="organizationpredictionfeedback", name="reviewed_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(
            model_name="organizationpredictionfeedback",
            name="expert_primary_organization",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="expert_primary_feedbacks", to="organizations.organization"),
        ),
        migrations.AddField(
            model_name="organizationpredictionfeedback",
            name="reviewed_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_organization_predictions", to=settings.AUTH_USER_MODEL),
        ),
    ]
