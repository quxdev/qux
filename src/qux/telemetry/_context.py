"""Per-process and per-request correlation IDs in ContextVars.

Set by :class:`qux.telemetry.middleware.QuxRequestIdMiddleware` for HTTP requests
and by :class:`qux.apps.QuxConfig` at boot. Read by :func:`qux.telemetry.events.emit`
when building the ``extra=`` payload.

ContextVars are the right primitive: they propagate through ``asyncio.Task``s,
work with Django's async views (4.x+), and middleware can clear them in a
``try/finally`` so request N+1 in a reused worker process never sees request N's IDs.
"""

from __future__ import annotations

import contextvars

# All four are anonymous, ephemeral, set/cleared by middleware or app startup.
# Default ``None`` so ``emit`` can omit them cleanly when no scope applies.
request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "qux_request_id", default=None
)
trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("qux_trace_id", default=None)
span_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("qux_span_id", default=None)
boot_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("qux_boot_id", default=None)
