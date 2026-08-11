from django.urls import path
from . import views, organization_admin
from . import platform_views
from . import lab_views
from . import portal_views
from . import entry_views
from organizations import expert_views
from django.contrib.auth.views import LogoutView

app_name = "dashboard"

urlpatterns = [
    path(
    "portal/research-data/",
    portal_views.public_research_data,
    name="public_research_data",
),
    path(
    "portal/analytics.csv",
    portal_views.public_analytics_csv,
    name="public_analytics_csv",
),
    path("portal/analytics-data/", portal_views.public_analytics_data, name="public_analytics_data",),
    
    path("portal/map-data/", portal_views.public_resolved_map_data, name="public_resolved_map_data",),
    
    # Unified public/private entry point.
    # path("", entry_views.smart_home, name="home"),

    # SmartGeoAI asosiy Public Portal
    path("", portal_views.public_portal, name="home"),
    
    # Existing admin dashboard kept under a stable internal URL.
    path("dashboard/", views.superadmin_dashboard, name="admin_home"),

    # Public portal can still be opened explicitly.
    path("portal/", portal_views.public_portal, name="public_portal"),

    path("platform-center/", platform_views.platform_center, name="platform_center"),
    path("gsor-center/", platform_views.gsor_center, name="gsor_center"),
    path("geoai-lab/", lab_views.geoai_lab, name="geoai_lab"),

    path("login/", views.sign_in, name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),

    path("shikoyatlar/", views.complaints_list, name="complaints"),
    path("organizations/", views.organizations_list, name="organizations"),
    path("organizations/<int:pk>/", views.organization_detail, name="organization_detail"),
    path("users/", views.users_list, name="users"),
    path("users/<uuid:pk>/", views.user_detail, name="user_detail"),
    path("shikoyatlar/<uuid:pk>/", views.report_detail, name="report_detail"),
    path("report/<uuid:pk>/", views.report_detail_json, name="report_detail_json"),

    path("org/", organization_admin.organization_admin_dashboard, name="org-dashboard"),
    path("org-admin/users/", organization_admin.org_users_list, name="org_users"),
    path("org-admin/reports/", views.org_reports_list, name="org_reports"),
    path("worker/tasks/", organization_admin.worker_tasks, name="worker_tasks"),
    path("worker/resolved/", organization_admin.worker_resolved, name="worker_resolved"),
    path("org-admin/reports/<uuid:pk>/", views.org_report_detail, name="org_report_detail"),

    path("expert-validation/", expert_views.expert_validation_queue, name="expert_validation_queue"),
    path("expert-validation/<int:pk>/", expert_views.expert_validation_detail, name="expert_validation_detail"),
]
