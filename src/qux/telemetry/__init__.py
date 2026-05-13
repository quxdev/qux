"""qux.telemetry — structured event emission on the ``qux`` logger channel.

Single-channel design: everything qux emits (telemetry events, internal logs,
lifecycle, asset unpack messages) goes through ``logging.getLogger("qux")``.
Operators wire one handler and get every signal qux produces. See
``src/qux/telemetry/README.md`` for the catalog and setup recipes.

Public surface (everything else is internal):

- :class:`EVENTS` — string constants for every event qux can emit.
- :func:`events.emit` — inline emission helper for conditional/branched events.
- :func:`events.<helper>` — named helpers per event (catalog single-source).
- :class:`JsonFormatter` — single-line JSON formatter for ``LOGGING['formatters']``.
- :class:`QuxRequestIdMiddleware` — per-request correlation + W3C trace propagation.

NOT exported (intentional): the internal ``qux_event`` decorator. Downstream
that wants their own telemetry uses stdlib ``logging`` directly.
"""

from __future__ import annotations

from . import events  # re-export the module so callers can `from qux.telemetry import events`
from .events import EVENTS, emit
from .formatter import JsonFormatter
from .middleware import QuxRequestIdMiddleware

__all__ = [
    "EVENTS",
    "JsonFormatter",
    "QuxRequestIdMiddleware",
    "emit",
    "events",
]
