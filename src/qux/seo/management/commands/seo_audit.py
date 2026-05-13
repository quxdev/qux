"""
Management command to run an SEO audit on any website.

Usage::

    python manage.py seo_audit example.com
    python manage.py seo_audit example.com --scheme http
    python manage.py seo_audit example.com --report  # print report to stdout
"""

from django.core.management.base import BaseCommand

from qux.seo.scanner import format_report, scan_site


class Command(BaseCommand):
    help = "Run an SEO audit on a website by crawling its sitemap."

    def add_arguments(self, parser):
        parser.add_argument("domain", help="Domain to audit (e.g. example.com)")
        parser.add_argument(
            "--scheme",
            default="https",
            choices=["http", "https"],
            help="URL scheme (default: https)",
        )
        parser.add_argument(
            "--report",
            action="store_true",
            help="Print a detailed report to stdout after the audit.",
        )

    def handle(self, *args, **options):
        domain = options["domain"]
        scheme = options["scheme"]

        self.stdout.write(f"Starting SEO audit for {scheme}://{domain} ...")

        audit = scan_site(domain, scheme=scheme)

        if audit.status == "failed":
            self.stderr.write(
                self.style.ERROR(f"Audit failed — could not fetch sitemap for {domain}")
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Audit complete: {audit.total_urls} URLs, "
                f"{audit.total_errors} errors, {audit.total_warnings} warnings"
            )
        )

        if options["report"]:
            self.stdout.write("")
            self.stdout.write(format_report(audit))
