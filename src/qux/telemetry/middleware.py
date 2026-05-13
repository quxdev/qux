"""QuxRequestIdMiddleware — anonymous per-request correlation + W3C trace context.

For every HTTP request:

- Generates a fresh ``request_id = uuid4().hex`` (32 hex chars, 128 bits) and
  stores it in a ContextVar so events emitted anywhere during the request
  (including signal handlers and inline ``events.emit`` calls without a
  ``request`` arg) can attach it.
- Parses the W3C ``traceparent`` header if upstream sent one and exposes
  ``trace_id`` + ``span_id`` for distributed-trace correlation. Qux does NOT
  start traces; it propagates context from upstream services that already use
  OTel/Datadog/Jaeger. Zero overhead when no header is present.

The middleware uses ``try/finally`` to clear the ContextVar after the response
so request N+1 in a reused worker process never sees request N's IDs.

**Middleware ordering is load-bearing.** This middleware MUST be the first
entry in ``MIDDLEWARE``, or at minimum before any middleware that might emit
qux events. ``QuxConfig.ready()`` warns if it isn't at index 0.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from uuid import uuid4

from . import _context

_log = logging.getLogger("qux")

# W3C traceparent format: version-traceid-parentid-flags
# https://www.w3.org/TR/trace-context/#traceparent-header-field-values
# Strict regex; malformed headers are silently ignored (we don't fail the request).
_TRACEPARENT_RE = re.compile(r"^([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


class QuxRequestIdMiddleware:
    """Set/clear request_id, trace_id, span_id ContextVars per request."""

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request):
        rid_token = _context.request_id.set(uuid4().hex)
        tid_token = _context.trace_id.set(None)
        sid_token = _context.span_id.set(None)
        try:
            traceparent = request.META.get("HTTP_TRACEPARENT")
            if traceparent:
                parsed = _parse_traceparent(traceparent)
                if parsed is not None:
                    trace_id, span_id = parsed
                    _context.trace_id.set(trace_id)
                    _context.span_id.set(span_id)
                else:
                    _log.debug("qux.telemetry: malformed traceparent header; skipping")
            return self.get_response(request)
        finally:
            _context.request_id.reset(rid_token)
            _context.trace_id.reset(tid_token)
            _context.span_id.reset(sid_token)


def _parse_traceparent(header_value: str) -> tuple[str, str] | None:
    """Parse a W3C traceparent header. Return (trace_id, span_id) or None."""
    match = _TRACEPARENT_RE.match(header_value.strip())
    if match is None:
        return None
    _version, trace_id, span_id, _flags = match.groups()
    # Spec: trace_id MUST NOT be all zeros; same for span_id.
    if trace_id == "0" * 32 or span_id == "0" * 16:
        return None
    return trace_id, span_id
