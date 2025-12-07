from django import forms

from .models import Expense, ExpenseCategory


class ExpenseForm(forms.ModelForm):
    date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"})
    )

    class Meta:
        model = Expense
        fields = ["category", "amount", "date", "description"]


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
