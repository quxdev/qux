import uuid
import json
import random
import string
import datetime
import decimal
import numpy as np


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
    def default(self, obj):
        # date
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        elif isinstance(obj, decimal.Decimal):
            return "{0:f}".format(obj)
        elif isinstance(obj, uuid.UUID):
            return obj.hex
        elif isinstance(obj, np.generic):
            return np.asscalar(obj)
        else:
            return json.JSONEncoder.default(self, obj)


def todate(x, default=None, timestamp=False):
    """
    Convert given value to a date

    :param x: input value for conversion
    :param default: default return value if conversion is not possible
    :param timestamp: return date if False and datetime if True
    :return:
    """
    if type(x) is datetime.date:
        result = x
    elif type(x) is datetime.datetime:
        result = x if timestamp else x.date()
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
    if type(numstr) in [int, float]:
        return float(numstr)

    if type(numstr) in [str, str] and numstr == "":
        return float(0)

    try:
        result = float(numstr.replace(", ", ""))
    except ValueError:
        result = defaultvalue
    except AttributeError:
        result = defaultvalue

    return result


def toint(numstr, default=None):
    if type(numstr) in [int, float]:
        result = int(numstr)
    elif type(numstr) in [str, str]:
        if numstr == "":
            result = default
        else:
            try:
                result = int(numstr.replace(", ", ""))
            except ValueError:
                result = default
            except AttributeError:
                result = default
    else:
        result = default
    return result


def tostring(somevalue):
    numdecimalplaces = 2
    if type(somevalue) == float:
        result = "{0:,.{1}f}".format(somevalue, numdecimalplaces)
        return result
    if type(somevalue) == int:
        result = "{0:,d}".format(somevalue)
        return result
    return somevalue


def tonumericlist(target):
    if type(target) is not list:
        return

    if all(type(x) in [int, float] for x in target):
        return target

    # target needs fixing
    result = []
    for x in target:
        if type(x) in [int, float]:
            result.append(x)
        else:
            result.append(0)

    return result


def tobool(x):
    y = ["yes", "y", "true", "1"]
    if any([v == x.lower() for v in y]):
        return True
    else:
        return False
