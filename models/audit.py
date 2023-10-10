from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from .base import CoreModel


class CoreModelAuditSummary(CoreModel):
    slug = models.CharField(max_length=16, unique=True)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    content_type = models.ForeignKey(ContentType, on_delete=models.DO_NOTHING)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def get_details(self):
        if hasattr(self, "details"):
            return self.details.all()

        raise NotImplementedError


class CoreModelAuditDetails(CoreModel):
    audit_summary = models.ForeignKey(
        CoreModelAuditSummary, on_delete=models.CASCADE, related_name="details"
    )
    field_name = models.CharField(max_length=128)
    old_value = models.JSONField(default=dict, null=True, blank=True)
    new_value = models.JSONField(default=dict, null=True, blank=True)

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["audit_summary", "field_name"]),
        ]
