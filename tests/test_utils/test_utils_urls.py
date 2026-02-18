import json
from unittest.mock import MagicMock, mock_open, patch

import requests
from django.http import JsonResponse
from django.test import SimpleTestCase

from qux.utils.urls import MetaURL, fetchurl, fetchurl_to_file


class TestFetchUrl(SimpleTestCase):
    @patch("qux.utils.urls.requests.get")
    def test_successful_fetch(self, mock_get):
        mock_response = MagicMock()
        mock_response.content = b"hello world"
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        contents, status_code = fetchurl("https://example.com")
        self.assertEqual(contents, b"hello world")
        self.assertEqual(status_code, 200)
        mock_get.assert_called_once_with("https://example.com", timeout=30)

    @patch("qux.utils.urls.requests.get")
    def test_connection_error_returns_none(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError
        contents, status_code = fetchurl("https://example.com")
        self.assertIsNone(contents)
        self.assertIsNone(status_code)

    @patch("qux.utils.urls.urlopen")
    @patch("qux.utils.urls.requests.get")
    def test_invalid_schema_falls_back_to_urlopen(self, mock_get, mock_urlopen):
        mock_get.side_effect = requests.exceptions.InvalidSchema
        mock_response = MagicMock()
        mock_response.read.return_value = b"fallback content"
        mock_response.status_code = 200
        mock_urlopen.return_value = mock_response

        contents, status_code = fetchurl("ftp://example.com/file")
        self.assertEqual(contents, b"fallback content")
        self.assertEqual(status_code, 200)
        mock_urlopen.assert_called_once_with("ftp://example.com/file", timeout=30)

    @patch("qux.utils.urls.urlopen")
    @patch("qux.utils.urls.requests.get")
    def test_invalid_schema_urlopen_urlerror_returns_none(self, mock_get, mock_urlopen):
        from urllib.error import URLError  # pylint: disable=import-outside-toplevel

        mock_get.side_effect = requests.exceptions.InvalidSchema
        mock_urlopen.side_effect = URLError("bad url")

        contents, status_code = fetchurl("ftp://example.com/file")
        self.assertIsNone(contents)
        self.assertIsNone(status_code)


class TestFetchUrlToFile(SimpleTestCase):
    @patch("qux.utils.urls.os.path.getsize", return_value=100)
    @patch("builtins.open", new_callable=mock_open)
    @patch("qux.utils.urls.fetchurl")
    def test_successful_write(self, mock_fetchurl, mock_file, _mock_getsize):
        mock_fetchurl.return_value = (b"file content", 200)

        result = fetchurl_to_file("https://example.com/file.txt", "/tmp/file.txt")
        self.assertTrue(result)
        mock_file.assert_called_once_with("/tmp/file.txt", "wb")
        mock_file().write.assert_called_once_with(b"file content")

    @patch("qux.utils.urls.fetchurl")
    def test_failed_fetch_returns_none(self, mock_fetchurl):
        mock_fetchurl.return_value = (None, None)

        result = fetchurl_to_file("https://example.com/file.txt", "/tmp/file.txt")
        self.assertIsNone(result)

    @patch("qux.utils.urls.fetchurl")
    def test_non_200_status_returns_none(self, mock_fetchurl):
        mock_fetchurl.return_value = (b"error", 404)

        result = fetchurl_to_file("https://example.com/file.txt", "/tmp/file.txt")
        self.assertIsNone(result)

    @patch("qux.utils.urls.os.remove")
    @patch("qux.utils.urls.os.path.getsize", return_value=0)
    @patch("builtins.open", new_callable=mock_open)
    @patch("qux.utils.urls.fetchurl")
    def test_empty_file_removed(
        self, mock_fetchurl, _mock_file, _mock_getsize, mock_remove
    ):
        mock_fetchurl.return_value = (b"", 200)

        fetchurl_to_file("https://example.com/file.txt", "/tmp/file.txt")
        mock_remove.assert_called_once_with("/tmp/file.txt")


class TestMetaURLInit(SimpleTestCase):
    def test_all_attributes_none(self):
        meta = MetaURL()
        self.assertIsNone(meta.orig_url)
        self.assertIsNone(meta.url)
        self.assertIsNone(meta.domain)
        self.assertIsNone(meta.type)
        self.assertIsNone(meta.title)
        self.assertIsNone(meta.description)
        self.assertIsNone(meta.image)


class TestMetaURLToDict(SimpleTestCase):
    def test_returns_dict_with_correct_keys(self):
        meta = MetaURL()
        result = meta.to_dict()
        self.assertIsInstance(result, dict)
        expected_keys = {"domain", "url", "type", "title", "description", "image"}
        self.assertEqual(set(result.keys()), expected_keys)

    def test_dict_values_match_attributes(self):
        meta = MetaURL()
        meta.domain = "example.com"
        meta.url = "https://example.com"
        meta.type = "website"
        meta.title = "Example"
        meta.description = "A description"
        meta.image = "https://example.com/img.png"

        result = meta.to_dict()
        self.assertEqual(result["domain"], "example.com")
        self.assertEqual(result["url"], "https://example.com")
        self.assertEqual(result["type"], "website")
        self.assertEqual(result["title"], "Example")
        self.assertEqual(result["description"], "A description")
        self.assertEqual(result["image"], "https://example.com/img.png")


class TestMetaURLStr(SimpleTestCase):
    def test_returns_json_string(self):
        meta = MetaURL()
        result = str(meta)
        parsed = json.loads(result)
        self.assertIsInstance(parsed, dict)
        expected_keys = {"domain", "url", "type", "title", "description", "image"}
        self.assertEqual(set(parsed.keys()), expected_keys)


class TestMetaURLLoad(SimpleTestCase):
    @patch("qux.utils.urls.requests.get")
    def test_load_with_og_tags(self, mock_get):
        html = """
        <html>
        <head>
            <title>Fallback Title</title>
            <meta property="og:url" content="https://example.com/page" />
            <meta property="og:title" content="OG Title" />
            <meta property="og:description" content="OG Description" />
            <meta property="og:image" content="https://example.com/image.png" />
            <meta property="og:type" content="article" />
        </head>
        <body></body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.content = html.encode()
        mock_response.url = "https://example.com/page"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        meta = MetaURL()
        meta.url = "https://example.com/page"
        _result = meta.load()

        self.assertEqual(meta.url, "https://example.com/page")
        self.assertEqual(meta.title, "OG Title")
        self.assertEqual(meta.description, "OG Description")
        self.assertEqual(meta.image, "https://example.com/image.png")
        self.assertEqual(meta.type, "article")
        self.assertEqual(meta.domain, "example.com")
        self.assertEqual(meta.orig_url, "https://example.com/page")

    @patch("qux.utils.urls.requests.get")
    def test_load_without_og_tags_fallback(self, mock_get):
        # HTML with no <head> triggers AttributeError on soup.html.head.find_all
        html = b"<body><p>No head tag here</p></body>"
        mock_response = MagicMock()
        mock_response.content = html
        mock_response.url = "https://example.com/document.pdf"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        meta = MetaURL()
        meta.url = "https://example.com/document.pdf"
        _result = meta.load()

        self.assertEqual(meta.type, "file.pdf")
        self.assertEqual(meta.title, "/document.pdf")
        self.assertIsNone(meta.description)

    @patch("qux.utils.urls.requests.get")
    def test_load_head_present_but_no_og_tags(self, mock_get):
        html = """
        <html>
        <head><title>Plain Page</title></head>
        <body><p>No OG tags here</p></body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.content = html.encode()
        mock_response.url = "https://example.com/page"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        meta = MetaURL()
        meta.url = "https://example.com/page"
        _result = meta.load()

        self.assertEqual(meta.type, "website")
        self.assertEqual(meta.title, "Plain Page")
        self.assertIsNone(meta.description)

    @patch("qux.utils.urls.requests.get")
    def test_load_connection_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError

        meta = MetaURL()
        meta.url = "https://invalid.example.com"
        result = meta.load()

        self.assertIsInstance(result, JsonResponse)
        self.assertIn(b"invalid", result.content)

    @patch("qux.utils.urls.requests.get")
    def test_load_timeout(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout

        meta = MetaURL()
        meta.url = "https://slow.example.com"
        result = meta.load()

        self.assertIsInstance(result, JsonResponse)
        self.assertIn(b"Error connecting", result.content)

    @patch("qux.utils.urls.requests.get")
    def test_load_url_without_scheme(self, mock_get):
        html = """
        <html>
        <head>
            <title>Test</title>
            <meta property="og:title" content="Test Title" />
            <meta property="og:type" content="website" />
        </head>
        <body></body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.content = html.encode()
        mock_response.url = "https://example.com"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        meta = MetaURL()
        meta.url = "example.com"
        meta.load()

        self.assertEqual(meta.orig_url, "example.com")
        self.assertEqual(meta.domain, "example.com")
        mock_get.assert_called_once()
        call_url = mock_get.call_args[0][0]
        self.assertTrue(call_url.startswith("https://"))
