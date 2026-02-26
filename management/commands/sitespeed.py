"""Audit site and CDN delivery stack (HTTP/2, TLS, DNS, compression, security headers).

Usage:
    python manage.py site_audit --url https://example.com --cdn https://cdn.example.com
    python manage.py site_audit --url https://example.com --cdn https://cdn.example.com --json
    python manage.py site_audit --url https://example.com --cdn https://cdn.example.com --compact
"""

import json
import sys

from django.core.management.base import BaseCommand

from qux.sitespeed.endpoint import Endpoint


class Command(BaseCommand):
    """Audit site and CDN delivery stack."""

    help = "Audit site + CDN delivery stack"

    def add_arguments(self, parser):
        """Add --url, --cdn, --timeout, --json, and --compact flags."""
        parser.add_argument("--url", required=True, help="Primary site URL")
        parser.add_argument("--cdn", required=True, help="CDN asset URL")
        parser.add_argument("--timeout", type=int, default=10)
        parser.add_argument("--json", action="store_true", help="JSON output")
        parser.add_argument("--compact", action="store_true", help="Compact output")

    def handle(self, *args, **options):
        """Run the audit and output results."""
        site = Endpoint(options["url"], options["timeout"], parse_html=True)
        cdn = Endpoint(options["cdn"], options["timeout"], parse_html=False)

        status = self.combine_status(site, cdn)

        if options["json"]:
            self.stdout.write(
                json.dumps(
                    {
                        "status": status,
                        "site": site.data,
                        "cdn": cdn.data,
                    },
                    indent=2,
                )
            )
            sys.exit(self.exit_code(status))

        if options["compact"]:
            width = 72
            print("\nDelivery Audit (Compact)")
            print("=" * width)

            print("\nSite")
            site.render_compact(include_css=True)

            print("\nCDN")
            cdn.render_compact(include_cache=True)

        else:
            self.render_table(site.data, cdn.data)

        printed = False
        printed |= site.render_warnings("Site")
        printed |= cdn.render_warnings("CDN")

        print(f"\nStatus: {status}")

        sys.exit(self.exit_code(status))

    @staticmethod
    def combine_status(site, cdn):
        """Combine site and CDN statuses into a single overall status."""
        statuses = {site.status(), cdn.status()}

        if "FAIL" in statuses:
            return "FAIL"
        if "WARN" in statuses:
            return "WARN"
        return "PASS"

    @staticmethod
    def exit_code(status):
        """Map status string to process exit code."""
        if status == "PASS":
            return 0
        if status == "WARN":
            return 1
        return 2

    @staticmethod
    def render_table(site, cdn):
        """Print a full comparison table of site vs CDN metrics."""
        key_width = 40
        val_width = 15
        total_width = 72

        def normalize(value):
            """Normalize a value for display."""
            if value is None:
                return "-"
            if isinstance(value, (int, float)):
                if isinstance(value, float):
                    return f"{value:,.3f}".rstrip("0").rstrip(".")
                return f"{value:,}"
            return str(value).strip()

        def fit(value):
            """Truncate a normalized value to fit the column width."""
            value = normalize(value)
            if len(value) > val_width:
                return value[: val_width - 1] + "\u2026"
            return value

        # Compute security header pass/fail counts
        site_sec = site.get("security_headers", {})
        cdn_sec = cdn.get("security_headers", {})
        site_sec_str = (
            f"{sum(1 for v in site_sec.values() if v is not None)}/{len(site_sec)}"
            if site_sec
            else "-"
        )
        cdn_sec_str = (
            f"{sum(1 for v in cdn_sec.values() if v is not None)}/{len(cdn_sec)}"
            if cdn_sec
            else "-"
        )

        rows = [
            ("HTTP Version", site.get("http_version"), cdn.get("http_version")),
            ("TLS Version", site.get("tls_version"), cdn.get("tls_version")),
            ("Status", site.get("status_code"), cdn.get("status_code")),
            ("POP", site.get("cf_pop"), cdn.get("cf_pop")),
            ("Cache Status", site.get("cf_cache_status"), cdn.get("cf_cache_status")),
            ("TTFB (ms)", site.get("ttfb_ms"), cdn.get("ttfb_ms")),
            ("Total Time (ms)", site.get("total_time_ms"), cdn.get("total_time_ms")),
            ("Encoding", site.get("content_encoding"), cdn.get("content_encoding")),
            (
                "Compressed Bytes",
                site.get("compressed_bytes"),
                cdn.get("compressed_bytes"),
            ),
            (
                "Uncompressed Bytes",
                site.get("uncompressed_bytes"),
                cdn.get("uncompressed_bytes"),
            ),
            (
                "Compression Ratio",
                site.get("compression_ratio"),
                cdn.get("compression_ratio"),
            ),
            ("Stylesheets", site.get("stylesheet_count"), "-"),
            ("Blocking Scripts", site.get("blocking_script_count"), "-"),
            ("Security Headers", site_sec_str, cdn_sec_str),
            (
                "Cert Expiry (days)",
                site.get("cert_expiry_days"),
                cdn.get("cert_expiry_days"),
            ),
            ("Cert Issuer", site.get("cert_issuer"), cdn.get("cert_issuer")),
            (
                "HSTS Preload Ready",
                site.get("hsts_preload_ready"),
                cdn.get("hsts_preload_ready"),
            ),
            (
                "Redirects",
                len(site.get("redirect_chain", [])),
                len(cdn.get("redirect_chain", [])),
            ),
            (
                "DNS Resolve (ms)",
                site.get("dns_resolve_ms"),
                cdn.get("dns_resolve_ms"),
            ),
            ("DNS A Records", site.get("dns_a_count"), cdn.get("dns_a_count")),
            ("IPv6", site.get("ipv6_address"), cdn.get("ipv6_address")),
            ("Age (s)", site.get("age"), cdn.get("age")),
            ("Vary", site.get("vary"), cdn.get("vary")),
        ]

        print("\nDelivery Audit")
        print("=" * total_width)
        print(f"{'Key':<{key_width}}{'Site':>{val_width}}{'CDN':>{val_width}}")
        print("-" * total_width)

        for label, site_val, cdn_val in rows:
            print(
                f"{label:<{key_width}}"
                f"{fit(site_val):>{val_width}}"
                f"{fit(cdn_val):>{val_width}}"
            )
