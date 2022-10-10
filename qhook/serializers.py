from .models import QHookTarget
from rest_framework import serializers


class QHookTargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = QHookTarget
        fields = ["identifier", "target_url", "event", "attempts", "status"]
