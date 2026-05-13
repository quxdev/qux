"""PageSpeed: resource hints (preconnect, dns-prefetch) in base template.

The base template should declare ``<link rel="preconnect">`` for origins
the page will need early (CDN, analytics, third-party scripts).  This
shaves ~100-300 ms off each cross-origin request by completing the TCP +
TLS handshake ahead of time.
"""

from django.test import SimpleTestCase

from qux.pagespeed.checks import check_resource_hints
from qux.pagespeed.config import BASE_TEMPLATE, VIEWPORT_SEARCH_PATHS


class TestResourceHints(SimpleTestCase):
    """Base template must have preconnect, dns-prefetch, and viewport."""

    def test_resource_hints(self):
        """Base template must have preconnect, dns-prefetch, and viewport."""
        findings = check_resource_hints(BASE_TEMPLATE, VIEWPORT_SEARCH_PATHS)
        self.assertEqual(
            len(findings),
            0,
            f"{len(findings)} resource hint issue(s). "
            "Run: python manage.py pagespeed --detailed",
        )
