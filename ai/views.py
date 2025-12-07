from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from .services.analyzer import ExpenseAIAnalyzer


# ai/views.py

class AIAnalysisView(LoginRequiredMixin, TemplateView):
    template_name = "ai/analysis.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # значения по умолчанию, чтобы шаблон не падал при GET
        ctx.setdefault("question", "")
        ctx.setdefault("answers", [])
        return ctx

    def post(self, request, *args, **kwargs):
        question = (request.POST.get("question") or "").strip()
        analyzer = ExpenseAIAnalyzer(request.user)
        answers = analyzer.answer_question(question)

        ctx = {
            "question": question,
            "answers": answers,
        }
        return self.render_to_response(ctx)
