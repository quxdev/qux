from django.contrib.auth.views import LogoutView
from django.urls import path
from django.conf.urls import url

from .views import *

app_name = 'qux_auth'

urlpatterns = [
    url(r'^signup/$', signup, name='signup'),
    url(
        r'^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        activate, name='activate'
    ),

    path('login/', CoreLoginView.as_view(redirect_authenticated_user=True), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path(r'password-reset/', CorePasswordResetView.as_view(), name='password_reset'),
    path(r'password-reset/done/', CorePasswordResetDoneView.as_view(), name='password_reset_done'),
    path(r'reset/<uidb64>/<token>/', CorePasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path(r'reset/done/', CorePasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path(r'needhelp/', TemplateView.as_view(template_name='login.html'), name='support_request'),
]
