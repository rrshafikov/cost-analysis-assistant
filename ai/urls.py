from django.urls import path
from .views import AIAnalysisView

urlpatterns = [
    path("", AIAnalysisView.as_view(), name="ai_analysis"),
]
