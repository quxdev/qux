#!/usr/bin/env python
"""Run the qux test suite without installing the package.

Adds src/ to sys.path so `import qux` resolves to the working tree, points
DJANGO_SETTINGS_MODULE at `qux.tests.settings`, and runs the discovered tests.

Equivalent installed-mode invocation (after `pip install -e '.[dev]'`):

    DJANGO_SETTINGS_MODULE=qux.tests.settings django-admin test qux.<app>
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "src"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "qux.tests.settings")

import django  # noqa: E402
from django.conf import settings  # noqa: E402
from django.test.utils import get_runner  # noqa: E402

django.setup()

verbosity = int(os.environ.get("QUX_TEST_VERBOSITY", "1"))
TestRunner = get_runner(settings)
test_runner = TestRunner(verbosity=verbosity)
failures = test_runner.run_tests(
    [
        "qux.tests",
        "qux.auth.tests",
        "qux.seo.tests",
        "qux.token.tests",
        "qux.qhook.tests",
        "qux.drf.log.tests",
    ]
)
sys.exit(bool(failures))
