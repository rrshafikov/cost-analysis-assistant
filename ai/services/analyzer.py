# ai/services/analyzer.py
from collections import Counter
from datetime import date, timedelta

from django.db.models import Sum

from expenses.models import Expense


def make_insight(main: str, advice: str | None = None) -> dict:
    return {"main": main, "advice": advice}


class ExpenseAIAnalyzer:
    """
    Лёгкий "AI"-анализатор без внешних ML-зависимостей.
    Генерирует текстовые инсайты по расходам на русском + краткие советы.
    """

    def __init__(self, user):
        self.user = user

    # --- helpers ---

    def _qs(self):
        return Expense.objects.filter(user=self.user)

    # --- блоки инсайтов ---

    def overall_summary(self) -> dict:
        qs = self._qs()
        count = qs.count()
        total = qs.aggregate(total=Sum("amount"))["total"] or 0

        if not count:
            return make_insight(
                "У вас пока нет расходов. Импортируйте выписку или добавьте первую операцию вручную.",
                None,
            )

        first = qs.order_by("date").first()
        last = qs.order_by("-date").first()
        days = (last.date - first.date).days + 1 if first and last else 1
        avg = total / days if days > 0 else total

        advice = (
            "Подумайте, какой дневной бюджет для вас комфортен, "
            "и сравнивайте его с текущим средним расходом."
        )

        return make_insight(
            f"Всего зафиксировано {count} операций на сумму {total:.2f} RUB. "
            f"В среднем вы тратите около {avg:.2f} RUB в день.",
            advice,
        )

    def top_categories(self, n: int = 3) -> dict:
        qs = (
            self._qs()
            .values("category__name")
            .annotate(total=Sum("amount"))
            .order_by("-total")
        )

        if not qs:
            return make_insight("По категориям пока нет данных.", None)

        grand_total = sum((row["total"] or 0) for row in qs)
        parts: list[str] = []

        top_share = 0.0
        top_name = None

        for row in qs[:n]:
            name = row["category__name"] or "Без категории"
            cat_total = row["total"] or 0
            share = (cat_total / grand_total * 100) if grand_total else 0
            parts.append(
                f"Категория «{name}» — {cat_total:.2f} RUB "
                f"({share:.1f}% от общей суммы расходов)."
            )
            # запомним самую "тяжёлую" категорию
            if top_name is None:
                top_name = name
                top_share = share

        advice = None
        if top_name and top_share >= 50:
            advice = (
                f"Категория «{top_name}» занимает более половины всех расходов. "
                f"Попробуйте найти 1–2 крупные статьи внутри неё и уменьшить их хотя бы на 10–15%."
            )
        elif top_name and top_share >= 30:
            advice = (
                f"Категория «{top_name}» заметно выделяется по сумме. "
                f"Имеет смысл задать для неё месячной лимит и отслеживать его."
            )

        return make_insight(" ".join(parts), advice)

    def month_compare(self) -> dict:
        today = date.today()
        start_this = today.replace(day=1)

        prev_last = start_this - timedelta(days=1)
        start_prev = prev_last.replace(day=1)

        qs = self._qs()
        this_total = (
            qs.filter(date__gte=start_this).aggregate(total=Sum("amount"))["total"] or 0
        )
        prev_total = (
            qs.filter(date__gte=start_prev, date__lt=start_this)
            .aggregate(total=Sum("amount"))["total"]
            or 0
        )

        if this_total == 0 and prev_total == 0:
            return make_insight(
                "За текущий и предыдущий месяц ещё нет данных для сравнения.", None
            )

        if prev_total == 0:
            return make_insight(
                f"В этом месяце вы потратили {this_total:.2f} RUB. "
                f"Данных за предыдущий месяц нет, поэтому сравнение невозможно.",
                "Сохраните данные за несколько месяцев подряд — так будет проще отследить тренды.",
            )

        diff = this_total - prev_total
        pct = diff / prev_total * 100

        if diff > 0:
            main = (
                f"Расходы выросли на {pct:.1f}% по сравнению с прошлым месяцем "
                f"({prev_total:.2f} → {this_total:.2f} RUB)."
            )
            advice = (
                "Посмотрите, какие категории дали основной рост, "
                "и попробуйте сократить самые неважные траты в них."
            )
        elif diff < 0:
            main = (
                f"Расходы снизились на {abs(pct):.1f}% по сравнению с прошлым месяцем "
                f"({prev_total:.2f} → {this_total:.2f} RUB)."
            )
            advice = "Получилось уменьшить траты — можно зафиксировать это как новую норму и не возвращаться к старым уровням."
        else:
            main = "Расходы почти не изменились по сравнению с прошлым месяцем."
            advice = "Если хотите сэкономить, подумайте, какой целевой уровень расходов вы хотите увидеть в следующем месяце."

        return make_insight(main, advice)

    def recurring_merchants(self, min_occurrences: int = 3) -> dict:
        """
        Находим повторяющиеся описания — кандидаты в подписки / регулярные траты.
        """
        qs = self._qs()
        counter: Counter[str] = Counter()

        for e in qs:
            if e.description:
                desc = e.description.strip()
                if desc:
                    counter[desc] += 1

        recurring = [(desc, c) for desc, c in counter.items() if c >= min_occurrences]
        if not recurring:
            return make_insight(
                "Явных регулярных платежей (подписок) по описаниям пока не видно.",
                None,
            )

        recurring.sort(key=lambda x: x[1], reverse=True)
        parts: list[str] = []
        for desc, c in recurring[:3]:
            parts.append(
                f"Повторяющийся плательщик «{desc}» встречается {c} раз(а) в истории."
            )

        advice = (
            "Проверьте, действительно ли каждая из этих регулярных оплат вам нужна. "
            "Возможно, часть подписок можно отменить или сменить тариф."
        )
        return make_insight(" ".join(parts), advice)

    def bank_breakdown(self) -> dict:
        qs = (
            self._qs()
            .values("bank")
            .annotate(total=Sum("amount"))
            .order_by("-total")
        )
        if not qs:
            return make_insight("Разбивка по банкам пока недоступна.", None)

        total = sum((row["total"] or 0) for row in qs)
        parts: list[str] = []
        top_bank = None
        top_share = 0.0

        for row in qs:
            bank = row["bank"] or "Неизвестный банк"
            btotal = row["total"] or 0
            share = (btotal / total * 100) if total else 0
            parts.append(
                f"Банк «{bank}» — {btotal:.2f} RUB ({share:.1f}% от всех расходов)."
            )
            if top_bank is None:
                top_bank = bank
                top_share = share

        advice = None
        if top_bank and top_share >= 70:
            advice = (
                f"Большая часть расходов идёт через банк «{top_bank}». "
                f"Проверьте, используете ли вы максимально выгодные тарифы и кэшбэк-программы именно там."
            )

        return make_insight(" ".join(parts), advice)

    def weekly_spike(self) -> dict | None:
        """
        Сравниваем последние 7 дней и предыдущие 7 дней.
        """
        today = date.today()
        last_7_start = today - timedelta(days=6)
        prev_7_start = today - timedelta(days=13)
        prev_7_end = last_7_start - timedelta(days=1)

        qs = self._qs()
        last_7_total = (
            qs.filter(date__gte=last_7_start).aggregate(total=Sum("amount"))["total"] or 0
        )
        prev_7_total = (
            qs.filter(date__gte=prev_7_start, date__lte=prev_7_end)
            .aggregate(total=Sum("amount"))["total"]
            or 0
        )

        if last_7_total == 0 and prev_7_total == 0:
            return None

        if prev_7_total == 0:
            return make_insight(
                f"За последние 7 дней вы потратили {last_7_total:.2f} RUB. "
                f"До этого недели с данными не было.",
                "Если такие траты для вас разовые — зафиксируйте это. Если нет, стоит понять, не станет ли это новой привычкой.",
            )

        diff = last_7_total - prev_7_total
        pct = diff / prev_7_total * 100

        if abs(pct) < 15:
            return None  # изменение небольшое, можно не шуметь

        if diff > 0:
            main = (
                f"За последние 7 дней расходы выше предыдущих на {pct:.1f}% "
                f"({prev_7_total:.2f} → {last_7_total:.2f} RUB)."
            )
            advice = "Подумайте, какие именно покупки появились на этой неделе и можно ли часть из них не повторять в будущем."
        else:
            main = (
                f"За последние 7 дней расходы ниже предыдущих на {abs(pct):.1f}% "
                f"({prev_7_total:.2f} → {last_7_total:.2f} RUB)."
            )
            advice = "Это хороший знак — вы тратите меньше. Важно понять, что именно помогло сократить расходы, и сохранить эту стратегию."

        return make_insight(main, advice)

    # --- основной метод ---

    def answer_question(self, question: str) -> list[dict]:
        """
        Простая маршрутизация по ключевым словам:
        - если вопрос пустой → общий обзор + все ключевые блоки;
        - если упоминаются категории / месяц / подписки / банк / неделя —
          добавляем соответствующие инсайты;
        - всегда стараемся добавить общий обзор, если он ещё не включён.
        """
        q = (question or "").lower()

        insights: list[dict] = []
        added_keys: set[str] = set()

        def add_block(key: str, fn):
            if key in added_keys:
                return
            added_keys.add(key)
            res = fn()
            if res is None:
                return
            if isinstance(res, list):
                insights.extend(res)
            else:
                insights.append(res)

        if not q:
            add_block("overall", self.overall_summary)
            add_block("top_cat", self.top_categories)
            add_block("month", self.month_compare)
            add_block("recurring", self.recurring_merchants)
            add_block("bank", self.bank_breakdown)
            spike = self.weekly_spike()
            if spike:
                insights.append(spike)
            return insights

        # категории
        if any(k in q for k in ["category", "categories", "категор"]):
            add_block("top_cat", self.top_categories)

        # месяцы / динамика
        if any(k in q for k in ["month", "месяц", "динамик", "рост", "сравн"]):
            add_block("month", self.month_compare)

        # недели / последние дни
        if any(k in q for k in ["week", "недел", "7 дней", "последн", "recent"]):
            spike = self.weekly_spike()
            if spike:
                insights.append(spike)

        # подписки / регулярные траты
        if any(k in q for k in ["subscription", "подпис", "регуляр", "every month", "каждый месяц"]):
            add_block("recurring", self.recurring_merchants)

        # банки
        if any(k in q for k in ["bank", "банк", "сбер", "тинькофф", "tinkoff", "t-bank", "tb"]):
            add_block("bank", self.bank_breakdown)

        # если по ключам ничего не сработало — даём общий обзор и топ категорий
        if not insights:
            add_block("overall", self.overall_summary)
            add_block("top_cat", self.top_categories)

        return insights
