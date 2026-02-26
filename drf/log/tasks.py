from __future__ import annotations

import json
from typing import Any, Dict

from celery import shared_task

from .app_settings import app_settings
from .models import APIRequestLog


def _serialize_value(value: Any) -> str | Any:
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, default=str)
        except Exception:
            return str(value)
    return value


@shared_task(name="qux.drf.log.persist_api_log", queue=app_settings.LOG_QUEUE)
def persist_api_log(payload: Dict[str, Any]) -> None:
    sanitized: Dict[str, Any] = {}
    for key, value in payload.items():
        sanitized[key] = _serialize_value(value)

    APIRequestLog(**sanitized).save()
