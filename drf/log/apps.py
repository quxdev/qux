import logging

from django.apps import AppConfig


class APILogConfig(AppConfig):
    name = "qux.drf.log"
    label = "qux_drf_log"
    verbose_name = "REST Framework Tracking"

    def ready(self):
        from .signals import Signals

        try:
            Signals.connect()
        except Exception as exc:  # pragma: no cover - defensive logging only
            logging.getLogger(__name__).warning(
                "Failed to connect API logging signals: %s", exc
            )
