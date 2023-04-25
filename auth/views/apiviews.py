from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView


class ToggleUserMode(APIView):
    def get(self, request, *args, **kwargs):
        user = self.request.user
        slug = kwargs.get("slug", None)
        if slug == user.profile.slug:
            print(user.profile.is_live)
            user.profile.is_live = not user.profile.is_live
            print(user.profile.is_live)
            user.profile.save()

        return Response(user.profile.is_live, status=200)
