from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import reports.models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("reports", "0003_workflow_tracking"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReportWorkEvidence",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to=reports.models.execution_evidence_upload_path)),
                ("original_name", models.CharField(blank=True, default="", max_length=255)),
                ("mime_type", models.CharField(blank=True, default="", max_length=100)),
                ("file_size", models.BigIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("assignment", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="evidence", to="reports.reportassignment")),
                ("report", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="work_evidence", to="reports.report")),
                ("uploaded_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at",)},
        ),
    ]
