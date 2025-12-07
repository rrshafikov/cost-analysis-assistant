from django import forms

from .models import Expense, ExpenseCategory


class ExpenseForm(forms.ModelForm):
    # отдельное текстовое поле для категории
    category_name = forms.CharField(
        required=False,
        label="Category",
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        # category (FK) скрываем, работаем только через category_name
        self.fields["category"].widget = forms.HiddenInput()

        # дата как date input
        self.fields["date"].widget = forms.DateInput(attrs={"type": "date"})

        # навешиваем базовый класс
        for name in ["date", "description", "amount", "bank", "currency", "category_name"]:
            if name in self.fields:
                existing = self.fields[name].widget.attrs.get("class", "")
                self.fields[name].widget.attrs["class"] = (existing + " auth-input").strip()

        # datalist-привязки
        self.fields["category_name"].widget.attrs["list"] = "category-options"
        self.fields["currency"].widget.attrs["list"] = "currency-options"
        self.fields["bank"].widget.attrs["list"] = "bank-options"
        # можно и description подсказать
        self.fields["description"].widget.attrs["list"] = "description-options"

        # при редактировании – проставить category_name
        if self.instance.pk and self.instance.category:
            self.fields["category_name"].initial = self.instance.category.name

    class Meta:
        model = Expense
        fields = ["date", "description", "category", "amount", "bank", "currency"]

    def save(self, commit=True):
        expense = super().save(commit=False)

        name = (self.cleaned_data.get("category_name") or "").strip()
        if name:
            category, _ = ExpenseCategory.objects.get_or_create(
                user=self.user,
                name=name,
            )
            expense.category = category

        if commit:
            expense.save()
        return expense


class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ["name"]


class StatementImportForm(forms.Form):
    SOURCE_CHOICES = [
        ("tbank_csv", "T-Bank CSV"),
        ("sber_pdf", "Sberbank PDF"),
    ]

    source = forms.ChoiceField(
        choices=SOURCE_CHOICES,
        label="Statement type",
    )
    file = forms.FileField(
        label="Statement file",
        help_text="Upload a CSV from T-Bank or a PDF statement from Sber.",
    )
