"""Event-name constants (EVENTS) + named helper functions + ``emit``.

Single source of truth for what qux emits on the ``qux`` logger channel.
Operators read this file (or the README catalog) to know what's available.

Adding a new event:
    1. Add a constant to :class:`EVENTS`.
    2. Add a helper function below that calls ``emit(EVENTS.NEW_THING, ...)``.
    3. Add the call site in qux's code.
    4. Note the addition in CHANGELOG.md under ``## Telemetry catalog``.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from . import _context

# LogRecord standard attrs that can NEVER appear in extra= per Python's
# logging contract — passing one raises KeyError deep in Logger.makeRecord.
# Source: cpython Lib/logging/__init__.py LogRecord.__init__.
_RESERVED_LOGRECORD_ATTRS = frozenset(
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

# Reserved attrs that are ALSO natural payload field names. These get
# auto-renamed to ``qux_<name>`` instead of raising. Anything else in
# _RESERVED_LOGRECORD_ATTRS \ _AUTO_RENAME raises ValueError at emit time.
_AUTO_RENAME = frozenset({"name", "message", "module", "filename"})

# Whitelist of dim-name characters: lowercase alpha, digits, underscore only.
# Event NAMES use dots (qux.auth.login_failed); dim NAMES do not (some
# backends treat dotted dims as nested objects, others flat — ambiguous).
_DIM_NAME_RE = re.compile(r"^[a-z_][a-z0-9_]*$")


class EVENTS:
    """All event names qux emits. Import and use to avoid string typos.

    Usage:
        from qux.telemetry import EVENTS
        EVENTS.AUTH_LOGIN_SUCCESS  # "qux.auth.login_success"
    """

    # Lifecycle
    STARTUP = "qux.startup"
    ASSETS_UNPACKED = "qux.assets.unpacked"
    ASSETS_UNPACK_FAILED = "qux.assets.unpack_failed"
    MIGRATION_APPLIED = "qux.migration.applied"
    CONFIG_LOADED = "qux.config.loaded"

    # Auth — login
    AUTH_LOGIN_SUCCESS = "qux.auth.login_success"
    AUTH_LOGIN_FAILED = "qux.auth.login_failed"
    AUTH_SIGNUP = "qux.auth.signup"

    # Auth — magic link
    AUTH_MAGIC_LINK_REQUESTED = "qux.auth.magic_link.requested"
    AUTH_MAGIC_LINK_REFUSED = "qux.auth.magic_link.refused"
    AUTH_MAGIC_LINK_CONSUMED = "qux.auth.magic_link.consumed"

    # Auth — CLI OTP
    AUTH_CLI_OTP_ISSUED = "qux.auth.cli_otp.issued"
    AUTH_CLI_OTP_CONSUMED = "qux.auth.cli_otp.consumed"

    # Auth — password reset
    AUTH_PASSWORD_RESET_REQUESTED = "qux.auth.password_reset.requested"
    AUTH_PASSWORD_RESET_COMPLETED = "qux.auth.password_reset.completed"

    # Token
    TOKEN_CREATED = "qux.token.created"
    TOKEN_DELETED = "qux.token.deleted"

    @classmethod
    def all(cls) -> tuple[str, ...]:
        """Return a tuple of every registered event name. For introspection / tests."""
        return tuple(
            value
            for key, value in vars(cls).items()
            if not key.startswith("_") and isinstance(value, str)
        )


def emit(event_name: str, **dims: Any) -> None:
    """Emit one structured log record on the ``qux`` logger.

    Adds correlation IDs from ContextVars (request_id, trace_id, span_id, boot_id)
    when they're set. Defensively handles reserved-name collisions in ``dims``.

    Args:
        event_name: One of the strings in :class:`EVENTS`.
        **dims: Categorical / scalar payload. Validated against:
            (a) reserved LogRecord attrs (auto-renamed or rejected),
            (b) dim-name regex (lowercase + underscores only).
    """
    safe_dims = _validate_dims(dims)
    safe_dims["event"] = event_name

    # Correlation IDs (only included when set in scope).
    rid = _context.request_id.get()
    if rid is not None:
        safe_dims["request_id"] = rid
    tid = _context.trace_id.get()
    if tid is not None:
        safe_dims["trace_id"] = tid
    sid = _context.span_id.get()
    if sid is not None:
        safe_dims["span_id"] = sid
    bid = _context.boot_id.get()
    if bid is not None and "boot_id" not in safe_dims:
        # Lifecycle events pass boot_id explicitly (kept for clarity); other
        # events get it from context only if the helper requested it.
        pass

    logging.getLogger("qux").info(event_name, extra=safe_dims)


def _validate_dims(dims: dict[str, Any]) -> dict[str, Any]:
    """Validate dim names and resolve reserved-attr collisions.

    Auto-rename for known natural names that clash (`name`, `message`, etc.) →
    ``qux_<name>``. Raise ``ValueError`` for any other reserved-attr collision
    or invalid dim name. Catches the bug at emit time with a clear message
    instead of an opaque KeyError deep in ``Logger.makeRecord``.
    """
    safe: dict[str, Any] = {}
    for key, value in dims.items():
        if key in _AUTO_RENAME:
            safe[f"qux_{key}"] = value
            continue
        if key in _RESERVED_LOGRECORD_ATTRS:
            raise ValueError(
                f"qux.telemetry: dim name {key!r} shadows a reserved logging.LogRecord "
                f"attr; pick a different name. Reserved attrs that can never appear in "
                f"extra=: {sorted(_RESERVED_LOGRECORD_ATTRS)}"
            )
        if not _DIM_NAME_RE.match(key):
            raise ValueError(
                f"qux.telemetry: dim name {key!r} is invalid; must match "
                f"^[a-z_][a-z0-9_]*$ (lowercase, underscores; no dots — backends "
                f"differ on dotted-key handling)."
            )
        safe[key] = value
    return safe


# ---------- Named helpers (one per event) ----------
# Each helper hardcodes its event constant + payload schema. Centralizing here
# means call sites stay one-liner and the catalog can't drift via copy-paste.

# --- Lifecycle ---


def startup(version: str, boot_id_value: str, worker_pid: int) -> None:
    """qux.startup — fired once per HTTP-server worker process boot."""
    emit(EVENTS.STARTUP, version=version, boot_id=boot_id_value, worker_pid=worker_pid)


def assets_unpack_failed(bundle: str, error_class: str, boot_id_value: str) -> None:
    """qux.assets.unpack_failed — bundle extraction raised."""
    emit(
        EVENTS.ASSETS_UNPACK_FAILED,
        ok=False,
        bundle=bundle,
        error_class=error_class,
        boot_id=boot_id_value,
    )


def migration_applied(app: str, qux_name: str, boot_id_value: str) -> None:
    """qux.migration.applied — post_migrate handler, filtered to qux apps.

    ``qux_name`` is the migration's name (e.g. ``0001_initial``). Renamed from
    ``name`` because ``name`` clashes with LogRecord's reserved attr.
    """
    emit(EVENTS.MIGRATION_APPLIED, app=app, qux_name=qux_name, boot_id=boot_id_value)


def config_loaded(bootstrap: str, use_magic_link: bool, boot_id_value: str) -> None:
    """qux.config.loaded — fired once per boot after settings inspected.

    Lifecycle event: emits exactly once per boot. Operators filter it out of
    routine queries; useful for "what was qux configured as during deploy X."
    """
    emit(
        EVENTS.CONFIG_LOADED,
        bootstrap=bootstrap,
        use_magic_link=use_magic_link,
        boot_id=boot_id_value,
    )


# --- Auth — login ---


def auth_login_success() -> None:
    """qux.auth.login_success — sibling of failed; fires from post_login signal."""
    emit(EVENTS.AUTH_LOGIN_SUCCESS, ok=True)


def auth_login_failed(reason: str) -> None:
    """qux.auth.login_failed — reason is one of bad_credentials / inactive / locked / unknown.

    Django's default authentication form does NOT distinguish bad-password
    from unknown-user (deliberate: avoids leaking which accounts exist). Both
    bucket into ``bad_credentials``.
    """
    emit(EVENTS.AUTH_LOGIN_FAILED, ok=False, reason=reason)


def auth_signup() -> None:
    """qux.auth.signup — success branch only."""
    emit(EVENTS.AUTH_SIGNUP, ok=True)


# --- Auth — magic link ---


def auth_magic_link_requested() -> None:
    """qux.auth.magic_link.requested — request was honored (link sent)."""
    emit(EVENTS.AUTH_MAGIC_LINK_REQUESTED, ok=True)


def auth_magic_link_refused(reason: str) -> None:
    """qux.auth.magic_link.refused — reason: rate_limit / blocked_domain / bot_check."""
    emit(EVENTS.AUTH_MAGIC_LINK_REFUSED, ok=False, reason=reason)


# --- Auth — CLI OTP ---


def auth_cli_otp_issued(ttl_seconds: int) -> None:
    """qux.auth.cli_otp.issued — OTP code generated and emailed."""
    emit(EVENTS.AUTH_CLI_OTP_ISSUED, ok=True, ttl_seconds=ttl_seconds)
