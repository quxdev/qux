import datetime
import hashlib
import os
import tempfile
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from qux.utils.file import filedate, filehash, uploadfile


class TestFiledate(SimpleTestCase):
    def test_existing_file(self):
        with tempfile.NamedTemporaryFile() as f:
            result = filedate(f.name)
            assert result is not None
            assert isinstance(result, datetime.datetime)

    def test_missing_file(self):
        result = filedate("/nonexistent/path/file.txt")
        assert result is None


class TestFilehash(SimpleTestCase):
    def test_known_content(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"hello world")
            f.flush()
            name = f.name

        try:
            result = filehash(name)
            assert result is not None
            assert len(result) == 32  # md5 hex digest length
        finally:
            os.unlink(name)

    def test_missing_file(self):
        result = filehash("/nonexistent/path/file.txt")
        assert result is None

    def test_empty_file_returns_md5_of_empty(self):
        expected = hashlib.md5(b"").hexdigest()
        with tempfile.NamedTemporaryFile(delete=False) as f:
            name = f.name
        try:
            result = filehash(name)
            assert result == expected
        finally:
            os.unlink(name)


class TestUploadfile(SimpleTestCase):
    def test_success(self):
        source = MagicMock()
        source.name = "test.txt"
        source.chunks.return_value = [b"chunk1", b"chunk2"]

        with tempfile.NamedTemporaryFile(delete=False) as f:
            target = f.name

        try:
            result, filename = uploadfile(source, target=target)
            assert result is True
            assert filename == target
            with open(target, "rb") as fh:
                assert fh.read() == b"chunk1chunk2"
        finally:
            os.unlink(target)

    def test_failure_bad_path(self):
        source = MagicMock()
        source.name = "test.txt"
        source.chunks.return_value = [b"data"]

        result, _filename = uploadfile(source, target="/nonexistent/dir/file.txt")
        assert result is False

    def test_upload_with_no_target_uses_default_basepath(self):
        """Cover lines 25-26: uploadfile with target=None uses default basepath."""
        source = MagicMock()
        source.name = "test_default.txt"
        source.chunks.return_value = [b"data"]

        with patch("qux.utils.file.settings") as mock_settings:
            mock_settings.BASE_DIR = tempfile.gettempdir()
            # Create the expected directory
            basepath = os.path.join(tempfile.gettempdir(), "data/upload")
            os.makedirs(basepath, exist_ok=True)
            expected_filename = os.path.join(basepath, "test_default.txt")

            try:
                result, filename = uploadfile(source, target=None)
                assert result is True
                assert filename == expected_filename
            finally:
                if os.path.exists(expected_filename):
                    os.unlink(expected_filename)
