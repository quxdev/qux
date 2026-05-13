"""Top-level qux Django AppConfig.

Runtime responsibilities, all idempotent and best-effort (failures are logged
and swallowed so a broken sub-system can't prevent the rest of qux from loading):

1. Set ``boot_id`` ContextVar (anonymous per-process correlation key).
2. Unpack vendored static asset bundles (``src/qux/_assets/bundles/*.zip``).
3. Emit ``qux.startup`` (HTTP servers only) and ``qux.config.loaded`` lifecycle events.
4. Register a ``post_migrate`` handler that emits ``qux.migration.applied`` for qux apps.
5. Validate ``MIDDLEWARE`` ordering: ``QuxRequestIdMiddleware`` should be at index 0.

Asset unpack can be re-triggered manually via:

    qux-install-assets --force
"""

from __future__ import annotations

import logging
import os
import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from uuid import uuid4

from django.apps import AppConfig
from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_migrate

from qux._assets.install import install_all
from qux.telemetry import _context, events

_log = logging.getLogger("qux")


def _resolve_version() -> str:
    """Best-effort qux version string for telemetry lifecycle events."""
    try:
        return pkg_version("qux")
    except PackageNotFoundError:
        return "unknown"


def _is_http_server() -> bool:
    """True when this process is running an HTTP server.

    Detected from ``sys.argv[0]`` (runserver / gunicorn / uvicorn / daphne) or
    the ``QUX_TELEMETRY_FORCE_STARTUP=1`` env var for unusual deployments.
    One-shot management commands (``shell``, ``migrate``, ``test``) return False —
    they get ``boot_id`` for any lifecycle events they happen to emit, but no
    spurious ``qux.startup``.
    """
    if os.environ.get("QUX_TELEMETRY_FORCE_STARTUP") == "1":
        return True
    argv0 = (sys.argv[0] or "").lower()
    needles = ("runserver", "gunicorn", "uvicorn", "daphne", "asgi", "wsgi")
    if any(n in argv0 for n in needles):
        return True
    # `manage.py runserver` puts "manage.py" in argv[0] and "runserver" in argv[1].
    return bool(any(n in arg.lower() for arg in sys.argv[1:] for n in ("runserver",)))


class QuxConfig(AppConfig):
    name = "qux"
    label = "qux"
    verbose_name = "QUX"

    def ready(self) -> None:
        self._setup_boot_id()
        self._setup_assets()
        self._setup_telemetry_lifecycle()
        self._validate_middleware_ordering()

    def _setup_boot_id(self) -> None:
        """Set boot_id ContextVar — every lifecycle event from this process carries it."""
        _context.boot_id.set(uuid4().hex)

    def _setup_assets(self) -> None:
        """Unpack vendored asset bundles. Idempotent via per-bundle marker files."""
        try:
            install_all()
        except Exception as exc:
            _log.warning("qux asset unpack failed: %s; run `qux-install-assets`", exc)

    def _setup_telemetry_lifecycle(self) -> None:
        """Emit qux.startup (HTTP servers) and qux.config.loaded lifecycle events.

        Also registers a post_migrate handler that emits qux.migration.applied
        for migrations belonging to qux apps (filtered via app_config.name to
        avoid noise from the downstream's other apps).
        """
        version = _resolve_version()
        boot = _context.boot_id.get() or "unknown"

        if _is_http_server():
            try:
                events.startup(version=version, boot_id_value=boot, worker_pid=os.getpid())
            except Exception as exc:
                _log.warning("qux.startup emit failed: %s", exc)

        try:
            events.config_loaded(
                bootstrap=str(getattr(settings, "BOOTSTRAP", "bs4")),
                use_magic_link=bool(getattr(settings, "USE_MAGIC_LINK", False)),
                boot_id_value=boot,
            )
        except Exception as exc:
            _log.warning("qux.config.loaded emit failed: %s", exc)

        # post_login handler — qux.auth.login_success.
        def _on_user_logged_in(sender, request, user, **kwargs):
            try:
                events.auth_login_success()
            except Exception as exc:
                _log.debug("qux.auth.login_success emit failed: %s", exc)

        user_logged_in.connect(
            _on_user_logged_in,
            weak=False,
            dispatch_uid="qux.telemetry.auth_login_success",
        )

        # post_migrate handler — filtered to qux.* apps to avoid noise.
        def _on_post_migrate(sender, **kwargs):
            try:
                if not getattr(sender, "name", "").startswith("qux"):
                    return
                plan = kwargs.get("plan") or []
                for migration, was_rolled_back in plan:
                    if was_rolled_back:
                        continue
                    events.migration_applied(
                        app=sender.name,
                        qux_name=getattr(migration, "name", "unknown"),
                        boot_id_value=_context.boot_id.get() or "unknown",
                    )
            except Exception as exc:
                _log.debug("qux.migration.applied emit failed: %s", exc)

        post_migrate.connect(
            _on_post_migrate, weak=False, dispatch_uid="qux.telemetry.migration_applied"
        )

    def _validate_middleware_ordering(self) -> None:
        """Warn if QuxRequestIdMiddleware isn't first in MIDDLEWARE.

        It must be first (or at minimum before anything that emits qux events)
        so events fired during request handling carry a request_id.
        """
        middleware = list(getattr(settings, "MIDDLEWARE", ()) or ())
        target = "qux.telemetry.middleware.QuxRequestIdMiddleware"
        if target not in middleware:
            return  # not registered at all — operator's choice; nothing to warn about
        index = middleware.index(target)
        if index != 0:
            _log.warning(
                "qux.telemetry.middleware.QuxRequestIdMiddleware should be the first "
                "MIDDLEWARE entry (currently at index %d). Events emitted by middleware "
                "or signal handlers running before it will lack request_id.",
                index,
            )
