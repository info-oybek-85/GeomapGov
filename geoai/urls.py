from django.urls import path
from . import views
from . import evaluation_views

app_name = "geoai"

urlpatterns = [
    path("", views.analytics_dashboard, name="analytics"),
    path("system-evaluation/", evaluation_views.system_evaluation, name="system_evaluation"),
    path("system-evaluation/kfold/", evaluation_views.run_kfold, name="run_kfold"),
    path("model/retrain/", views.retrain_model, name="retrain_model"),
    path("reports/model.pdf", views.model_results_pdf, name="model_results_pdf"),
    path("reports/system.pdf", views.system_results_pdf, name="system_results_pdf"),
    path("export/priority.csv", views.priority_export_csv, name="priority_export_csv"),
    path("api/results/", views.analytics_json, name="results_json"),
    path("api/smart-online/", views.smart_online_json, name="smart_online_json"),
    path("export/smart-online.csv", views.smart_export_csv, name="smart_export_csv"),
]
