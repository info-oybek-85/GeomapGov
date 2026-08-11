from django.urls import path
from .views import (
    OrganizationListApiView,
    TelegramStaffLoginView,
    TelegramStaffTasksView,
    TelegramStaffTaskDetailView,
    TelegramStaffTaskStartView,
    TelegramStaffTaskCompleteView,
    TelegramStaffMapLinkView,
    staff_mobile_map,
    OrganizationPredictionView,
    OrganizationPredictionFeedbackView,
)

urlpatterns = [
    path("organizations/", OrganizationListApiView.as_view(), name="org-list"),
    path("organizations/predict/", OrganizationPredictionView.as_view(), name="org-predict"),
    path("organizations/prediction-feedback/", OrganizationPredictionFeedbackView.as_view(), name="org-prediction-feedback"),
    path("staff/telegram-login/", TelegramStaffLoginView.as_view(), name="staff-telegram-login"),
    path("staff/tasks/", TelegramStaffTasksView.as_view(), name="staff-tasks"),
    path("staff/tasks/<uuid:report_id>/", TelegramStaffTaskDetailView.as_view(), name="staff-task-detail"),
    path("staff/tasks/<uuid:report_id>/start/", TelegramStaffTaskStartView.as_view(), name="staff-task-start"),
    path("staff/tasks/<uuid:report_id>/complete/", TelegramStaffTaskCompleteView.as_view(), name="staff-task-complete"),
    path("staff/map-link/", TelegramStaffMapLinkView.as_view(), name="staff-map-link"),
    path("staff/mobile-map/", staff_mobile_map, name="staff-mobile-map"),
]
