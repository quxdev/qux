from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import *


urlpatterns = [
    path('login/', CoreLoginView.as_view(redirect_authenticated_user=True), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path(r'password-reset/', CorePasswordResetView.as_view(), name='password_reset'),
    path(r'password-reset/done/', CorePasswordResetDoneView.as_view(), name='password_reset_done'),
    path(r'reset/<uidb64>/<token>/', CorePasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path(r'reset/done/', CorePasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
