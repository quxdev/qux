import hashlib
import os
import tempfile
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.test import TestCase, SimpleTestCase, override_settings
from django.utils import timezone

from qux.logger.models import CoreCommLog, CoreURLLog, DownloadLog, UploadLog

User = get_user_model()


class TestDownloadLog(TestCase):
    def test_creation_with_all_fields(self):
        user = User.objects.create_user(username="dluser", password="pass123")
        log = DownloadLog(
            user=user,
            url="https://example.com/file.pdf",
            original="report.pdf",
            filename="download_report.pdf",
        )
        assert log.url == "https://example.com/file.pdf"
        assert log.original == "report.pdf"
        assert log.filename == "download_report.pdf"
        assert log.user == user


class TestUploadLogSave(TestCase):
    @patch.object(UploadLog, "save_base")
    def test_save_computes_file_hash_for_existing_file(self, mock_save_base):
        tmpdir = tempfile.mkdtemp()
        test_content = b"hello world test content"

        filepath = os.path.join(tmpdir, "upload.txt")
        with open(filepath, "wb") as f:
            f.write(test_content)

        expected_hash = hashlib.md5(test_content).hexdigest()

        with override_settings(BASE_DIR=tmpdir):
            log = UploadLog(
                filename="upload.txt",
                filepath="",
                filedate=timezone.now(),
            )
            log.save()

        assert log.filehash == expected_hash

        os.unlink(filepath)
        os.rmdir(tmpdir)

    @patch.object(UploadLog, "save_base")
    def test_save_sets_empty_hash_for_missing_file(self, mock_save_base):
        tmpdir = tempfile.mkdtemp()

        with override_settings(BASE_DIR=tmpdir):
            log = UploadLog(
                filename="nonexistent.txt",
                filepath="missing_dir",
                filedate=timezone.now(),
            )
            log.save()

        assert log.filehash == ""
        os.rmdir(tmpdir)


class TestCoreURLLogStr(TestCase):
    def test_str_returns_numeric_string_when_saved(self):
        log = CoreURLLog(id=42, urlpath="/api/test")
        result = str(log)
        assert result == "42"

    def test_str_returns_id_of_object_when_unsaved(self):
        log = CoreURLLog(urlpath="/api/test")
        result = str(log)
        # When id is None, it uses id(self) which is a Python object id
        assert result == str(id(log))


class TestCoreCommLog(TestCase):
    def test_creation(self):
        user = User.objects.create_user(username="commuser", password="pass123")
        log = CoreCommLog(
            comm_type="email",
            user=user,
            sender="noreply@example.com",
            to="user@example.com",
            subject="Test Subject",
            message="Test message body",
            status=True,
        )
        assert log.comm_type == "email"
        assert log.sender == "noreply@example.com"
        assert log.status is True
