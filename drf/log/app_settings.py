from django.conf import settings


class AppSettings(object):
    def __init__(self, prefix):
        self.prefix = prefix

    def _setting(self, name, default):
        return getattr(settings, self.prefix + name, default)

    # noinspection PyPep8Naming
    @property
    def ADMIN_LOG_READONLY(self):
        """Prevent log entries from being modified from Django admin."""
        return self._setting("ADMIN_LOG_READONLY", False)

    # noinspection PyPep8Naming
    @property
    def DECODE_REQUEST_BODY(self):
        """
        Allow the request.body byte string to be decoded to a string.

        If you are allowing large file uploads, setting this to False prevents
        a RequestDataTooBig exception.
        """
        return self._setting("DECODE_REQUEST_BODY", True)

    # noinspection PyPep8Naming
    @property
    def PATH_LENGTH(self):
        """Maximum length of request path to log"""
        return self._setting("PATH_LENGTH", 256)

    # noinspection PyPep8Naming
    @property
    def LOOKUP_FIELD(self):
        """Field to identify user in User model"""
        return self._setting("LOOKUP_FIELD", "email")

    # noinspection PyPep8Naming
    @property
    def MAX_SIZE(self):
        """Maximum size of field to log"""
        return self._setting("MAX_SIZE", 4096)


app_settings = AppSettings("DRF_TRACKING_")
