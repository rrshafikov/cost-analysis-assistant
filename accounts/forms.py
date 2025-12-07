from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=False,
        help_text="Необязательно, можно оставить пустым.",
    )

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]
