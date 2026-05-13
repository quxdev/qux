"""JsonFormatter — one JSON object per line, ready for ``jq``.

Without this, operators pointing a ``FileHandler`` at the ``qux`` logger get
Python logging's default ``%(message)s`` format which DROPS the ``extra=``
dims — telemetry records arrive with the event name as a string and nothing
else, useless for ``jq``.

Why custom vs ``python-json-logger`` / ``structlog``: both libraries solve the
general case but the specifics qux needs (single-line guarantee for ``jq``,
type coercion for ORM/Decimal/UUID/Exception, ISO-8601 timestamps, stable
field order) require customization either way. Building it ourselves removes
a dependency at roughly the same LOC.
"""

from __future__ import annotations

import datetime
import decimal
import json
import logging
import uuid
from typing import Any

# LogRecord standard attrs we surface in the JSON object under shortened names.
# Anything not in this map and not in the event's extra= is dropped from output.
_STANDARD_ATTRS_MAP: dict[str, str] = {
    "levelname": "lvl",
    "name": "logger",
    "module": "module",
    "funcName": "func",
    "lineno": "line",
    "process": "pid",
    "thread": "tid",
    "message": "message",
    "exc_text": "exc",
}

# Standard LogRecord attrs (used to discriminate dim keys from base attrs).
# This is the same reserved set used in events.py's validation, plus a few
# extras that exist on every record by virtue of being a LogRecord.
_STANDARD_ATTRS = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "asctime",
    }
)


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per record, single-line guaranteed.

    Field order: ts, lvl, then the event/dim payload in insertion order, then
    standard attrs. Stable across calls so log diffs are readable.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Resolve the message (handles %-style and {} formatting).
        record.message = record.getMessage()
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)

        out: dict[str, Any] = {}
        out["ts"] = _iso_utc(record.created)
        out["lvl"] = record.levelname

        # Dims (everything in extra=) come next. Python sets them as attributes
        # on the record object directly. Distinguish dim keys from standard
        # LogRecord attrs by membership in _STANDARD_ATTRS.
        for key, value in record.__dict__.items():
            if key in _STANDARD_ATTRS:
                continue
            if key.startswith("_"):
                continue
            out[key] = _coerce(value)

        # Selected standard attrs at the end so dims dominate the eye.
        for std_key, json_key in _STANDARD_ATTRS_MAP.items():
            if std_key in {"message", "exc_text"}:
                continue  # handled below
            value = getattr(record, std_key, None)
            if value is not None and json_key not in out:
                out[json_key] = _coerce(value)

        # Message + exception text last. Both get newline-escaped so the whole
        # record is a single line — non-negotiable for jq stream-parsing.
        if record.message and "message" not in out:
            out["message"] = _escape_newlines(record.message)
        if record.exc_text:
            out["exc"] = _escape_newlines(record.exc_text)

        return json.dumps(out, ensure_ascii=False, separators=(",", ":"))


def _iso_utc(epoch_seconds: float) -> str:
    """Format epoch seconds as ISO-8601 UTC with millisecond precision."""
    dt = datetime.datetime.fromtimestamp(epoch_seconds, tz=datetime.timezone.utc)
    # Trim microseconds → milliseconds, append Z.
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def _escape_newlines(value: str) -> str:
    """Replace newlines, carriage returns, tabs with literal escapes.

    Multi-line tracebacks (from logger.exception) and any newline-bearing
    string in extra= would break one-record-per-line jq parsing. Escape all
    such characters so the formatted record is guaranteed single-line.
    """
    return (
        value.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    )


def _coerce(value: Any) -> Any:
    """Coerce non-JSON-serializable values to JSON-friendly forms.

    datetime → ISO-8601, Decimal → str, UUID → str, Exception → "ClassName: msg",
    bytes → repr, anything else with ``__str__`` → str fallback.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        if isinstance(value, str):
            return _escape_newlines(value)
        return value
    if isinstance(value, (list, tuple)):
        return [_coerce(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _coerce(v) for k, v in value.items()}
    if isinstance(value, datetime.datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=datetime.timezone.utc)
        return (
            value.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.")
            + f"{value.microsecond // 1000:03d}Z"
        )
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, uuid.UUID):
        return value.hex
    if isinstance(value, BaseException):
        return f"{type(value).__name__}: {value}"
    if isinstance(value, bytes):
        return repr(value)
    # Fallback: str() of the value (covers ORM model instances, custom objects).
    try:
        return _escape_newlines(str(value))
    except Exception:
        return f"<unrepresentable {type(value).__name__}>"
