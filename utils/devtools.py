import logging
import traceback

logger = logging.getLogger(__name__)


def cast(valtype, value, default=None):  # pylint: disable=too-many-return-statements
    """
    TODO: does not consider datetime.date, datetime.time, or datetime.datetime
    """
    valtype = valtype.lower()

    if hasattr(value, "lower") and value.lower() in ["none", "null"]:
        return None

    if valtype == "int":
        try:
            return int(value)
        except TypeError:
            return default

    if valtype == "float":
        try:
            return float(value)
        except TypeError:
            return default

    if valtype == "bool" and hasattr(value, "lower"):
        if value.lower() in ["true", "1"]:
            return True
        if value.lower() in ["false", "0"]:
            return False
        return default

    # else ???
    return value


def stacktrace(depth=6):
    # exc_type, exc_value, exc_traceback = sys.exc_info()

    stack = traceback.format_exc().splitlines()

    for n, x in enumerate(stack[1:-1]):
        if n < depth:
            logger.debug(x)

    if len(stack) > depth:
        logger.debug("  ...")
        logger.debug("  %s", stack[-1])
