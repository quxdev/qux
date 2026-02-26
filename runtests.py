#!/usr/bin/env python
import sys

import django
from django.conf import settings
from django.test.utils import get_runner

settings.configure(
    SECRET_KEY="test-secret-key-do-not-use-in-production",
    INSTALLED_APPS=[
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
    ],
    MIDDLEWARE=[
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
    ],
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    },
    DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
    DEBUG=True,
    SITE_ID=1,
    ROOT_URLCONF="qux.tests.urls",
    BASE_DIR="/tmp/qux_test",
    TEMPLATES=[
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
    ],
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ROOT_TEMPLATE="_blank.html",
    STATIC_URL="/static/",
)
django.setup()

TestRunner = get_runner(settings)
test_runner = TestRunner(verbosity=2)
failures = test_runner.run_tests(
    [
        "qux.tests",
        "qux.auth.tests",
        "qux.seo.tests",
        "qux.token.tests",
        "qux.qhook.tests",
        "qux.logger.tests",
        "qux.drf.log.tests",
    ]
)
sys.exit(bool(failures))
