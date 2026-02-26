"""PageSpeed: images must use loading="lazy" for off-screen content.

Scans all HTML templates for ``<img`` tags and asserts that each one
includes ``loading="lazy"``.  This prevents off-screen images from
blocking the initial page load and improves Largest Contentful Paint
(LCP) scores.
"""

import os

from django.conf import settings
from django.test import SimpleTestCase

from qux.pagespeed.checks import check_lazy_loading
from qux.pagespeed.config import LAZY_LOADING_EXCEPTIONS


class TestImageLazyLoading(SimpleTestCase):
    """All <img> tags in templates must have loading="lazy"."""

    def test_all_images_have_lazy_loading(self):
        """All images must include loading="lazy" for off-screen content."""
        missing = check_lazy_loading(LAZY_LOADING_EXCEPTIONS)
        self.assertEqual(
            len(missing),
            0,
            f'{len(missing)} image(s) missing loading="lazy". '
            "Run: python manage.py pagespeed_report --detailed",
        )

    def test_lazy_loading_exceptions_are_still_valid(self):
        """Ensure allowlisted files still exist — prune stale entries."""
        for relpath, line_no in LAZY_LOADING_EXCEPTIONS:
            path = os.path.join(settings.BASE_DIR, relpath)
            self.assertTrue(
                os.path.exists(path),
                f"Stale LAZY_LOADING_EXCEPTIONS entry: {relpath}:{line_no} "
                "— file no longer exists. Remove it.",
            )
