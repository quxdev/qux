from qux.models import CoreModel
from django.db import models

QHOOK_STATUS = (("SUCESS", "success"), ("FAIL", "fail"), ("PENDING", "pending"))


class QHookTarget(CoreModel):
    owner = models.CharField(max_length=32)
    event = models.CharField(max_length=255)
    target_url = models.CharField(max_length=255)
    identifier = models.CharField(max_length=32)
    attempts = models.IntegerField(default=0)
    status = models.CharField(max_length=32, choices=QHOOK_STATUS, default="PENDING")

    class Meta:
        unique_together = ("identifier", "target_url")

    def success(self):
        self.attempts += 1
        self.status = "SUCCESS"
        self.save()
        return self

    def fail(self):
        self.status = "FAIL"
        self.save()
        return self

    def pending(self):
        self.attempts += 1
        self.status = "PENDING"
        self.save()
        return self

    @staticmethod
    def register(request, identifier, event):
        target_url = request.data.get("target_url", None)
        if target_url is not None:
            QHookTarget.objects.create(
                owner=request.user.profile.slug,
                event=event,
                target_url=request.data.get("target_url"),
                identifier=identifier,
            )
