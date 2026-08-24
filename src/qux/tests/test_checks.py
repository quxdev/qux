"""Tests for ``qux.checks`` — the qux.W001 static-assets system check."""

from __future__ import annotations

from unittest.mock import patch

from django.test import SimpleTestCase

from qux.checks import W001_ID, check_static_assets


class TestStaticAssetsCheck(SimpleTestCase):
    def test_no_warning_when_nothing_missing(self):
        with patch("qux.checks.missing_assets", return_value=[]):
            self.assertEqual(check_static_assets(), [])

    def test_warns_and_lists_every_missing_asset(self):
        with patch(
            "qux.checks.missing_assets",
            return_value=["bundle not unpacked: bootstrap 5.2.3", "alias target missing: static/x"],
        ):
            warnings = check_static_assets()

        self.assertEqual(len(warnings), 1)
        warning = warnings[0]
        self.assertEqual(warning.id, W001_ID)
        self.assertIn("bundle not unpacked: bootstrap 5.2.3", warning.msg)
        self.assertIn("alias target missing: static/x", warning.msg)
        self.assertIn("qux-install-assets", warning.hint)

    def test_real_tree_is_complete(self):
        """The working tree itself must not be missing assets after install."""
        self.assertEqual(check_static_assets(), [])
