from django.urls import path

from .views import *

app_name = "qux_token"

urlpatterns = [
    path("", CustomTokenListView.as_view(), name="home"),
    path("new/", CustomTokenCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", CustomTokenUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", CustomTokenDeleteView.as_view(), name="delete"),
    path("<str:key>/", CustomTokenDetailView.as_view(), name="key"),
]
