"""Tests for the scanner's polite-request layer.

The scanner makes external HTTP calls. Without throttling it would hammer the
target (10k URLs in a sitemap = 10k back-to-back requests). These tests pin
the three knobs that keep it well-behaved:

- ``QUX_SEO_REQUEST_DELAY_MS`` — sleep between consecutive requests.
- ``QUX_SEO_USER_AGENT`` — clear UA on outgoing requests.
- ``QUX_SEO_MAX_URLS`` — cap on URLs scanned per ``scan_site`` run.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase, override_settings

from qux.seo import scanner


class TestPoliteRequestDefaults(SimpleTestCase):
    def test_default_delay_is_250ms(self):
        self.assertAlmostEqual(scanner._request_delay_seconds(), 0.25)

    def test_default_user_agent_identifies_scanner(self):
        ua = scanner._user_agent()
        self.assertIn("qux", ua.lower())

    def test_default_max_urls_is_10000(self):
        self.assertEqual(scanner._max_urls(), 10000)


class TestPoliteRequestSettingsOverride(SimpleTestCase):
    @override_settings(QUX_SEO_REQUEST_DELAY_MS=0)
    def test_delay_zero_disables_throttling(self):
        self.assertEqual(scanner._request_delay_seconds(), 0.0)

    @override_settings(QUX_SEO_REQUEST_DELAY_MS=1500)
    def test_delay_settings_override(self):
        self.assertEqual(scanner._request_delay_seconds(), 1.5)

    @override_settings(QUX_SEO_REQUEST_DELAY_MS=-100)
    def test_negative_delay_clamps_to_zero(self):
        self.assertEqual(scanner._request_delay_seconds(), 0.0)

    @override_settings(QUX_SEO_USER_AGENT="custom-bot/1.0")
    def test_user_agent_settings_override(self):
        self.assertEqual(scanner._user_agent(), "custom-bot/1.0")

    @override_settings(QUX_SEO_MAX_URLS=42)
    def test_max_urls_settings_override(self):
        self.assertEqual(scanner._max_urls(), 42)


class TestPoliteGetSetsUserAgent(SimpleTestCase):
    def test_polite_get_passes_user_agent_header(self):
        with patch("qux.seo.scanner.requests.get") as mock_get:
            mock_get.return_value = MagicMock()
            scanner._polite_get("https://example.com/x")
        kwargs = mock_get.call_args.kwargs
        self.assertEqual(kwargs["timeout"], scanner.REQUEST_TIMEOUT)
        self.assertEqual(kwargs["headers"]["User-Agent"], scanner._user_agent())


@override_settings(QUX_SEO_REQUEST_DELAY_MS=0, QUX_SEO_MAX_URLS=10000)
class TestScanSiteCallsPoliteGet(TestCase):
    def test_scan_site_uses_polite_get(self):
        # Stub fetch_sitemap_urls to avoid hitting the network for the sitemap;
        # then assert _polite_get is what scan_site uses for each page.
        page_urls = ["https://example.com/a", "https://example.com/b"]
        page_resp = MagicMock(status_code=200, text="<html>ok</html>")
        with (
            patch("qux.seo.scanner.fetch_sitemap_urls", return_value=page_urls),
            patch("qux.seo.scanner._polite_get", return_value=page_resp) as mock_get,
        ):
            audit = scanner.scan_site("example.com")
        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual(audit.total_urls, 2)


@override_settings(QUX_SEO_REQUEST_DELAY_MS=50, QUX_SEO_MAX_URLS=10000)
class TestScanSiteSleepsBetweenRequests(TestCase):
    def test_sleep_called_between_requests(self):
        page_urls = ["https://example.com/a", "https://example.com/b", "https://example.com/c"]
        page_resp = MagicMock(status_code=200, text="<html>ok</html>")
        with (
            patch("qux.seo.scanner.fetch_sitemap_urls", return_value=page_urls),
            patch("qux.seo.scanner._polite_get", return_value=page_resp),
            patch("qux.seo.scanner.time.sleep") as mock_sleep,
        ):
            scanner.scan_site("example.com")
        # Sleep called between requests (3 requests → 2 sleeps); no sleep before the first.
        self.assertEqual(mock_sleep.call_count, 2)
        self.assertAlmostEqual(mock_sleep.call_args.args[0], 0.05)


@override_settings(QUX_SEO_REQUEST_DELAY_MS=0, QUX_SEO_MAX_URLS=2)
class TestScanSiteCapsUrls(TestCase):
    def test_url_list_truncated_at_cap(self):
        page_urls = [f"https://example.com/p{i}" for i in range(10)]
        page_resp = MagicMock(status_code=200, text="<html>ok</html>")
        with (
            patch("qux.seo.scanner.fetch_sitemap_urls", return_value=page_urls),
            patch("qux.seo.scanner._polite_get", return_value=page_resp) as mock_get,
        ):
            audit = scanner.scan_site("example.com")
        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual(audit.total_urls, 2)
