"""
API URL patterns for qux_auth CLI OTP endpoints.
"""

from django.urls import path

from ..views.apiviews import CLIOTPRequestView, CLIOTPVerifyView

urlpatterns = [
    path("cli/request/", CLIOTPRequestView.as_view(), name="cli-otp-request"),
    path("cli/verify/", CLIOTPVerifyView.as_view(), name="cli-otp-verify"),
]
