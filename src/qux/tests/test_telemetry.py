"""Tests for qux.telemetry — emission, EVENTS constants, middleware,
reserved-name protection, JsonFormatter.

Assertions scope to event NAMES (not exact record counts) so the suite
survives parallel test runners without flaking from cross-test record
cross-talk on the process-global ``qux`` logger.
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

from django.test import RequestFactory, SimpleTestCase

from qux.telemetry import EVENTS, JsonFormatter, QuxRequestIdMiddleware, _context, emit
from qux.telemetry._decorator import qux_event
from qux.telemetry.events import _AUTO_RENAME, _RESERVED_LOGRECORD_ATTRS

# --- EVENTS constants ---


class TestEventsCatalog(SimpleTestCase):
    """EVENTS class is the single source of truth for event names."""

    def test_constants_match_their_string_values(self):
        # Spot-check a few — full enumeration is via EVENTS.all() below.
        self.assertEqual(EVENTS.AUTH_LOGIN_SUCCESS, "qux.auth.login_success")
        self.assertEqual(EVENTS.STARTUP, "qux.startup")
        self.assertEqual(EVENTS.TOKEN_CREATED, "qux.token.created")

    def test_all_returns_every_string_constant(self):
        names = EVENTS.all()
        self.assertGreaterEqual(len(names), 17)  # initial catalog size
        for name in names:
            self.assertTrue(
                name.startswith("qux."),
                f"event name {name!r} must start with 'qux.'",
            )

    def test_no_duplicate_event_names(self):
        names = EVENTS.all()
        self.assertEqual(len(names), len(set(names)), "duplicate event names in EVENTS")


# --- emit() and reserved-name protection ---


class TestEmit(SimpleTestCase):
    """events.emit emits structured records on the qux logger."""

    def test_emit_appears_on_qux_logger(self):
        with self.assertLogs("qux", level=logging.INFO) as cm:
            emit(EVENTS.AUTH_LOGIN_SUCCESS, ok=True)
        events_seen = [r.event for r in cm.records if hasattr(r, "event")]
        self.assertIn(EVENTS.AUTH_LOGIN_SUCCESS, events_seen)

    def test_emit_attaches_dims_to_extra(self):
        with self.assertLogs("qux", level=logging.INFO) as cm:
            emit(EVENTS.AUTH_LOGIN_FAILED, ok=False, reason="bad_credentials")
        record = next(
            r for r in cm.records if getattr(r, "event", None) == EVENTS.AUTH_LOGIN_FAILED
        )
        self.assertEqual(record.ok, False)
        self.assertEqual(record.reason, "bad_credentials")


class TestReservedNameProtection(SimpleTestCase):
    """events.emit must defensively handle dim names that clash with LogRecord."""

    def test_message_dim_auto_renames_to_qux_message(self):
        with self.assertLogs("qux", level=logging.INFO) as cm:
            emit(EVENTS.AUTH_SIGNUP, message="welcome aboard")
        record = next(r for r in cm.records if getattr(r, "event", None) == EVENTS.AUTH_SIGNUP)
        # message → qux_message per _AUTO_RENAME map.
        self.assertEqual(record.qux_message, "welcome aboard")

    def test_name_dim_auto_renames(self):
        with self.assertLogs("qux", level=logging.INFO) as cm:
            emit(EVENTS.MIGRATION_APPLIED, name="0001_initial")
        record = next(
            r for r in cm.records if getattr(r, "event", None) == EVENTS.MIGRATION_APPLIED
        )
        self.assertEqual(record.qux_name, "0001_initial")

    def test_unknown_reserved_attr_raises_at_emit_time(self):
        # `pathname` is reserved and NOT in the auto-rename map → ValueError.
        with self.assertRaises(ValueError) as ctx:
            emit(EVENTS.AUTH_SIGNUP, pathname="/tmp/something")
        self.assertIn("reserved", str(ctx.exception).lower())

    def test_every_unrenamed_reserved_attr_raises(self):
        for attr in _RESERVED_LOGRECORD_ATTRS - _AUTO_RENAME:
            with self.subTest(attr=attr), self.assertRaises(ValueError):
                emit(EVENTS.AUTH_SIGNUP, **{attr: "x"})

    def test_dim_name_with_dots_raises(self):
        with self.assertRaises(ValueError) as ctx:
            emit(EVENTS.AUTH_SIGNUP, **{"a.b": 1})
        self.assertIn("a.b", str(ctx.exception))

    def test_dim_name_with_uppercase_raises(self):
        with self.assertRaises(ValueError):
            emit(EVENTS.AUTH_SIGNUP, BadName=1)


# --- @qux_event decorator ---


class TestQuxEventDecorator(SimpleTestCase):
    """The internal qux_event decorator emits ok=True on return, ok=False on raise."""

    def test_emits_ok_true_on_normal_return(self):
        @qux_event(
            EVENTS.TOKEN_CREATED, provider="ses", to_count=1
        )  # provider/to_count: arbitrary dims for the decorator test
        def succeed():
            return "result"

        with self.assertLogs("qux", level=logging.INFO) as cm:
            result = succeed()
        self.assertEqual(result, "result")
        rec = next(r for r in cm.records if getattr(r, "event", None) == EVENTS.TOKEN_CREATED)
        self.assertTrue(rec.ok)
        self.assertEqual(rec.provider, "ses")

    def test_emits_ok_false_on_exception_then_re_raises(self):
        @qux_event(
            EVENTS.TOKEN_CREATED, provider="ses", to_count=1
        )  # provider/to_count: arbitrary dims for the decorator test
        def boom():
            raise RuntimeError("kaboom")

        with self.assertLogs("qux", level=logging.INFO) as cm, self.assertRaises(RuntimeError):
            boom()
        rec = next(r for r in cm.records if getattr(r, "event", None) == EVENTS.TOKEN_CREATED)
        self.assertFalse(rec.ok)
        self.assertEqual(rec.error_class, "RuntimeError")

    def test_decorator_does_not_swallow_handler_errors_silently(self):
        # A handler that raises should NOT prevent the wrapped function from returning.
        @qux_event(EVENTS.AUTH_SIGNUP)
        def succeed():
            return 42

        bad_handler = logging.Handler()
        bad_handler.emit = MagicMock(side_effect=RuntimeError("handler broken"))
        bad_handler.setLevel(logging.DEBUG)
        logger = logging.getLogger("qux")
        logger.addHandler(bad_handler)
        try:
            result = succeed()  # must NOT raise
            self.assertEqual(result, 42)
        finally:
            logger.removeHandler(bad_handler)


# --- Middleware ---


class TestRequestIdMiddleware(SimpleTestCase):
    """QuxRequestIdMiddleware sets and clears ContextVars per request."""

    def setUp(self):
        self.factory = RequestFactory()
        # Clean slate — an earlier test may have left state.
        try:
            _context.request_id.set(None)
            _context.trace_id.set(None)
            _context.span_id.set(None)
        except Exception:
            pass

    def test_request_id_set_and_cleared(self):
        captured: dict[str, str | None] = {}

        def view(request):
            captured["rid"] = _context.request_id.get()
            return MagicMock(status_code=200)

        middleware = QuxRequestIdMiddleware(view)
        middleware(self.factory.get("/"))

        self.assertIsNotNone(captured["rid"])
        self.assertEqual(len(captured["rid"]), 32, "request_id must be full uuid4().hex")
        # After the response, ContextVar is cleared back to None.
        self.assertIsNone(_context.request_id.get())

    def test_traceparent_well_formed_populates_trace_and_span(self):
        captured: dict[str, str | None] = {}

        def view(request):
            captured["trace_id"] = _context.trace_id.get()
            captured["span_id"] = _context.span_id.get()
            return MagicMock(status_code=200)

        middleware = QuxRequestIdMiddleware(view)
        request = self.factory.get(
            "/", HTTP_TRACEPARENT="00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
        )
        middleware(request)

        self.assertEqual(captured["trace_id"], "0af7651916cd43dd8448eb211c80319c")
        self.assertEqual(captured["span_id"], "b7ad6b7169203331")

    def test_traceparent_malformed_does_not_raise(self):
        captured: dict[str, str | None] = {}

        def view(request):
            captured["trace_id"] = _context.trace_id.get()
            captured["span_id"] = _context.span_id.get()
            return MagicMock(status_code=200)

        middleware = QuxRequestIdMiddleware(view)
        # Garbage header.
        request = self.factory.get("/", HTTP_TRACEPARENT="not-a-real-traceparent")
        middleware(request)

        self.assertIsNone(captured["trace_id"])
        self.assertIsNone(captured["span_id"])

    def test_traceparent_all_zeros_rejected(self):
        captured: dict[str, str | None] = {}

        def view(request):
            captured["trace_id"] = _context.trace_id.get()
            return MagicMock(status_code=200)

        middleware = QuxRequestIdMiddleware(view)
        request = self.factory.get("/", HTTP_TRACEPARENT="00-" + "0" * 32 + "-" + "0" * 16 + "-01")
        middleware(request)
        self.assertIsNone(captured["trace_id"])

    def test_consecutive_requests_get_distinct_request_ids(self):
        ids: list[str | None] = []

        def view(request):
            ids.append(_context.request_id.get())
            return MagicMock(status_code=200)

        middleware = QuxRequestIdMiddleware(view)
        middleware(self.factory.get("/"))
        middleware(self.factory.get("/"))

        self.assertEqual(len(ids), 2)
        self.assertNotEqual(ids[0], ids[1])

    def test_request_id_cleared_on_view_exception(self):
        def view(request):
            raise RuntimeError("view crashed")

        middleware = QuxRequestIdMiddleware(view)
        with self.assertRaises(RuntimeError):
            middleware(self.factory.get("/"))
        # try/finally must clear even on exception.
        self.assertIsNone(_context.request_id.get())

    def test_emit_during_request_includes_request_id(self):
        captured_record: dict[str, logging.LogRecord] = {}

        def view(request):
            with self.assertLogs("qux", level=logging.INFO) as cm:
                emit(EVENTS.AUTH_LOGIN_SUCCESS, ok=True)
            captured_record["r"] = next(
                r for r in cm.records if getattr(r, "event", None) == EVENTS.AUTH_LOGIN_SUCCESS
            )
            return MagicMock(status_code=200)

        middleware = QuxRequestIdMiddleware(view)
        middleware(self.factory.get("/"))
        self.assertTrue(hasattr(captured_record["r"], "request_id"))
        self.assertEqual(len(captured_record["r"].request_id), 32)


# --- JsonFormatter ---


class TestJsonFormatter(SimpleTestCase):
    """JsonFormatter emits one JSON object per line, single-line guaranteed."""

    def setUp(self):
        self.formatter = JsonFormatter()

    def _make_record(self, msg: str = "hi", **extra) -> logging.LogRecord:
        record = logging.LogRecord(
            name="qux",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg=msg,
            args=(),
            exc_info=None,
        )
        for key, value in extra.items():
            setattr(record, key, value)
        return record

    def test_output_is_single_line_json(self):
        out = self.formatter.format(self._make_record(event="qux.test", ok=True))
        self.assertNotIn("\n", out)
        parsed = json.loads(out)
        self.assertEqual(parsed["event"], "qux.test")
        self.assertTrue(parsed["ok"])

    def test_multi_line_message_is_escaped_to_single_line(self):
        out = self.formatter.format(self._make_record(msg="line1\nline2\nline3", event="qux.test"))
        self.assertEqual(out.count("\n"), 0, "formatted output must be single-line")
        parsed = json.loads(out)
        self.assertIn("line1", parsed["message"])
        self.assertIn("line2", parsed["message"])
        self.assertIn("\\n", out)  # literal backslash-n in the JSON output

    def test_traceback_is_escaped_to_single_line(self):
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            record = logging.LogRecord(
                name="qux",
                level=logging.ERROR,
                pathname=__file__,
                lineno=1,
                msg="caught",
                args=(),
                exc_info=sys.exc_info(),
            )
        out = self.formatter.format(record)
        self.assertEqual(out.count("\n"), 0)
        parsed = json.loads(out)
        self.assertIn("RuntimeError", parsed["exc"])

    def test_datetime_coerced_to_iso8601(self):
        dt = datetime(2026, 5, 9, 18, 42, 1, 123000, tzinfo=timezone.utc)
        out = self.formatter.format(self._make_record(event="qux.test", when=dt))
        parsed = json.loads(out)
        self.assertEqual(parsed["when"], "2026-05-09T18:42:01.123Z")

    def test_decimal_coerced_to_string(self):
        out = self.formatter.format(self._make_record(event="qux.test", price=Decimal("19.99")))
        parsed = json.loads(out)
        self.assertEqual(parsed["price"], "19.99")

    def test_uuid_coerced_to_hex(self):
        u = uuid.uuid4()
        out = self.formatter.format(self._make_record(event="qux.test", id_=u))
        parsed = json.loads(out)
        self.assertEqual(parsed["id_"], u.hex)

    def test_exception_value_coerced(self):
        exc = ValueError("bad input")
        out = self.formatter.format(self._make_record(event="qux.test", err=exc))
        parsed = json.loads(out)
        self.assertEqual(parsed["err"], "ValueError: bad input")

    def test_date_coerced_to_iso(self):
        out = self.formatter.format(self._make_record(event="qux.test", when=date(2026, 5, 9)))
        parsed = json.loads(out)
        self.assertEqual(parsed["when"], "2026-05-09")

    def test_ts_field_iso_utc_with_milliseconds(self):
        record = self._make_record(event="qux.test")
        out = self.formatter.format(record)
        parsed = json.loads(out)
        # YYYY-MM-DDTHH:MM:SS.mmmZ
        self.assertRegex(parsed["ts"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
