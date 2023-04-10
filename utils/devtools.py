import traceback


def cast(valtype, value, default=None):
    """
    TODO: does not consider datetime.date, datetime.time, or datetime.datetime
    """
    valtype = valtype.lower()

    if hasattr(value, "lower") and value.lower() in ["none", "null"]:
        return None

    elif valtype == "int":
        try:
            return int(value)
        except TypeError:
            return default

    elif valtype == "float":
        try:
            return float(value)
        except TypeError:
            return default

    elif valtype == "bool" and hasattr(value, "lower"):
        if value.lower() in ["true", "1"]:
            return True
        elif value.lower() in ["false", "0"]:
            return False
        else:
            return default

    # else ???
    return value


def stacktrace(depth=6):
    # exc_type, exc_value, exc_traceback = sys.exc_info()

    stack = traceback.format_exc().splitlines()
    print()

    for n, x in enumerate(stack[1:-1]):
        if n < depth:
            print(x)

    if len(stack) > depth:
        print("  ...")
        print("  " + stack[-1])

    print()
