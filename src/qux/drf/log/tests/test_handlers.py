"""Tests for ``qux.drf.log.handlers.APIRequestLogDBHandler``.

The handler bridges the new ``qux.drf`` logging channel back to the
``APIRequestLog`` ORM model — for projects that want feature parity with
the pre-2026 celery-backed pipeline.
"""

from __future__ import annotations

import logging
from unittest.mock import patch

from django.test import TestCase

from qux.drf.log.handlers import APIRequestLogDBHandler


class TestAPIRequestLogDBHandler(TestCase):
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

    def test_emit_writes_to_apirequestlog(self):
        handler = APIRequestLogDBHandler()
        rec = self._record(method="GET", path="/api/x", status_code=200)
        with patch("qux.drf.log.handlers.APIRequestLog") as mock_model:
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
        with patch("qux.drf.log.handlers.APIRequestLog") as mock_model:
            handler.emit(rec)
        kwargs = mock_model.call_args.kwargs
        self.assertNotIn("event", kwargs)
        self.assertNotIn("weird_key", kwargs)

    def test_emit_swallows_db_error(self):
        """Handler errors must never propagate (would break the request flow)."""
        handler = APIRequestLogDBHandler()
        rec = self._record(method="GET", path="/x", status_code=200)
        with patch("qux.drf.log.handlers.APIRequestLog", side_effect=RuntimeError("db down")):
            with patch.object(handler, "handleError") as on_error:
                handler.emit(rec)  # must not raise
            on_error.assert_called_once_with(rec)
