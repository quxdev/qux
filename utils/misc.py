import datetime
import decimal
import json
import random
import string
import uuid

try:
    import numpy as np
except ImportError:
    np = None

FMT_DTSTR = [
    "%Y-%m-%d",
    "%b %Y",
    "%b_%Y",
    "%Y-%m-%d %H:%M",
    "%Y%m%d",
    "%Y%m%d %H:%M",
    "%d%b%Y",
    "%m/%d/%y",
    "%d%b%Y %H:%M",
    "%b-%d-%y",
    "%b-%d-%y %H:%M",
    "%d-%b-%Y",
    "%d-%b-%Y %H:%M",
    "%m/%d/%Y",
    "%m/%d/%Y %H:%M",
    "%d-%m-%Y",
    "%d-%m-%Y %H:%M",
    "%b-%y",
    "%H:%M",
]


def random_string(length=8):
    letters = string.ascii_letters
    result = "".join(random.choice(letters) for _ in range(length))
    return result


def random_number(length=10):
    numbers = string.digits
    result = "".join(random.choice(numbers) for _ in range(length))
    return result


class QuxComplexEncoder(json.JSONEncoder):
    def default(self, o):
        # date
        if hasattr(o, "isoformat"):
            return o.isoformat()
        if isinstance(o, decimal.Decimal):
            return f"{o:f}"
        if isinstance(o, uuid.UUID):
            return o.hex
        if np is not None and isinstance(o, np.generic):
            return o.item()
        return super().default(o)


def todate(x, default=None, timestamp=False):
    """
    Convert given value to a date

    :param x: input value for conversion
    :param default: default return value if conversion is not possible
    :param timestamp: return date if False and datetime if True
    :return:
    """
    if isinstance(x, datetime.datetime):
        result = x if timestamp else x.date()
    elif isinstance(x, datetime.date):
        result = x
    # elif type(dt) == str or type(dt) == unicode:
    elif isinstance(x, str):
        result = default
        for fmt in FMT_DTSTR:
            try:
                result = datetime.datetime.strptime(x, fmt)
                result = result if timestamp else result.date()
                break
            except ValueError:
                result = default
    else:
        result = default
    return result


def tofloat(numstr, defaultvalue=None):
    if isinstance(numstr, (int, float)):
        return float(numstr)

    if isinstance(numstr, str) and numstr == "":
        return float(0)

    try:
        result = float(numstr.replace(", ", ""))
    except ValueError:
        result = defaultvalue
    except AttributeError:
        result = defaultvalue

    return result


def toint(numstr, default=None):
    if isinstance(numstr, (int, float)):
        result = int(numstr)
    elif isinstance(numstr, str):
        if numstr == "":
            result = default
        else:
            try:
                result = int(numstr.replace(", ", ""))
            except ValueError:
                result = default
            except AttributeError:  # pragma: no cover
                result = default
    else:
        result = default
    return result


def tostring(somevalue):
    numdecimalplaces = 2
    if isinstance(somevalue, float):
        result = f"{somevalue:,.{numdecimalplaces}f}"
        return result
    if isinstance(somevalue, int):
        result = f"{somevalue:,d}"
        return result
    return somevalue


def tonumericlist(target):
    if not isinstance(target, list):
        return None

    if all(isinstance(x, (int, float)) for x in target):
        return target

    # target needs fixing
    result = []
    for x in target:
        if isinstance(x, (int, float)):
            result.append(x)
        else:
            result.append(0)

    return result


def tobool(x):
    return str(x).lower() in ("yes", "y", "true", "1")
