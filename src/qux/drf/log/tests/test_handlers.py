"""Tests for ``qux.drf.log.handlers.APIRequestLogDBHandler``.

The handler bridges the new ``qux.drf`` logging channel back to the
``APIRequestLog`` ORM model — for projects that want feature parity with
the pre-2026 celery-backed pipeline.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

from django.test import TestCase

from qux.drf.log.handlers import APIRequestLogDBHandler, _log_model_and_fields

_KNOWN_FIELDS = frozenset(["method", "path", "status_code"])


class TestAPIRequestLogDBHandler(TestCase):
    def setUp(self):
        _log_model_and_fields.cache_clear()

    def tearDown(self):
        _log_model_and_fields.cache_clear()

    def _record(self, **extra) -> logging.LogRecord:
        rec = logging.LogRecord(
            name="qux.drf",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="request",
            args=(),
            exc_info=None,
        )
        for key, value in extra.items():
            setattr(rec, key, value)
        return rec

    def _make_mock_model(self, fields=None):
        mock_model = MagicMock()
        return mock_model, fields or _KNOWN_FIELDS

    def test_emit_writes_to_apirequestlog(self):
        handler = APIRequestLogDBHandler()
        rec = self._record(method="GET", path="/api/x", status_code=200)
        mock_model, fields = self._make_mock_model()
        with patch(
            "qux.drf.log.handlers._log_model_and_fields", return_value=(mock_model, fields)
        ):
            handler.emit(rec)
        mock_model.assert_called_once()
        kwargs = mock_model.call_args.kwargs
        self.assertEqual(kwargs["method"], "GET")
        self.assertEqual(kwargs["path"], "/api/x")
        self.assertEqual(kwargs["status_code"], 200)
        mock_model.return_value.save.assert_called_once()

    def test_emit_filters_unknown_keys(self):
        """Stray extra= keys (event, custom dims) shouldn't crash the model constructor."""
        handler = APIRequestLogDBHandler()
        rec = self._record(method="GET", path="/x", status_code=200, event="request", weird_key="x")
        mock_model, fields = self._make_mock_model()
        with patch(
            "qux.drf.log.handlers._log_model_and_fields", return_value=(mock_model, fields)
        ):
            handler.emit(rec)
        kwargs = mock_model.call_args.kwargs
        self.assertNotIn("event", kwargs)
        self.assertNotIn("weird_key", kwargs)

    def test_emit_swallows_db_error(self):
        """Handler errors must never propagate (would break the request flow)."""
        handler = APIRequestLogDBHandler()
        rec = self._record(method="GET", path="/x", status_code=200)
        mock_model = MagicMock(side_effect=RuntimeError("db down"))
        with patch(
            "qux.drf.log.handlers._log_model_and_fields",
            return_value=(mock_model, _KNOWN_FIELDS),
        ):
            with patch.object(handler, "handleError") as on_error:
                handler.emit(rec)  # must not raise
            on_error.assert_called_once_with(rec)
