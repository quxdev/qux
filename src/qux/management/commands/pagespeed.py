"""Generate a PageSpeed findings report by scanning templates and CSS.

Runs the same checks as qux/pagespeed/tests/ and collects every
finding into a single report.

Usage:
    python manage.py pagespeed                  # writes to stdout
    python manage.py pagespeed --detailed       # include per-file findings
    python manage.py pagespeed -o report.txt    # writes to file
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from qux.pagespeed.checks import format_summary, get_template_dirs
from qux.pagespeed.config import run_all_checks


def _collapse(text, maxlen=80):
    """Collapse whitespace in a tag snippet to a single line."""
    return " ".join(text.split())[:maxlen]


def _loc_fmt(finding):
    """Format (relpath, line_no, text) with text on a new line."""
    return f"{finding[0]}:{finding[1]}\n       {_collapse(finding[2])}"


def _font_fmt(finding):
    """Format (css_file, font_name, message) with message on a new line."""
    return f"{finding[0]}: {finding[1]}\n       {finding[2]}"


def _script_fmt(finding):
    """Format (relpath, line_no, src) with src on a new line."""
    return f"{finding[0]}:{finding[1]}\n       src={finding[2]}"


# Detail format per category — used only by --detailed output.
_DETAIL_FMT = {
    "FONTS": _font_fmt,
    "SCRIPTS": _script_fmt,
    "RESOURCE HINTS": str,
}


class Command(BaseCommand):
    """Generate a PageSpeed findings report for all templates and CSS."""

    help = "Generate a PageSpeed findings report for all templates and CSS"

    def add_arguments(self, parser):
        """Add --output and --detailed flags."""
        parser.add_argument(
            "-o",
            "--output",
            help="Write report to this file (default: stdout)",
        )
        parser.add_argument(
            "--detailed",
            action="store_true",
            help="Include per-file findings for failing checks",
        )

    def handle(self, *args, **options):
        """Run all checks, build report, and write output."""
        lines = [
            "PageSpeed Report",
            f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S %Z')}",
            "Scanned dirs:",
        ]
        for d in get_template_dirs():
            lines.append(f"- {d}")
        lines.append("")

        checks = run_all_checks()
        lines.extend(format_summary(checks))

        if options["detailed"]:
            self._append_details(lines, checks)

        lines.append("")
        lines.append(f"Total issues: {sum(len(f) for _, _, f in checks)}")

        report = "\n".join(lines) + "\n"
        if options.get("output"):
            with open(options["output"], "w", encoding="utf-8") as fh:
                fh.write(report)
            self.stdout.write(self.style.SUCCESS(f"Report written to {options['output']}"))
        else:
            self.stdout.write(report)

    @staticmethod
    def _append_details(lines, checks):
        """Append per-file failure details to *lines*."""
        has_details = False
        for category, title, findings in checks:
            if not findings:
                continue
            if not has_details:
                lines.append("")
                has_details = True
            fmt = _DETAIL_FMT.get(category, _loc_fmt)
            lines.append(f"[FAIL] {category} — {title}")
            for f in findings:
                lines.append(f"     - {fmt(f)}")
