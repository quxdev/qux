import sys

from .app_settings import app_settings
from .base_mixins import BaseLoggingMixin
from .models import APIRequestLog


class LoggingMixin(BaseLoggingMixin):
    def handle_log(self):
        """
        Hook to define what happens with the log.

        Defaults on saving the data on the db.
        """
        max_size = getattr(app_settings, "MAX_SIZE")
        for field in ["query_params", "data", "response", "errors"]:
            if sys.getsizeof(self.log.get(field)) > max_size:
                self.log.pop(field)

        APIRequestLog(**self.log).save()


class LoggingErrorsMixin(LoggingMixin):
    """
    Log only errors
    """

    def should_log(self, request, response):
        return response.status_code >= 400
