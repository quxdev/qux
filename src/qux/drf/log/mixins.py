"""DRF API request logging — emits structured records on the ``qux.drf`` channel.

Replaces the prior celery-based DB-INSERT pipeline. The mixin builds a record
dict from the request/response and emits it via stdlib ``logging``; operators
wire whatever sink they want via Django's standard ``LOGGING`` config (file,
JSON to ELK/Datadog/Loki, syslog, or — for parity with the old behavior — the
opt-in ``qux.drf.log.handlers.APIRequestLogDBHandler`` that writes to the
``APIRequestLog`` ORM model).

See ``README.drf-logging.md`` for handler / filter recipes.
"""

from __future__ import annotations

import json
import logging
import sys

from .app_settings import app_settings
from .base_mixins import BaseLoggingMixin
from .rules import should_log

_log = logging.getLogger("qux.drf")


class LoggingMixin(BaseLoggingMixin):
    def handle_log(self):
        """Emit the assembled ``self.log`` dict on the ``qux.drf`` logger."""
        if not app_settings.ENABLED:
            return

        status_code = int(self.log.get("status_code", 0) or 0)
        user_identifier = self.log.get("user")

        if not should_log(user_identifier):
            return

        max_size = app_settings.MAX_SIZE
        for key in sorted(self.log.keys()):
            value_str = json.dumps(self.log[key], default=str)
            if sys.getsizeof(value_str) > max_size:
                self.log.pop(key)

        if app_settings.STORE_RESPONSE_ON_ERRORS_ONLY and status_code < 400:
            self.log.pop("response", None)

        for key in ("data", "response"):
            value = self.log.get(key)
            if isinstance(value, (str, bytes)):
                limit = int(app_settings.MAX_BODY_BYTES)
                self.log[key] = value[:limit]

        level = logging.WARNING if status_code >= 400 else logging.INFO
        _log.log(level, "request", extra={"event": "request", **self.log})


class LoggingErrorsMixin(LoggingMixin):
    """Log only error responses (status >= 400)."""

    def should_log(self, request, response):
        return response.status_code >= 400
