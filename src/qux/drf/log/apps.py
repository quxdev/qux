import logging

from django.apps import AppConfig


class APILogConfig(AppConfig):
    name = "qux.drf.log"
    label = "qux_drf_log"
    verbose_name = "REST Framework Tracking"
    default = True

    def ready(self):
        # Signal connection imports models — must defer until Django finishes
        # loading apps (i.e., until ready() fires). Hoisting to module top
        # triggers AppRegistryNotReady during INSTALLED_APPS processing.
        from .signals import Signals

        try:
            Signals.connect()
        except Exception as exc:  # pragma: no cover - defensive logging only
            logging.getLogger("qux").warning("Failed to connect API logging signals: %s", exc)
