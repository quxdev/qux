import ipaddress
from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.db import models

from qux.models import CoreModel

QHOOK_STATUS = (("SUCCESS", "success"), ("FAIL", "fail"), ("PENDING", "pending"))


class QHookTarget(CoreModel):
    owner = models.CharField(max_length=32)
    event = models.CharField(max_length=255)
    target_url = models.CharField(max_length=255)
    identifier = models.CharField(max_length=32)
    attempts = models.IntegerField(default=0)
    status = models.CharField(max_length=32, choices=QHOOK_STATUS, default="PENDING")

    class Meta:
        db_table = "qux_qhook_target"
        constraints = [
            models.UniqueConstraint(
                fields=["identifier", "target_url"],
                name="unique_qhook_identifier_url",
            ),
        ]

    def __str__(self):
        return f"{self.identifier} → {self.event}"

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
    def validate_target_url(url):
        """Reject URLs targeting private/internal networks (SSRF protection)."""
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            raise ValidationError("Invalid webhook URL.")
        if not parsed.scheme or parsed.scheme not in ("http", "https"):
            raise ValidationError("Webhook URL must use http or https.")
        try:
            addr = ipaddress.ip_address(hostname)
            if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
                raise ValidationError("Webhook URL must not target private networks.")
        except ValueError:
            # hostname is a domain name, not an IP — check for common internal names
            if hostname in ("localhost", "metadata.google.internal"):
                raise ValidationError("Webhook URL must not target internal hosts.") from None

    @staticmethod
    def register(request, identifier, event):
        target_url = request.data.get("target_url", None)
        if target_url is not None:
            QHookTarget.validate_target_url(target_url)
            QHookTarget.objects.create(
                owner=request.user.profile.slug,
                event=event,
                target_url=target_url,
                identifier=identifier,
            )
