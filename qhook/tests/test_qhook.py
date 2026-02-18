from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from qux.qhook.decorators import call_target_url, qhook
from qux.qhook.models import QHookTarget


class TestQHookTargetStr(TestCase):
    def test_str_format(self):
        hook = QHookTarget.objects.create(
            owner="testowner",
            event="order.created",
            target_url="https://example.com/hook",
            identifier="order123",
        )
        self.assertEqual(str(hook), "order123 \u2192 order.created")


class TestQHookTargetStatusMethods(TestCase):
    def setUp(self):
        self.hook = QHookTarget.objects.create(
            owner="testowner",
            event="test.event",
            target_url="https://example.com/hook",
            identifier="hook1",
        )

    def test_success_increments_attempts_and_sets_status(self):
        initial_attempts = self.hook.attempts
        result = self.hook.success()
        self.hook.refresh_from_db()
        self.assertEqual(self.hook.attempts, initial_attempts + 1)
        self.assertEqual(self.hook.status, "SUCCESS")
        self.assertEqual(result, self.hook)

    def test_fail_sets_status_to_fail(self):
        result = self.hook.fail()
        self.hook.refresh_from_db()
        self.assertEqual(self.hook.status, "FAIL")
        self.assertEqual(result, self.hook)

    def test_pending_increments_attempts_and_sets_status(self):
        initial_attempts = self.hook.attempts
        result = self.hook.pending()
        self.hook.refresh_from_db()
        self.assertEqual(self.hook.attempts, initial_attempts + 1)
        self.assertEqual(self.hook.status, "PENDING")
        self.assertEqual(result, self.hook)


class TestValidateTargetUrl(TestCase):
    def test_valid_https_url_passes(self):
        # Should not raise
        QHookTarget.validate_target_url("https://example.com")

    def test_valid_http_url_passes(self):
        QHookTarget.validate_target_url("http://example.com/hook")

    def test_private_ip_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            QHookTarget.validate_target_url("https://192.168.1.1/hook")

    def test_loopback_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            QHookTarget.validate_target_url("https://127.0.0.1/hook")

    def test_link_local_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            QHookTarget.validate_target_url("https://169.254.1.1/hook")

    def test_localhost_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            QHookTarget.validate_target_url("https://localhost/hook")

    def test_metadata_google_internal_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            QHookTarget.validate_target_url("https://metadata.google.internal/hook")

    def test_ftp_scheme_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            QHookTarget.validate_target_url("ftp://example.com/hook")

    def test_no_scheme_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            QHookTarget.validate_target_url("noscheme")


class TestQHookTargetRegister(TestCase):
    def test_register_creates_qhook_target(self):
        mock_request = MagicMock()
        mock_request.data = {"target_url": "https://example.com/webhook"}
        mock_request.user.profile.slug = "testowner"

        QHookTarget.register(mock_request, identifier="proj1", event="build.done")

        hook = QHookTarget.objects.get(identifier="proj1")
        self.assertEqual(hook.owner, "testowner")
        self.assertEqual(hook.event, "build.done")
        self.assertEqual(hook.target_url, "https://example.com/webhook")

    def test_register_with_no_target_url_does_nothing(self):
        mock_request = MagicMock()
        mock_request.data = {}

        QHookTarget.register(mock_request, identifier="proj2", event="build.done")

        self.assertFalse(QHookTarget.objects.filter(identifier="proj2").exists())


class TestCallTargetUrl(TestCase):
    @patch("qux.qhook.decorators.requests.post")
    def test_returns_true_on_200(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        result = call_target_url("https://example.com/hook", {"key": "value"})
        self.assertTrue(result)
        mock_post.assert_called_once_with(
            "https://example.com/hook", json={"key": "value"}, timeout=30
        )

    @patch("qux.qhook.decorators.requests.post")
    def test_returns_false_on_500(self, mock_post):
        mock_post.return_value = MagicMock(status_code=500)
        result = call_target_url("https://example.com/hook", {"key": "value"})
        self.assertFalse(result)


@override_settings(QHOOK_EVENTS=["test.event"], QHOOK_MAX_ATTEMPTS=3)
class TestQHookDecorator(TestCase):
    def test_no_identifier_raises_value_error(self):
        @qhook
        def my_func():
            return {"event": "test.event"}

        with self.assertRaises(ValueError) as ctx:
            my_func()
        self.assertIn("Identifier", str(ctx.exception))

    def test_no_event_raises_value_error(self):
        @qhook
        def my_func():
            return {"identifier": "abc"}

        with self.assertRaises(ValueError) as ctx:
            my_func()
        self.assertIn("Event", str(ctx.exception))

    def test_no_matching_hook_raises_lookup_error(self):
        @qhook
        def my_func():
            return {"identifier": "nonexistent", "event": "test.event"}

        with self.assertRaises(LookupError) as ctx:
            my_func()
        self.assertIn("not found", str(ctx.exception))

    @patch("qux.qhook.decorators.call_target_url", return_value=True)
    def test_successful_hook_call_sets_success(self, _mock_call):
        hook = QHookTarget.objects.create(
            owner="owner",
            event="test.event",
            target_url="https://example.com/hook",
            identifier="myid",
        )

        @qhook
        def my_func():
            return {"identifier": "myid", "event": "test.event"}

        my_func()

        hook.refresh_from_db()
        self.assertEqual(hook.status, "SUCCESS")
        self.assertEqual(hook.attempts, 1)

    @patch("qux.qhook.decorators.call_target_url", return_value=False)
    def test_failed_hook_call_exhausts_attempts_and_fails(self, _mock_call):
        hook = QHookTarget.objects.create(
            owner="owner",
            event="test.event",
            target_url="https://example.com/hook",
            identifier="failid",
        )

        @qhook
        def my_func():
            return {"identifier": "failid", "event": "test.event"}

        my_func()

        hook.refresh_from_db()
        self.assertEqual(hook.status, "FAIL")
        self.assertEqual(hook.attempts, 3)

    def test_event_not_in_qhook_events_returns_early(self):
        """Cover line 31: early return when event doesn't match QHOOK_EVENTS."""
        hook = QHookTarget.objects.create(
            owner="owner",
            event="other.event",
            target_url="https://example.com/hook",
            identifier="mismatch_id",
        )

        @qhook
        def my_func():
            return {"identifier": "mismatch_id", "event": "other.event"}

        # "other.event" is not in QHOOK_EVENTS=["test.event"], so it returns early
        result = my_func()
        self.assertIsNone(result)

        hook.refresh_from_db()
        # Hook should not have been attempted
        self.assertEqual(hook.attempts, 0)
