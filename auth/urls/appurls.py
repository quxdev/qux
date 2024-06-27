"""
    App urls for qux_auth.
"""

from django.contrib.auth.views import LogoutView
from django.urls import path

from ..views.appviews import (
    QuxSignupView,
    QuxActivateView,
    QuxLoginView,
    QuxChangePasswordView,
    QuxPasswordResetView,
    QuxPasswordResetDoneView,
    QuxPasswordResetConfirmView,
    QuxPasswordResetCompleteView,
    TemplateView,
)

app_name = "qux_auth"

urlpatterns = [
    path("signup/", QuxSignupView.as_view(), name="signup"),
    path(
        "activate/<uidb64>/<token>/",
        QuxActivateView.as_view(),
        name="activate",
    ),
    path(
        "login/",
        QuxLoginView.as_view(redirect_authenticated_user=True),
        name="login",
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
    path(
        "change-password/",
        QuxChangePasswordView.as_view(),
        name="change_password",
    ),
    path(
        r"password-reset/",
        QuxPasswordResetView.as_view(),
        name="password_reset",
    ),
    path(
        r"password-reset/done/",
        QuxPasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        r"reset/<uidb64>/<token>/",
        QuxPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        r"reset/done/",
        QuxPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path(
        r"needhelp/",
        TemplateView.as_view(template_name="login.html"),
        name="support_request",
    ),
]
