from django.conf import settings
from django.http import JsonResponse
from rest_framework.exceptions import AuthenticationFailed

from qux.token.models import CustomTokenAuthentication


def authenticate_user(request):
    """
    Method to check the user authentication in mixin in case of token
    based authentication
    """
    auth_obj = CustomTokenAuthentication()

    try:
        user_token = auth_obj.authenticate(request)
        if user_token is None:
            raise AuthenticationFailed
        user, token = user_token[0], user_token[1].name
    except AuthenticationFailed:
        user = request.user
        token = None

    if settings.DEBUG:
        print(f"User: {user}, Token: {token}")

    return user


class TokenAccessMixin(object):
    """
    access_required - list of strings, required param

    Provides functionality for user group access check
    """

    access_required = None

    def dispatch(self, request, *args, **kwargs):
        user = authenticate_user(request)

        if not user.is_authenticated:
            return JsonResponse(
                data="User is not authenticated!", safe=False, status=401
            )

        user_groups = list(user.groups.values_list("name", flat=True))

        if set(user_groups).intersection(self.access_required):
            return super().dispatch(request, *args, **kwargs)

        return JsonResponse(data="User is not authorized!", safe=False, status=403)
