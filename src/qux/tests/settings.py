"""Django settings module for qux's own test suite and for tooling that needs
configured Django settings (pylint-django, mypy-django, IDE inspectors).

Wire-up:

    python -m django test qux.<app> --settings=qux.tests.settings

    pylint --load-plugins=pylint_django --django-settings-module=qux.tests.settings src/qux/

`runtests.py` sets ``DJANGO_SETTINGS_MODULE`` to this module and runs the
discovered tests; downstream projects do not consume this module.
"""

from __future__ import annotations

SECRET_KEY = "test-secret-key-do-not-use-in-production"
DEBUG = True
SITE_ID = 1
BASE_DIR = "/tmp/qux_test"
ROOT_URLCONF = "qux.tests.urls"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sites",
    "django.contrib.admin",
    "rest_framework",
    "impersonate",
    "qux",
    "qux.auth",
    "qux.seo",
    "qux.token",
    "qux.qhook",
    "qux.drf.log",
    "qux.contacts",
    "qux.tests",
]

MIDDLEWARE = [
    # QuxRequestIdMiddleware MUST be first so events emitted by any later
    # middleware or signal handler carry a request_id.
    "qux.telemetry.middleware.QuxRequestIdMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "null": {"class": "logging.NullHandler"},
    },
    "loggers": {
        # Route qux logger to a sink during tests so emit()/logger.warning/etc.
        # don't pollute the test runner's stdout. `assertLogs` attaches its own
        # handler at runtime and still captures records regardless of propagation,
        # so test coverage of log output is unaffected.
        "qux": {"handlers": ["null"], "level": "DEBUG", "propagate": False},
    },
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
ROOT_TEMPLATE = "_blank.html"
STATIC_URL = "/static/"
