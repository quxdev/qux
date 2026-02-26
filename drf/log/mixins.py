import json
import sys
from random import Random

from .app_settings import app_settings
from .base_mixins import BaseLoggingMixin
from .models import APIRequestLog
from .rules import should_log
from .tasks import persist_api_log


class LoggingMixin(BaseLoggingMixin):
    def handle_log(self):
        """
        Hook to define what happens with the log.

        Defaults on saving the data on the db.
        """
        if not app_settings.ENABLED:
            return

        status_code = int(self.log.get("status_code", 0) or 0)

        # Evaluate rules
        # Base mixin stores user as slug/userid string; we cannot reliably map back here
        # but rules engine will handle None gracefully
        user_identifier = self.log.get("user")
        path = self.log.get("path")
        method = self.log.get("method")

        if not should_log(user_identifier):
            return

        # Always log errors if configured
        if status_code >= 400 and app_settings.ALWAYS_LOG_ERRORS:
            pass

        max_size = getattr(app_settings, "MAX_SIZE")

        keys = self.log.keys()
        # json.dumps(dict) is a hack to get order of magnitude of the size of
        # a nested dictionary correct. It is inaccurate but serves our need.
        # The size of the dictionary is not the same as the size of the
        # string representation of the dictionary.
        for key in sorted(keys):
            value_str = json.dumps(self.log[key], default=str)
            if sys.getsizeof(value_str) > max_size:
                self.log.pop(key)

        # Optional: drop response for non-error statuses to reduce storage
        if app_settings.STORE_RESPONSE_ON_ERRORS_ONLY and status_code < 400:
            if "response" in self.log:
                self.log.pop("response")

        # Truncate data/response aggressively
        for key in ("data", "response"):
            if key in self.log and isinstance(self.log[key], (str, bytes)):
                limit = int(app_settings.MAX_BODY_BYTES)
                value = self.log[key]
                if isinstance(value, bytes):
                    value = value[:limit]
                else:
                    if len(value) > limit:
                        value = value[:limit]
                self.log[key] = value

        # Dispatch async persistence
        try:
            persist_api_log.delay(self.log)
        except Exception:
            # Fallback to synchronous save if Celery unavailable
            APIRequestLog(**self.log).save()


class LoggingErrorsMixin(LoggingMixin):
    """
    Log only errors
    """

    def should_log(self, request, response):
        return response.status_code >= 400
