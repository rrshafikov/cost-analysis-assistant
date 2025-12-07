from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include

from accounts.views import RegisterView

urlpatterns = [
    path("admin/", admin.site.urls),

    path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("logout/", SimpleLogoutView.as_view(), name="custom_logout"),

    # password reset и related URL-ы (password_reset, password_reset_done и т.д.)
    path("accounts/", include("django.contrib.auth.urls")),

    # регистрация как стартовая страница
    path("", RegisterView.as_view(), name="register"),

    # основные страницы приложения расходов
    path("", include("expenses.urls")),
]
