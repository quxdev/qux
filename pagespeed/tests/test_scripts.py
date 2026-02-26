"""PageSpeed: external scripts should not block rendering.

Scripts in ``<head>`` without ``async`` or ``defer`` block the HTML
parser.  Scripts at the end of ``<body>`` are less critical but still
benefit from ``defer`` for parallel download.

Note: inline ``<script>`` blocks (no ``src``) and dynamically injected
scripts (e.g. GTM's inline loader) are not flagged — they run
synchronously by design or manage their own async loading.
"""

import os
import re

from django.conf import settings
from django.test import SimpleTestCase

from qux.pagespeed.checks import SCRIPT_SRC_RE, check_script_loading, read_project_file
from qux.pagespeed.config import SCRIPT_ALLOWLIST


class TestScriptLoading(SimpleTestCase):
    """External scripts should use async or defer to avoid blocking."""

    def test_scripts_have_async_or_defer(self):
        """External scripts must use async or defer to avoid blocking."""
        missing = check_script_loading(SCRIPT_ALLOWLIST)
        self.assertEqual(
            len(missing),
            0,
            f"{len(missing)} script(s) missing async/defer. "
            "Run: python manage.py pagespeed_report --detailed",
        )

    def test_no_scripts_in_head_without_async(self):
        """Scripts in <head> (extra_head block) must be async/defer.

        The base template's extra_head block runs before <body>.  Any
        external script there without async blocks the entire page render.

        Limitation: this only checks the base template.  Scripts injected
        by child templates that override ``extra_head`` are not detected —
        those should be caught by ``test_scripts_have_async_or_defer`` which
        scans all templates.
        """
        content = read_project_file("templates/_blank.html")

        head_match = re.search(
            r"\{%\s*block\s+extra_head\s*%\}(.*?)\{%\s*endblock\s*%\}",
            content,
            re.DOTALL,
        )
        if not head_match:
            return  # No extra_head block

        head_content = head_match.group(1)
        for match in SCRIPT_SRC_RE.finditer(head_content):
            # Groups: 1=pre-attrs, 2=quote char, 3=src value, 4=post-attrs
            src = match.group(3)
            attrs = match.group(1) + match.group(4)
            has_async_defer = re.search(r"\bdefer\b|\basync\b", attrs, re.IGNORECASE)
            self.assertTrue(
                has_async_defer,
                f"Render-blocking script in <head>: src={src}. Add async or defer.",
            )

    def test_allowlist_entries_are_still_referenced(self):
        """Ensure allowlisted scripts still appear in templates."""
        for pattern in SCRIPT_ALLOWLIST:
            # External URLs — can't verify on disk
            if pattern.startswith("//"):
                continue
            # Static file path like "qux/js/bootstrap/bootstrap.bundle.min.js"
            # lives at qux/static/<pattern> on disk
            static_path = os.path.join(settings.BASE_DIR, "qux", "static", pattern)
            self.assertTrue(
                os.path.exists(static_path),
                f"Stale ALLOWLIST entry: {pattern} — "
                f"static file not found at {static_path}. Remove it.",
            )
