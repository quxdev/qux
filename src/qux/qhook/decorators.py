import logging
from functools import wraps

from django.conf import settings

import requests

from .models import QHookTarget
from .serializers import QHookTargetSerializer

logger = logging.getLogger("qux")


def qhook(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug("QHOOK: %s", func.__name__)
        data_dict = func(*args, **kwargs)
        logger.debug("QHOOK: %s", data_dict)

        identifier = data_dict.get("identifier", None)
        if identifier is None:
            raise ValueError("Identifier is required")
        event = data_dict.get("event", None)
        if event is None:
            raise ValueError("Event is required")
        _hook = QHookTarget.objects.get_or_none(identifier=identifier)
        if _hook is None:
            raise LookupError("Hook not found")

        if not (event in settings.QHOOK_EVENTS and event == _hook.event):
            return

        data = {
            "hook": QHookTargetSerializer(_hook).data,
            "data": data_dict,
        }

        total_attempts = settings.QHOOK_MAX_ATTEMPTS

        while _hook.attempts < total_attempts:
            if call_target_url(_hook.target_url, data):
                _hook = _hook.success()
                break
            _hook = _hook.pending()

        if _hook.attempts >= total_attempts:
            _hook = _hook.fail()

    return wrapper


def call_target_url(target_url, data):
    resp = requests.post(target_url, json=data, timeout=30)
    return resp.status_code == 200
