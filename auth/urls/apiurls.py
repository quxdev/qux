from django.urls import path

from ..views.apiviews import (
    ToggleUserMode,
)


app_name = "quxauth_api"

urlpatterns = [
    path(
        "user/<slug:slug>/toggle_mode/",
        ToggleUserMode.as_view(),
        name="toggle_user_mode",
    ),
]
