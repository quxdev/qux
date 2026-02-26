from django.conf import settings


class AppSettings:
    def __init__(self, prefix):
        self.prefix = prefix

    def _setting(self, name, default):
        return getattr(settings, self.prefix + name, default)

    @property
    def ADMIN_LOG_READONLY(self):  # pylint: disable=invalid-name
        """Prevent log entries from being modified from Django admin."""
        return self._setting("ADMIN_LOG_READONLY", False)

    @property
    def DECODE_REQUEST_BODY(self):  # pylint: disable=invalid-name
        """
        Allow the request.body byte string to be decoded to a string.

        If you are allowing large file uploads, setting this to False prevents
        a RequestDataTooBig exception.
        """
        return self._setting("DECODE_REQUEST_BODY", True)

    @property
    def PATH_LENGTH(self):  # pylint: disable=invalid-name
        """Maximum length of request path to log"""
        return self._setting("PATH_LENGTH", 256)

    @property
    def LOOKUP_FIELD(self):  # pylint: disable=invalid-name
        """Field to identify user in User model"""
        return self._setting("LOOKUP_FIELD", "email")

    @property
    def MAX_SIZE(self):  # pylint: disable=invalid-name
        """Maximum size of field to log"""
        return self._setting("MAX_SIZE", 4096)

    # noinspection PyPep8Naming
    @property
    def ENABLED(self):
        """Global switch to enable/disable API request logging"""
        return self._setting("ENABLED", True)

    # noinspection PyPep8Naming
    @property
    def ALWAYS_LOG_ERRORS(self):
        """Always log error responses (4xx/5xx) regardless of sampling"""
        return self._setting("ALWAYS_LOG_ERRORS", True)

    # noinspection PyPep8Naming
    @property
    def MAX_BODY_BYTES(self):
        """Maximum number of bytes to store for data/response fields"""
        return self._setting("MAX_BODY_BYTES", 4096)

    # noinspection PyPep8Naming
    @property
    def STORE_RESPONSE_ON_ERRORS_ONLY(self):
        """If True, only store response body for error responses (status >= 400)"""
        return self._setting("STORE_RESPONSE_ON_ERRORS_ONLY", True)

    # noinspection PyPep8Naming
    @property
    def RETENTION_DAYS(self):
        """Default number of days to retain API logs when pruning"""
        return self._setting("RETENTION_DAYS", 14)

    # noinspection PyPep8Naming
    @property
    def LOG_QUEUE(self):
        """Celery queue name for request log persistence task"""
        return self._setting("LOG_QUEUE", "drf_log")


app_settings = AppSettings("DRF_TRACKING_")
