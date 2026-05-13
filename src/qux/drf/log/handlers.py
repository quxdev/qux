"""Opt-in logging handlers for ``qux.drf`` records.

``APIRequestLogDBHandler`` writes each log record to the ``APIRequestLog`` ORM
model — feature parity with the pre-2026 celery-backed pipeline, exposed as
a standard ``logging.Handler`` so projects opt in via ``LOGGING`` config:

    LOGGING = {
        "version": 1,
        "handlers": {
            "qux_drf_db": {"class": "qux.drf.log.handlers.APIRequestLogDBHandler"},
        },
        "loggers": {
            "qux.drf": {"handlers": ["qux_drf_db"], "level": "INFO", "propagate": False},
        },
    }

Without this handler wired, ``qux.drf.LoggingMixin`` only emits log records;
no DB rows are written. Projects that prefer file/JSON/ELK sinks attach
their own handler to the ``qux.drf`` channel instead.
"""

from __future__ import annotations

import logging

from .models import APIRequestLog

# Fields APIRequestLog accepts as model kwargs. ``handle_log`` adds many
# attrs to the LogRecord via extra=; we filter to known model fields so a
# stray extra key doesn't TypeError the constructor.
_MODEL_FIELDS = frozenset(f.name for f in APIRequestLog._meta.get_fields() if hasattr(f, "attname"))


class APIRequestLogDBHandler(logging.Handler):
    """Persists qux.drf log records to the APIRequestLog table.

    Synchronous INSERT per record. Operators who need async dispatch wrap
    this in a `QueueHandler` + listener thread, or use a different sink.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            payload = {k: v for k, v in record.__dict__.items() if k in _MODEL_FIELDS}
            APIRequestLog(**payload).save()
        except Exception:
            self.handleError(record)
