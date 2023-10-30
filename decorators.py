import inspect
import os
from functools import wraps

from django.conf import settings


def qux_debug(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not settings.DEBUG:
            return func(*args, **kwargs)

        func_args = inspect.signature(func).bind(*args, **kwargs).arguments
        func_args_str = ", ".join(map("{0[0]} = {0[1]!r}".format, func_args.items()))

        inspect_stack = inspect.stack()
        frame = inspect_stack[1]
        filename = os.path.relpath(frame.filename, settings.BASE_DIR)
        lineno = frame.lineno
        function = frame.function
        print(f"{function}({func_args_str})")
        print(f"-- {filename}:{lineno}")

        return func(*args, **kwargs)

    return wrapper
