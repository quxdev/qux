"""Developer tooling helpers.

``stacktrace(depth=6)`` — emits the current exception traceback lines (up to
``depth``) on the ``qux`` logger at DEBUG level. Call from inside an
``except`` block. Used by greenflash for inline tracebacks in dev logs.

(``cast`` previously lived here too. It moved to ``qux.utils.coerce``
alongside its sibling helpers ``toint`` / ``tofloat`` / ``tobool`` and got a
``ValueError`` fix in the process. Update imports:
``from qux.utils.coerce import cast``.)
"""

import logging
import traceback

logger = logging.getLogger("qux")


def stacktrace(depth=6):
    stack = traceback.format_exc().splitlines()

    for n, x in enumerate(stack[1:-1]):
        if n < depth:
            logger.debug(x)

    if len(stack) > depth:
        logger.debug("  ...")
        logger.debug("  %s", stack[-1])
