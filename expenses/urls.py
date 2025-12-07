# expenses/urls.py
from django.urls import path

from .views import (
    DashboardView,
    ExpenseListView,
    ExpenseCreateView,
    ExpenseUpdateView,
    ExpenseDeleteView,
    AIAnalysisView,
)

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),

    path("expenses/", ExpenseListView.as_view(), name="expense_list"),
    path("expenses/add/", ExpenseCreateView.as_view(), name="expense_create"),
    path("expenses/<int:pk>/edit/", ExpenseUpdateView.as_view(), name="expense_update"),
    path("expenses/<int:pk>/delete/", ExpenseDeleteView.as_view(), name="expense_delete"),

    path("ai/analysis/", AIAnalysisView.as_view(), name="ai_analysis"),
]
