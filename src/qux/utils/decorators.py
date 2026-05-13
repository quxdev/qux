"""Decorators for Django views and helper functions.

``qux_debug`` — wraps a function and, when ``settings.DEBUG`` is True, logs
the call site (file, line, function) and bound argument values at DEBUG level
on the ``qux`` logger. No-op when DEBUG is False — safe to leave on
production-deployed code.
"""

import inspect
import logging
import os
from functools import wraps

from django.conf import settings

logger = logging.getLogger("qux")


def qux_debug(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not settings.DEBUG:
            return func(*args, **kwargs)

        func_args = inspect.signature(func).bind(*args, **kwargs).arguments
        func_args_str = ", ".join(f"{k} = {v!r}" for k, v in func_args.items())

        inspect_stack = inspect.stack()
        frame = inspect_stack[1]
        filename = os.path.relpath(frame.filename, settings.BASE_DIR)
        lineno = frame.lineno
        function = frame.function
        logger.debug("%s(%s)", function, func_args_str)
        logger.debug("-- %s:%s", filename, lineno)

        return func(*args, **kwargs)

    return wrapper
