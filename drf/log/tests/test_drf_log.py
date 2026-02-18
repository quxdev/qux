# pylint: disable=protected-access,import-outside-toplevel
import datetime
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.admin import AdminSite
from django.test import SimpleTestCase, override_settings
from django.utils.timezone import now

import qux.core
import qux.drf.log as drf_log
from qux.core.apps import CoreConfig
from qux.drf.log.admin import APIRequestLogAdmin
from qux.drf.log.app_settings import AppSettings
from qux.drf.log.apps import APILogConfig
from qux.drf.log.base_mixins import BaseLoggingMixin
from qux.drf.log.base_models import BaseAPIRequestLog
from qux.drf.log.mixins import LoggingErrorsMixin, LoggingMixin


class FakeAPIView:
    """Fake base class to stand in for DRF's APIView."""

    def initial(self, request, *args, **kwargs):
        pass

    def handle_exception(self, exc):
        pass

    def finalize_response(self, request, response, *args, **kwargs):
        return response


class ConcreteLoggingMixin(
    BaseLoggingMixin, FakeAPIView
):  # pylint: disable=too-many-instance-attributes
    """Concrete subclass for testing BaseLoggingMixin instance methods."""

    def __init__(self):  # pylint: disable=super-init-not-called
        # Bypass super().__init__ which expects *args/**kwargs from a view
        setattr(self, "CLEANED_SUBSTITUTE", "********************")
        self.log = None
        self.sensitive_fields = {}
        self.logging_methods = "__all__"

    def handle_log(self):
        pass


def _make_request(meta=None, method="GET", user=None):
    """Create a mock request object."""
    request = MagicMock()
    request.META = meta or {}
    request.method = method
    if user is not None:
        request.user = user
    else:
        request.user = MagicMock()
        request.user.is_anonymous = True
    return request


class TestGetIpAddress(SimpleTestCase):
    def test_ipv4_remote_addr(self):
        request = _make_request(meta={"REMOTE_ADDR": "192.168.1.1"})
        result = BaseLoggingMixin._get_ip_address(request)
        assert result == "192.168.1.1"

    def test_ipv6_remote_addr(self):
        request = _make_request(meta={"REMOTE_ADDR": "::1"})
        result = BaseLoggingMixin._get_ip_address(request)
        assert result == "::1"

    def test_x_forwarded_for_multiple_ips_takes_first(self):
        request = _make_request(
            meta={"HTTP_X_FORWARDED_FOR": "10.0.0.1, 10.0.0.2, 10.0.0.3"}
        )
        result = BaseLoggingMixin._get_ip_address(request)
        assert result == "10.0.0.1"

    def test_ipv4_with_port(self):
        request = _make_request(meta={"REMOTE_ADDR": "192.168.1.1:8080"})
        result = BaseLoggingMixin._get_ip_address(request)
        assert result == "192.168.1.1"

    def test_invalid_ip_returns_raw_string(self):
        """Cover the ValueError branch (line 148) when no valid IP can be parsed."""
        request = _make_request(meta={"REMOTE_ADDR": "not-an-ip"})
        result = BaseLoggingMixin._get_ip_address(request)
        assert result == "not-an-ip"


class TestCleanData(SimpleTestCase):
    def setUp(self):
        self.mixin = ConcreteLoggingMixin()

    def test_dict_with_password_key_replaced(self):
        data = {"username": "admin", "password": "secret123"}
        result = self.mixin._clean_data(data)
        assert result["password"] == self.mixin.CLEANED_SUBSTITUTE
        assert result["username"] == "admin"

    def test_dict_with_token_key_replaced(self):
        data = {"token": "abc123", "data": "value"}
        result = self.mixin._clean_data(data)
        assert result["token"] == self.mixin.CLEANED_SUBSTITUTE
        assert result["data"] == "value"

    def test_nested_dict_recursively_cleaned(self):
        data = {"outer": {"password": "secret"}}
        result = self.mixin._clean_data(data)
        assert result["outer"]["password"] == self.mixin.CLEANED_SUBSTITUTE

    def test_list_of_dicts_each_cleaned(self):
        data = [{"password": "one"}, {"password": "two"}]
        result = self.mixin._clean_data(data)
        assert len(result) == 2
        for item in result:
            assert item["password"] == self.mixin.CLEANED_SUBSTITUTE

    def test_bytes_decoded_to_string(self):
        data = b"some byte string"
        result = self.mixin._clean_data(data)
        assert result == "some byte string"

    def test_custom_sensitive_fields(self):
        self.mixin.sensitive_fields = {"custom_secret"}
        data = {"custom_secret": "hidden", "normal": "visible"}
        result = self.mixin._clean_data(data)
        assert result["custom_secret"] == self.mixin.CLEANED_SUBSTITUTE
        assert result["normal"] == "visible"


class TestShouldLog(SimpleTestCase):
    def test_logging_methods_all_returns_true_for_any_method(self):
        mixin = ConcreteLoggingMixin()
        mixin.logging_methods = "__all__"
        request = _make_request(method="POST")
        response = MagicMock()
        assert mixin.should_log(request, response) is True

    def test_logging_methods_list_returns_true_for_matching(self):
        mixin = ConcreteLoggingMixin()
        mixin.logging_methods = ["GET"]
        request_get = _make_request(method="GET")
        request_post = _make_request(method="POST")
        response = MagicMock()
        assert mixin.should_log(request_get, response) is True
        assert mixin.should_log(request_post, response) is False


class TestGetUser(SimpleTestCase):
    def test_anonymous_user_returns_none(self):
        request = _make_request()
        request.user.is_anonymous = True
        result = BaseLoggingMixin._get_user(request)
        assert result is None

    def test_user_with_profile_slug_returns_slug(self):
        user = MagicMock()
        user.is_anonymous = False
        user.id = 5
        user.profile = MagicMock()
        user.profile.slug = "usr_abc123"
        request = _make_request(user=user)
        result = BaseLoggingMixin._get_user(request)
        assert result == "usr_abc123"

    def test_user_without_profile_returns_userid_n(self):
        user = MagicMock()
        user.is_anonymous = False
        user.id = 42
        # Remove profile attribute
        del user.profile
        request = _make_request(user=user)
        result = BaseLoggingMixin._get_user(request)
        assert result == "userid_42"


class TestLoggingErrorsMixinShouldLog(SimpleTestCase):
    def test_returns_true_for_status_400(self):
        mixin = LoggingErrorsMixin()
        request = _make_request()
        response = MagicMock()
        response.status_code = 400
        assert mixin.should_log(request, response) is True

    def test_returns_false_for_status_200(self):
        mixin = LoggingErrorsMixin()
        request = _make_request()
        response = MagicMock()
        response.status_code = 200
        assert mixin.should_log(request, response) is False


class TestAppSettings(SimpleTestCase):
    def test_path_length_default(self):
        app = AppSettings("DRF_TRACKING_")
        assert app.PATH_LENGTH == 256

    def test_decode_request_body_default(self):
        app = AppSettings("DRF_TRACKING_")
        assert app.DECODE_REQUEST_BODY is True

    @override_settings(DRF_TRACKING_PATH_LENGTH=512)
    def test_path_length_override(self):
        app = AppSettings("DRF_TRACKING_")
        assert app.PATH_LENGTH == 512

    @override_settings(DRF_TRACKING_DECODE_REQUEST_BODY=False)
    def test_decode_request_body_override(self):
        app = AppSettings("DRF_TRACKING_")
        assert app.DECODE_REQUEST_BODY is False

    def test_admin_log_readonly_default(self):
        """Cover ADMIN_LOG_READONLY property (line 14)."""
        app = AppSettings("DRF_TRACKING_")
        assert app.ADMIN_LOG_READONLY is False

    def test_lookup_field_default(self):
        """Cover LOOKUP_FIELD property (line 34)."""
        app = AppSettings("DRF_TRACKING_")
        assert app.LOOKUP_FIELD == "email"

    def test_max_size_default(self):
        """Cover MAX_SIZE property (line 39)."""
        app = AppSettings("DRF_TRACKING_")
        assert app.MAX_SIZE == 4096


class TestGetPath(SimpleTestCase):
    """Cover _get_path (line 123)."""

    def test_truncates_long_path(self):
        request = _make_request()
        request.path = "/api/" + "x" * 300
        result = BaseLoggingMixin._get_path(request)
        assert len(result) == 256

    def test_short_path_unchanged(self):
        request = _make_request()
        request.path = "/api/test"
        result = BaseLoggingMixin._get_path(request)
        assert result == "/api/test"


class TestGetViewName(SimpleTestCase):
    """Cover _get_view_name (lines 152-162)."""

    def test_returns_module_and_class_name(self):
        mixin = ConcreteLoggingMixin()
        request = _make_request(method="GET")

        # Create a mock method attribute on the mixin with __self__
        mock_handler = MagicMock()
        mock_handler.__self__ = mixin
        mixin.get = mock_handler

        result = mixin._get_view_name(request)
        expected_module = type(mixin).__module__
        expected_class = type(mixin).__name__
        assert result == f"{expected_module}.{expected_class}"

    def test_returns_none_when_no_method_attribute(self):
        mixin = ConcreteLoggingMixin()
        request = _make_request(method="DELETE")
        # mixin does not have a 'delete' attribute
        result = mixin._get_view_name(request)
        assert result is None


class TestGetViewMethod(SimpleTestCase):
    """Cover _get_view_method (lines 166-168)."""

    def test_returns_action_when_present(self):
        mixin = ConcreteLoggingMixin()
        mixin.action = "list"
        request = _make_request(method="GET")
        result = mixin._get_view_method(request)
        assert result == "list"

    def test_returns_none_when_action_is_none(self):
        mixin = ConcreteLoggingMixin()
        mixin.action = None
        request = _make_request(method="GET")
        result = mixin._get_view_method(request)
        assert result is None

    def test_returns_request_method_lower_when_no_action_attr(self):
        mixin = ConcreteLoggingMixin()
        # Ensure no 'action' attribute exists
        assert not hasattr(mixin, "action")
        request = _make_request(method="POST")
        result = mixin._get_view_method(request)
        assert result == "post"


class TestGetUsername(SimpleTestCase):
    """Cover _get_username (lines 183-186)."""

    def test_returns_username(self):
        request = _make_request()
        request.user.get_username.return_value = "testuser"
        result = BaseLoggingMixin._get_username(request)
        assert result == "testuser"

    def test_returns_none_when_no_user(self):
        request = _make_request()
        request.user = None
        result = BaseLoggingMixin._get_username(request)
        assert result is None


class TestGetResponseMs(SimpleTestCase):
    """Cover _get_response_ms (lines 193-195)."""

    def test_returns_non_negative_ms(self):
        mixin = ConcreteLoggingMixin()
        mixin.log = {"requested_at": now()}
        result = mixin._get_response_ms()
        assert result >= 0

    def test_returns_zero_for_future_requested_at(self):
        """If requested_at is somehow in the future, result should be 0."""
        mixin = ConcreteLoggingMixin()
        mixin.log = {"requested_at": now() + timedelta(seconds=10)}
        result = mixin._get_response_ms()
        assert result == 0


class TestBaseLoggingMixinHandleLog(SimpleTestCase):
    """Cover handle_log raising NotImplementedError (line 118)."""

    def test_raises_not_implemented(self):
        mixin = BaseLoggingMixin.__new__(BaseLoggingMixin)
        with self.assertRaises(NotImplementedError):
            mixin.handle_log()


class TestInitialMethod(SimpleTestCase):
    """Cover initial() method (lines 31-47)."""

    def test_initial_sets_log_data(self):
        mixin = ConcreteLoggingMixin()
        request = _make_request()
        request.body = b'{"key": "value"}'
        request.data = MagicMock()
        request.data.dict.return_value = {"key": "value"}  # pylint: disable=no-member
        mixin.request = request

        mixin.initial(request)

        assert mixin.log is not None
        assert "requested_at" in mixin.log
        assert "data" in mixin.log

    def test_initial_decode_request_body_false(self):
        """Cover the branch where decode_request_body is False (line 33)."""
        mixin = ConcreteLoggingMixin()
        mixin.decode_request_body = False
        request = _make_request()
        request.body = b'{"key": "value"}'
        request.data = MagicMock()
        request.data.dict.return_value = {"key": "value"}  # pylint: disable=no-member
        mixin.request = request

        mixin.initial(request)

        assert mixin.log["data"] is not None

    def test_initial_request_data_attributeerror(self):
        """Cover the AttributeError branch (lines 45-46) when request.data has no dict()."""
        mixin = ConcreteLoggingMixin()
        request = _make_request()
        request.body = b"raw data"
        request.data = {"already": "a dict"}
        mixin.request = request

        mixin.initial(request)

        assert mixin.log["data"] == {"already": "a dict"}


class TestHandleExceptionMethod(SimpleTestCase):
    """Cover handle_exception (lines 50-53)."""

    def test_handle_exception_stores_traceback(self):
        mixin = ConcreteLoggingMixin()
        mixin.log = {}

        mock_response = MagicMock()
        mock_response.status_code = 500

        exc = ValueError("test error")

        response = None
        with patch.object(FakeAPIView, "handle_exception", return_value=mock_response):
            try:
                raise exc
            except ValueError:
                response = mixin.handle_exception(exc)

        assert "ValueError: test error" in mixin.log["errors"]
        assert response == mock_response


class TestFinalizeResponse(SimpleTestCase):
    """Cover finalize_response (lines 56-110)."""

    def _make_finalize_mixin_and_request(self):
        """Helper to set up a mixin and request for finalize_response tests."""
        mixin = ConcreteLoggingMixin()
        mixin.log = {"requested_at": now(), "data": {}}

        request = _make_request()
        request.path = "/api/test"
        request.get_host.return_value = "localhost"
        request.query_params = MagicMock()
        request.query_params.dict.return_value = {"q": "search"}

        user = MagicMock()
        user.is_anonymous = False
        user.id = 1
        user.get_username.return_value = "admin"
        del user.profile
        request.user = user

        return mixin, request

    def test_finalize_response_full_flow(self):
        """Test the full finalize_response flow by actually calling the method."""
        mixin, request = self._make_finalize_mixin_and_request()

        response = MagicMock()
        response.status_code = 200
        response.streaming = False
        response.rendered_content = '{"result": "ok"}'
        response.exception = None

        with patch.object(
            FakeAPIView,
            "finalize_response",
            return_value=response,
        ):
            result = mixin.finalize_response(request, response)

        assert mixin.log["status_code"] == 200
        assert mixin.log["path"] == "/api/test"
        assert mixin.log["method"] == "GET"
        assert mixin.log["host"] == "localhost"
        assert result == response

    def test_finalize_response_streaming_response(self):
        """Cover the streaming branch (line 74)."""
        mixin, request = self._make_finalize_mixin_and_request()

        response = MagicMock()
        response.status_code = 200
        response.streaming = True
        response.exception = None

        with patch.object(
            FakeAPIView,
            "finalize_response",
            return_value=response,
        ):
            result = mixin.finalize_response(request, response)

        assert mixin.log["response"] is None
        assert result == response

    def test_finalize_response_getvalue_fallback(self):
        """Cover the getvalue() fallback (line 79)."""
        mixin, request = self._make_finalize_mixin_and_request()

        response = MagicMock(spec=["status_code", "streaming", "getvalue", "exception"])
        response.status_code = 200
        response.streaming = False
        response.getvalue.return_value = b"raw content"
        response.exception = None

        with patch.object(
            FakeAPIView,
            "finalize_response",
            return_value=response,
        ):
            result = mixin.finalize_response(request, response)

        assert result == response

    def test_finalize_response_empty_query_params_uses_data(self):
        """Cover the branch where query_params is empty (lines 99-100)."""
        mixin, request = self._make_finalize_mixin_and_request()
        mixin.log["data"] = {"key": "value"}
        request.query_params.dict.return_value = {}

        response = MagicMock()
        response.status_code = 200
        response.streaming = False
        response.rendered_content = '{"ok": true}'
        response.exception = None

        with patch.object(
            FakeAPIView,
            "finalize_response",
            return_value=response,
        ):
            mixin.finalize_response(request, response)

        assert mixin.log["query_params"] == {"key": "value"}

    def test_finalize_response_should_log_false(self):
        """Cover the branch where should_log returns False."""
        mixin, request = self._make_finalize_mixin_and_request()
        mixin.logging_methods = ["POST"]  # request is GET, so should_log returns False

        response = MagicMock()
        response.status_code = 200
        response.streaming = False

        with patch.object(
            FakeAPIView,
            "finalize_response",
            return_value=response,
        ):
            result = mixin.finalize_response(request, response)

        assert result == response
        # status_code should NOT be set since should_log is False
        assert "status_code" not in mixin.log

    def test_finalize_response_handle_log_exception(self):
        """Cover lines 103-106: handle_log raising exception is caught."""
        mixin, request = self._make_finalize_mixin_and_request()

        response = MagicMock()
        response.status_code = 200
        response.streaming = False
        response.rendered_content = '{"ok": true}'
        response.exception = None

        with patch.object(
            FakeAPIView,
            "finalize_response",
            return_value=response,
        ):
            with patch.object(
                mixin, "handle_log", side_effect=RuntimeError("db error")
            ):
                result = mixin.finalize_response(request, response)

        assert result == response

    def test_finalize_response_should_log_hook(self):
        """Cover the _should_log backward compatibility branch (line 60)."""
        mixin, request = self._make_finalize_mixin_and_request()
        mixin._should_log = MagicMock(
            return_value=False
        )  # pylint: disable=protected-access

        response = MagicMock()
        response.status_code = 200
        response.streaming = False

        with patch.object(
            FakeAPIView,
            "finalize_response",
            return_value=response,
        ):
            result = mixin.finalize_response(request, response)

        assert result == response

    def test_finalize_response_atomic_rollback(self):
        """Cover lines 72-73: set_rollback when ATOMIC_REQUESTS and exception."""
        mixin, request = self._make_finalize_mixin_and_request()

        response = MagicMock()
        response.status_code = 401
        response.streaming = False
        response.rendered_content = '{"error": "unauthorized"}'
        response.exception = True  # response has an exception

        mock_connection = MagicMock()
        mock_connection.settings_dict = {"ATOMIC_REQUESTS": True}
        mock_connection.in_atomic_block = True

        with patch.object(FakeAPIView, "finalize_response", return_value=response):
            with patch("qux.drf.log.base_mixins.connection", mock_connection):
                result = mixin.finalize_response(request, response)

        mock_connection.set_rollback.assert_any_call(True)
        mock_connection.set_rollback.assert_any_call(False)
        assert result == response


class TestLoggingMixinHandleLog(SimpleTestCase):
    """Cover LoggingMixin.handle_log (lines 16-28 in mixins.py)."""

    @patch("qux.drf.log.mixins.APIRequestLog")
    def test_handle_log_saves_log(self, mock_model):
        """Test that handle_log creates and saves an APIRequestLog."""
        mixin = LoggingMixin.__new__(LoggingMixin)
        setattr(mixin, "CLEANED_SUBSTITUTE", "********************")
        mixin.sensitive_fields = {}
        mixin.logging_methods = "__all__"
        mixin.log = {
            "path": "/api/test",
            "method": "GET",
            "status_code": 200,
        }
        mixin.handle_log()
        mock_model.assert_called_once_with(**mixin.log)
        mock_model.return_value.save.assert_called_once()

    @patch("qux.drf.log.mixins.APIRequestLog")
    def test_handle_log_pops_oversized_fields(self, mock_model):
        """Test that fields exceeding MAX_SIZE are removed."""
        mixin = LoggingMixin.__new__(LoggingMixin)
        setattr(mixin, "CLEANED_SUBSTITUTE", "********************")
        mixin.sensitive_fields = {}
        mixin.logging_methods = "__all__"

        # Create a large value that exceeds max_size (4096 default)
        large_value = "x" * 10000
        mixin.log = {
            "path": "/api/test",
            "response": large_value,
        }
        mixin.handle_log()
        # The large field should have been popped
        assert "response" not in mixin.log
        mock_model.assert_called_once()
        mock_model.return_value.save.assert_called_once()


class TestBaseAPIRequestLogStr(SimpleTestCase):
    """Cover BaseAPIRequestLog.__str__ (line 56 in base_models.py)."""

    def test_str_representation(self):
        instance = BaseAPIRequestLog.__new__(BaseAPIRequestLog)
        instance.method = "GET"
        instance.path = "/api/test"
        assert str(instance) == "GET /api/test"

    def test_str_post_method(self):
        instance = BaseAPIRequestLog.__new__(BaseAPIRequestLog)
        instance.method = "POST"
        instance.path = "/api/users/"
        assert str(instance) == "POST /api/users/"


class TestAPILogConfig(SimpleTestCase):
    """Cover apps.py for drf.log."""

    def test_app_config_attributes(self):
        assert APILogConfig.name == "qux.drf.log"
        assert APILogConfig.label == "qux_drf_log"
        assert APILogConfig.verbose_name == "REST Framework Tracking"


class TestDrfLogInit(SimpleTestCase):
    """Cover drf/log/__init__.py."""

    def test_version_and_default_app_config(self):
        assert hasattr(drf_log, "__version__")
        assert drf_log.default_app_config == "qux.drf.log.apps.APILogConfig"


class TestAPIRequestLogAdmin(SimpleTestCase):
    """Cover admin.py for drf.log (lines 50-101)."""

    def test_admin_class_attributes(self):
        assert APIRequestLogAdmin.date_hierarchy == "requested_at"
        assert "id" in APIRequestLogAdmin.list_display
        assert APIRequestLogAdmin.ordering == ("-requested_at",)

    @patch("qux.drf.log.admin.APIRequestLog")
    def test_changelist_view(self, mock_model):
        """Cover changelist_view (lines 50-62)."""
        mock_qs = MagicMock()
        mock_model.objects = mock_qs
        chained = mock_qs.annotate.return_value.values.return_value
        chained.annotate.return_value.order_by.return_value = [
            {"date": "2025-01-01", "y": 5}
        ]

        site = AdminSite()
        # We need a model to register - use MagicMock
        ma = APIRequestLogAdmin.__new__(APIRequestLogAdmin)
        ma.model = mock_model
        ma.admin_site = site
        ma.opts = MagicMock()

        request = MagicMock()
        request.method = "GET"
        request.GET = {}

        # Patch the super().changelist_view to avoid needing full admin setup
        with patch.object(
            type(ma).__bases__[0], "changelist_view", return_value="rendered"
        ) as mock_super:
            result = ma.changelist_view(request)
            mock_super.assert_called_once()
            assert result == "rendered"

    def test_get_urls(self):
        """Cover get_urls (lines 64-69)."""
        site = AdminSite()
        ma = APIRequestLogAdmin.__new__(APIRequestLogAdmin)
        ma.model = MagicMock()
        ma.admin_site = site
        ma.opts = MagicMock()
        ma.opts.app_label = "qux_drf_log"
        ma.opts.model_name = "apirequestlog"

        with patch.object(type(ma).__bases__[0], "get_urls", return_value=[]):
            urls = ma.get_urls()
            # Should have at least the chart_data URL
            assert len(urls) >= 1

    def test_chart_data_endpoint_missing_dates(self):
        """Cover chart_data_endpoint when dates are missing (line 78)."""
        ma = APIRequestLogAdmin.__new__(APIRequestLogAdmin)
        request = MagicMock()
        request.GET = {}

        response = ma.chart_data_endpoint(request)
        assert response.status_code == 400

    def test_chart_data_endpoint_invalid_dates(self):
        """Cover chart_data_endpoint with invalid date format (line 84)."""
        ma = APIRequestLogAdmin.__new__(APIRequestLogAdmin)
        request = MagicMock()
        request.GET = {"start_date": "not-a-date", "end_date": "also-bad"}

        response = ma.chart_data_endpoint(request)
        assert response.status_code == 400

    @patch("qux.drf.log.admin.APIRequestLog")
    def test_chart_data_endpoint_valid_dates(self, mock_model):
        """Cover chart_data_endpoint with valid dates (lines 86-87)."""
        mock_qs = MagicMock()
        mock_model.objects = mock_qs
        chained = mock_qs.filter.return_value.annotate.return_value.values.return_value
        chained.annotate.return_value.order_by.return_value = []

        ma = APIRequestLogAdmin.__new__(APIRequestLogAdmin)
        request = MagicMock()
        request.GET = {"start_date": "2025-01-01", "end_date": "2025-01-31"}

        response = ma.chart_data_endpoint(request)
        assert response.status_code == 200

    @patch("qux.drf.log.admin.APIRequestLog")
    def test_chart_data_method(self, mock_model):
        """Cover chart_data queryset method (lines 89-98)."""
        mock_qs = MagicMock()
        mock_model.objects = mock_qs
        chained = mock_qs.filter.return_value.annotate.return_value.values.return_value
        chained.annotate.return_value.order_by.return_value = [
            {"date": "2025-01-01", "y": 3}
        ]

        ma = APIRequestLogAdmin.__new__(APIRequestLogAdmin)
        start = datetime.date(2025, 1, 1)
        end = datetime.date(2025, 1, 31)
        _result = ma.chart_data(start, end)
        mock_model.objects.filter.assert_called_once()


class TestAdminReadonlyFields(SimpleTestCase):
    """Cover line 32: readonly_fields set when ADMIN_LOG_READONLY=True."""

    @override_settings(DRF_TRACKING_ADMIN_LOG_READONLY=True)
    def test_readonly_fields_set_when_setting_enabled(self):
        import importlib
        from django.contrib import admin as django_admin
        import qux.drf.log.admin as admin_module
        from qux.drf.log.models import APIRequestLog

        # Unregister before reload to avoid AlreadyRegistered
        try:
            django_admin.site.unregister(APIRequestLog)
        except django_admin.sites.NotRegistered:
            pass

        importlib.reload(admin_module)
        try:
            assert hasattr(admin_module.APIRequestLogAdmin, "readonly_fields")
            assert "user" in admin_module.APIRequestLogAdmin.readonly_fields
            assert "status_code" in admin_module.APIRequestLogAdmin.readonly_fields
        finally:
            # Unregister and reload again to restore original state
            try:
                django_admin.site.unregister(APIRequestLog)
            except django_admin.sites.NotRegistered:
                pass
            importlib.reload(admin_module)


class TestCoreModules(SimpleTestCase):
    """Cover core/__init__.py, core/apps.py, core/models/__init__.py."""

    def test_core_init_default_app_config(self):
        assert qux.core.default_app_config == "qux.core.apps.CoreConfig"

    def test_core_apps_config(self):
        assert CoreConfig.name == "qux.core"
        assert CoreConfig.label == "qux_core"
        assert CoreConfig.verbose_name == "QUX Core"

    def test_core_models_init_imports(self):
        """Importing qux.core.models triggers the try/except blocks."""
        # pylint: disable=import-outside-toplevel,unused-import,redefined-outer-name
        import qux.core.models  # noqa: F401

        # Just importing is enough to cover the try/except blocks
