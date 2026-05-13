"""PageSpeed summary — prints the report at the end of the test run.

This test always passes.  It runs all checks and prints a grouped
summary so you can see overall template health at a glance.  For
per-file details, run:

    python manage.py pagespeed --detailed
"""

import logging

from django.test import SimpleTestCase

from qux.pagespeed.checks import format_summary
from qux.pagespeed.config import run_all_checks


class TestPageSpeedSummary(SimpleTestCase):
    """Run all PageSpeed checks and print a summary report."""

    def test_summary(self):
        """Collect all findings and print the grouped PageSpeed summary."""
        checks = run_all_checks()

        lines = ["", "PageSpeed Summary"]
        lines.extend(format_summary(checks))

        total = sum(len(f) for _, _, f in checks)
        lines.append("")
        lines.append(f"Total issues: {total}")
        if total:
            lines.append("Run: python manage.py pagespeed --detailed")
        lines.append("")

        logging.getLogger("qux").info("\n".join(lines))
