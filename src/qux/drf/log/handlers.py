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

``APIRequestLogDBHandler`` is safe to reference in ``LOGGING`` config before
Django's app registry is ready (i.e. before ``django.setup()`` completes).
The model import and ``_meta`` introspection are deferred to the first
``emit()`` call, by which point the registry is fully initialised.
"""

from __future__ import annotations

import logging
from functools import lru_cache


@lru_cache(maxsize=1)
def _log_model_and_fields() -> tuple[type, frozenset[str]]:
    """Return ``(APIRequestLog, frozenset_of_field_names)`` — resolved once.

    Deferred past module import so LOGGING config can reference this handler
    before ``django.setup()`` completes without triggering
    ``AppRegistryNotReady``.
    """
    from .models import APIRequestLog

    fields = frozenset(f.name for f in APIRequestLog._meta.get_fields() if hasattr(f, "attname"))
    return APIRequestLog, fields


class APIRequestLogDBHandler(logging.Handler):
    """Persists qux.drf log records to the APIRequestLog table.

    Safe to reference in ``LOGGING`` config before ``django.setup()``
    completes — model access is deferred to the first ``emit()`` call.

    Synchronous INSERT per record. Operators who need async dispatch wrap
    this in a ``QueueHandler`` + listener thread, or use a different sink.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            model, fields = _log_model_and_fields()
            payload = {k: v for k, v in record.__dict__.items() if k in fields}
            model(**payload).save()
        except Exception:
            self.handleError(record)
