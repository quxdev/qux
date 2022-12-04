import json
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

        keys = self.log.keys()
        for key in sorted(keys):
            """
            json.dumps(dict) is a hack to get order of magnitude of the size of
            a nested dictionary correct. It is inaccurate but serves our need.

            The size of the dictionary is not the same as the size of the
            string representation of the dictionary.
            """
            value_str = json.dumps(self.log[key], default=str)
            if sys.getsizeof(value_str) > max_size:
                self.log.pop(key)

        APIRequestLog(**self.log).save()


class LoggingErrorsMixin(LoggingMixin):
    """
    Log only errors
    """

    def should_log(self, request, response):
        return response.status_code >= 400
