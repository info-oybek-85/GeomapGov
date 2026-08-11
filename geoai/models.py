from django.db import models
from utils.models import BaseModel


class ComplaintAnalysis(BaseModel):
    """4 ta ilmiy yangilik natijalarini bitta yozuvda saqlovchi tahlil modeli."""

    class PriorityLevel(models.TextChoices):
        HIGH = "high", "Yuqori"
        MEDIUM = "medium", "O‘rta"
        LOW = "low", "Past"

    report = models.OneToOneField(
        "reports.Report",
        on_delete=models.CASCADE,
        related_name="geoai_analysis",
    )

    # 1-ilmiy yangilik: klassifikatsiya
    predicted_category = models.CharField(max_length=80, blank=True, default="")
    classifier_confidence = models.FloatField(default=0.0)

    # 2-ilmiy yangilik: ustuvorlik komponentlari
    spatial_density = models.FloatField(default=0.0)
    recurrence_frequency = models.FloatField(default=0.0)
    temporal_relevance = models.FloatField(default=0.0)
    severity_weight = models.FloatField(default=0.0)
    neighbor_influence = models.FloatField(default=0.0)
    priority_index = models.FloatField(default=0.0, db_index=True)
    priority_level = models.CharField(
        max_length=10,
        choices=PriorityLevel.choices,
        default=PriorityLevel.LOW,
        db_index=True,
    )

    # 3-ilmiy yangilik uchun tayyor maydonlar
    cluster_label = models.IntegerField(null=True, blank=True, db_index=True)
    weighted_kde = models.FloatField(default=0.0)
    risk_index = models.FloatField(default=0.0, db_index=True)
    risk_level = models.CharField(max_length=10, blank=True, default="")

    algorithm_version = models.CharField(max_length=30, default="geoai-1.0")
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-priority_index",)
        verbose_name = "GeoAI tahlil natijasi"
        verbose_name_plural = "GeoAI tahlil natijalari"

    def __str__(self):
        return f"{self.report_id}: {self.predicted_category} ({self.priority_index:.3f})"
