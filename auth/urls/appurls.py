"""
App urls for qux_auth.
"""

from django.conf import settings
from django.contrib.auth.views import LogoutView
from django.urls import path

from ..views.appviews import (
    CompleteProfileView,
    MagicLinkLoginView,
    MagicLinkRequestView,
    QuxActivateView,
    QuxChangePasswordView,
    QuxLoginView,
    QuxPasswordResetCompleteView,
    QuxPasswordResetConfirmView,
    QuxPasswordResetDoneView,
    QuxPasswordResetView,
    QuxSetPasswordView,
    QuxSignupView,
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
]

# Configure the primary login route based on settings.USE_EMAIL_SIGNIN
if hasattr(settings, "USE_MAGIC_LINK") and settings.USE_MAGIC_LINK:
    urlpatterns += [
        path(
            "magic-link/",
            MagicLinkRequestView.as_view(),
            name="magic_link",
        ),
    ]

urlpatterns += [
    path("logout/", LogoutView.as_view(), name="logout"),
    path(
        "change-password/",
        QuxChangePasswordView.as_view(),
        name="change_password",
    ),
    path(
        "password-reset/",
        QuxPasswordResetView.as_view(),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        QuxPasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        QuxPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        QuxPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path(
        "needhelp/",
        TemplateView.as_view(template_name="login.html"),
        name="support_request",
    ),
    path(
        "login/link/<uidb64>/<token>/",
        MagicLinkLoginView.as_view(),
        name="login_link",
    ),
    path(
        "update-profile/",
        CompleteProfileView.as_view(),
        name="update_profile",
    ),
    path(
        r"set-password/",
        QuxSetPasswordView.as_view(),
        name="set_password",
    ),
]
