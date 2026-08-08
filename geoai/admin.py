from django.contrib import admin
from .models import ComplaintAnalysis


@admin.register(ComplaintAnalysis)
class ComplaintAnalysisAdmin(admin.ModelAdmin):
    list_display = (
        "report", "predicted_category", "classifier_confidence",
        "priority_index", "priority_level", "cluster_label", "risk_index",
    )
    list_filter = ("priority_level", "predicted_category", "risk_level")
    search_fields = ("report__description", "predicted_category")
