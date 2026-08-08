# Generated manually for GeoAI Build 1
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    initial = True
    dependencies = [("reports", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="ComplaintAnalysis",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateField(auto_now_add=True)),
                ("updated_at", models.DateField(auto_now=True)),
                ("predicted_category", models.CharField(blank=True, default="", max_length=80)),
                ("classifier_confidence", models.FloatField(default=0.0)),
                ("spatial_density", models.FloatField(default=0.0)),
                ("recurrence_frequency", models.FloatField(default=0.0)),
                ("temporal_relevance", models.FloatField(default=0.0)),
                ("severity_weight", models.FloatField(default=0.0)),
                ("neighbor_influence", models.FloatField(default=0.0)),
                ("priority_index", models.FloatField(db_index=True, default=0.0)),
                ("priority_level", models.CharField(choices=[("high", "Yuqori"), ("medium", "O‘rta"), ("low", "Past")], db_index=True, default="low", max_length=10)),
                ("cluster_label", models.IntegerField(blank=True, db_index=True, null=True)),
                ("weighted_kde", models.FloatField(default=0.0)),
                ("risk_index", models.FloatField(db_index=True, default=0.0)),
                ("risk_level", models.CharField(blank=True, default="", max_length=10)),
                ("algorithm_version", models.CharField(default="geoai-1.0", max_length=30)),
                ("calculated_at", models.DateTimeField(auto_now=True)),
                ("report", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="geoai_analysis", to="reports.report")),
            ],
            options={"ordering": ("-priority_index",)},
        )
    ]
