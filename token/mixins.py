from qux.token.models import CustomTokenAuthentication
from django.http import JsonResponse


def authenticate_user(request):
    """
    Method to check the user authentication in mixin in case of token
    based authentication
    """
    auth_obj = CustomTokenAuthentication()
    try:
        user, token = auth_obj.authenticate(request)
        print(f"User: {user}, Token: {token}")
        return user
    except:
        return request.user


class TokenAccessMixin(object):
    """
    access_required - list of strings, required param

    Provides functionality for user group access check
    """

    access_required = None

    def dispatch(self, request, *args, **kwargs):
        user = authenticate_user(request)

        print(self.access_required)

        if not user.is_authenticated:
            return JsonResponse(
                data="User is not authenticated!", safe=False, status=401
            )

        user_groups = list(user.groups.values_list("name", flat=True))

        if set(user_groups).intersection(self.access_required):
            return super().dispatch(request, *args, **kwargs)

        return JsonResponse(data="User is not authorized!", safe=False, status=403)
