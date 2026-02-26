from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

from qux.models import QuxModel

from .base_models import BaseAPIRequestLog


class APIRequestLog(BaseAPIRequestLog):
    pass


class APILoggingRule(QuxModel):
    """Per-user enable/disable rule for API request logging (default enabled)."""

    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    enabled = models.BooleanField(
        default=True,
        help_text="When True, logging is enabled for this user; when False, disabled",
    )
    active = models.BooleanField(default=True)
    notes = models.CharField(max_length=256, blank=True)

    class Meta:
        unique_together = ("user",)
        verbose_name = "API Logging Rule"
        verbose_name_plural = "API Logging Rules"

    def __str__(self):
        status = "enabled" if self.enabled else "disabled"
        return f"{self.user_id} -> {status}{' (inactive)' if not self.active else ''}"
