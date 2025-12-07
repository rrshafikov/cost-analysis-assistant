from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include

from accounts.views import RegisterView, SimpleLogoutView

urlpatterns = [
    path("admin/", admin.site.urls),

    path(
        "login/",
        auth_views.LoginView.as_view(template_name="accounts/login.html"),
        name="login",
    ),

    path(
        "logout/",
        SimpleLogoutView.as_view(),
        name="custom_logout",
    ),

    # password reset flow (all templates in accounts/)
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/password_reset_form.html"
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),

    path("", RegisterView.as_view(), name="register"),
    path("", include("expenses.urls")),
    path("ai/", include("ai.urls")),
]
