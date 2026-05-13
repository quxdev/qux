from django.urls import include, path

urlpatterns = [
    path("account/tokens/", include("qux.token.urls")),
    path("auth/", include("qux.auth.urls.appurls")),
]
