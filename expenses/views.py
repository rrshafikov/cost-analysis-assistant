# expenses/views.py
from datetime import date, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    FormView,
    TemplateView,
    ListView,
    CreateView,
    UpdateView,
    DeleteView,
)

from .forms import ExpenseForm, ExpenseCategory
from .models import Expense

from django.utils import timezone

from .forms import ExpenseForm, StatementImportForm
from .services.importers import import_tbank_csv, import_sber_pdf


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "expenses/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = filtered_expenses_queryset(self.request)

        # по умолчанию — последние 30 дней
        if not self.request.GET.get("date_from") and not self.request.GET.get("date_to"):
            today = timezone.now().date()
            qs = qs.filter(date__gte=today - timezone.timedelta(days=30))

        summary = qs.aggregate(
            total=Sum("amount"),
            count=Count("id"),
        )

        total = summary["total"] or 0
        count = summary["count"] or 0

        first = qs.order_by("date").first()
        last = qs.order_by("-date").first()
        if first and last:
            days_span = (last.date - first.date).days + 1
            avg_per_day = total / days_span if days_span > 0 else total
        else:
            avg_per_day = 0

        # для фильтров
        ctx["available_banks"] = (
            Expense.objects.filter(user=self.request.user)
            .exclude(bank="")
            .values_list("bank", flat=True)
            .distinct()
        )
        ctx["available_currencies"] = (
            Expense.objects.filter(user=self.request.user)
            .values_list("currency", flat=True)
            .distinct()
        )
        ctx["categories"] = ExpenseCategory.objects.filter(user=self.request.user)

        ctx["total"] = total
        ctx["count"] = count
        ctx["avg_per_day"] = avg_per_day
        ctx["has_expenses"] = qs.exists()

        return ctx


class ExpenseListView(LoginRequiredMixin, ListView):
    model = Expense
    template_name = "expenses/expense_list.html"
    context_object_name = "expenses"
    paginate_by = 20

    def get_queryset(self):
        return filtered_expenses_queryset(self.request)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["available_banks"] = (
            Expense.objects.filter(user=self.request.user)
            .exclude(bank="")
            .values_list("bank", flat=True)
            .distinct()
        )
        ctx["available_currencies"] = (
            Expense.objects.filter(user=self.request.user)
            .values_list("currency", flat=True)
            .distinct()
        )
        ctx["categories"] = ExpenseCategory.objects.filter(user=self.request.user)
        return ctx


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


class StatementImportView(LoginRequiredMixin, FormView):
    template_name = "expenses/statement_import.html"
    form_class = StatementImportForm
    success_url = reverse_lazy("expense_list")

    def form_valid(self, form):
        uploaded = form.cleaned_data["file"]
        source = form.cleaned_data["source"]

        if source == "tbank_csv":
            created, total = import_tbank_csv(uploaded, self.request.user)
        else:
            created, total = import_sber_pdf(uploaded, self.request.user)

        messages.success(
            self.request,
            f"Imported {created} expenses, total amount: {total}.",
        )
        return super().form_valid(form)


def filtered_expenses_queryset(request):
    qs = Expense.objects.filter(user=request.user).select_related("category")

    bank = request.GET.get("bank")
    if bank:
        qs = qs.filter(bank=bank)

    currency = request.GET.get("currency")
    if currency:
        qs = qs.filter(currency=currency)

    category_id = request.GET.get("category")
    if category_id:
        qs = qs.filter(category_id=category_id)

    date_from = request.GET.get("date_from")
    if date_from:
        qs = qs.filter(date__gte=date_from)

    date_to = request.GET.get("date_to")
    if date_to:
        qs = qs.filter(date__lte=date_to)

    return qs
