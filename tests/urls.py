from django.urls import path, include

urlpatterns = [
    path("account/tokens/", include("qux.token.urls")),
    path("auth/", include("qux.auth.urls.appurls")),
]
