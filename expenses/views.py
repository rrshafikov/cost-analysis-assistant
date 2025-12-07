# expenses/views.py
from datetime import date, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    TemplateView,
    ListView,
    CreateView,
    UpdateView,
    DeleteView,
)

from .forms import ExpenseForm
from .models import Expense


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "expenses/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        expenses = Expense.objects.filter(user=self.request.user)

        total = expenses.aggregate(total=Sum("amount"))["total"] or 0

        by_category = (
            expenses
            .values("category__name")
            .annotate(total=Sum("amount"))
            .order_by("-total")
        )

        context["total"] = total
        context["by_category"] = by_category
        return context


class ExpenseListView(LoginRequiredMixin, ListView):
    model = Expense
    template_name = "expenses/expense_list.html"
    context_object_name = "expenses"

    def get_queryset(self):
        qs = Expense.objects.filter(user=self.request.user)

        from_date = self.request.GET.get("from_date")
        to_date = self.request.GET.get("to_date")

        if from_date:
            qs = qs.filter(date__gte=from_date)
        if to_date:
            qs = qs.filter(date__lte=to_date)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        expenses = context["expenses"]
        total = expenses.aggregate(total=Sum("amount"))["total"] or 0

        context["total"] = total
        context["from_date"] = self.request.GET.get("from_date") or ""
        context["to_date"] = self.request.GET.get("to_date") or ""
        return context


class ExpenseCreateView(LoginRequiredMixin, CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = "expenses/expense_form.html"
    success_url = reverse_lazy("expense_list")

    def form_valid(self, form):
        expense = form.save(commit=False)
        expense.user = self.request.user
        expense.save()
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Добавить расход"
        return context


class ExpenseUpdateView(LoginRequiredMixin, UpdateView):
    model = Expense
    form_class = ExpenseForm
    template_name = "expenses/expense_form.html"
    success_url = reverse_lazy("expense_list")

    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Редактировать расход"
        return context


class ExpenseDeleteView(LoginRequiredMixin, DeleteView):
    model = Expense
    template_name = "expenses/expense_confirm_delete.html"
    success_url = reverse_lazy("expense_list")

    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user)


class AIAnalysisView(LoginRequiredMixin, View):
    template_name = "expenses/ai_analysis.html"

    def get(self, request, *args, **kwargs):
        days_raw = request.GET.get("days", "30")
        try:
            days = int(days_raw)
            if days <= 0:
                days = 30
        except ValueError:
            days = 30

        start_date = date.today() - timedelta(days=days)

        qs = (
            Expense.objects
            .filter(user=request.user, date__gte=start_date)
            .select_related("category")
        )

        total = qs.aggregate(total=Sum("amount"))["total"] or 0
        by_category = (
            qs.values("category__name")
            .annotate(total=Sum("amount"))
            .order_by("-total")
        )

        pseudo_ai_report_lines = [
            f"Период: последние {days} дней.",
            f"Всего расходов за период: {total}.",
        ]

        if by_category:
            top_cat = by_category[0]
            cat_name = top_cat["category__name"] or "Без категории"
            pseudo_ai_report_lines.append(
                f"Больше всего вы тратите в категории: {cat_name} ({top_cat['total']} единиц)."
            )
            pseudo_ai_report_lines.append(
                "Рекомендация: посмотрите, какие траты в этой категории можно оптимизировать."
            )
        else:
            pseudo_ai_report_lines.append(
                "За выбранный период расходов не найдено."
            )

        ai_report = "\n".join(pseudo_ai_report_lines)

        context = {
            "days": days,
            "total": total,
            "count": qs.count(),
            "ai_report": ai_report,
        }
        return self._render(context)

    def _render(self, context):
        from django.shortcuts import render  # импорт локально, чтобы не засорять глобальный неймспейс

        return render(self.request, self.template_name, context)
