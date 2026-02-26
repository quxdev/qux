from rest_framework import serializers

from .models import QHookTarget


class QHookTargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = QHookTarget
        fields = ["identifier", "target_url", "event", "attempts", "status"]
