"""Internal: ``qux_event`` decorator backing the named helpers in events.py.

NOT exported from ``qux.telemetry.__init__``. Downstream that wants telemetry
uses stdlib ``logging`` directly. Qux does not ship a public decorator API.

Behavior:
- Wraps a function. On normal return → emit with ``ok=True``.
- On exception → emit with ``ok=False`` (and ``error_class`` for triage), then re-raise.
- Telemetry never raises into the wrapped function. If logging is broken
  (handler raises with ``logging.raiseExceptions=True``), the wrapped call
  still returns its result.
"""

from __future__ import annotations

import contextlib
import functools
import logging
from collections.abc import Callable
from typing import Any, TypeVar

from .events import emit

F = TypeVar("F", bound=Callable[..., Any])


def qux_event(event_name: str, **default_dims: Any) -> Callable[[F], F]:
    """Decorate a function so each call emits ``event_name`` on logger ``qux``.

    ``default_dims`` are merged into the event's ``extra=`` payload on every
    call. The wrapped function's args/kwargs are NOT inspected — telemetry
    payloads are deliberately decoupled from function signatures so refactors
    don't quietly change the schema.
    """

    def decorate(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                result = func(*args, **kwargs)
            except BaseException as exc:
                _emit(event_name, ok=False, error_class=type(exc).__name__, **default_dims)
                raise
            _emit(event_name, ok=True, **default_dims)
            return result

        return wrapper  # type: ignore[return-value]

    return decorate


def _emit(event_name: str, **dims: Any) -> None:
    """Internal emit. Telemetry must never raise into the wrapped function."""
    try:
        emit(event_name, **dims)
    except Exception:
        # Best-effort log. If the logging path itself is broken, swallow —
        # the wrapped function's behavior takes precedence over observability.
        with contextlib.suppress(Exception):
            logging.getLogger("qux").exception("qux.telemetry: emit failed (swallowed)")
