<<<<<<< HEAD
import json
import random
import string


def get_random_string(length=8):
    letters = string.ascii_letters
    result = ''.join(random.choice(letters) for _ in range(length))
    return result


def get_random_number(length=10):
    numbers = string.digits
    result = ''.join(random.choice(numbers) for _ in range(length))
    return result


class QuxComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        # date
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return '{0:f}'.format(obj)
        elif isinstance(obj, UUID):
            return obj.hex
        elif isinstance(obj, np.generic):
            return np.asscalar(obj)
        else:
            return json.JSONEncoder.default(self, obj)
=======
import datetime
import six


FMT_DTSTR = [
    '%Y-%m-%d',
    '%b %Y',
    '%b_%Y',
    '%Y-%m-%d %H:%M',
    '%Y%m%d',
    '%Y%m%d %H:%M',
    '%d%b%Y',
    '%m/%d/%y',
    '%d%b%Y %H:%M',
    '%b-%d-%y',
    '%b-%d-%y %H:%M',
    '%d-%b-%Y',
    '%d-%b-%Y %H:%M',
    '%m/%d/%Y',
    '%m/%d/%Y %H:%M',
    '%d-%m-%Y',
    '%d-%m-%Y %H:%M',
    '%b-%y',
    '%H:%M',
]


def todate(x, default=None, timestamp=False):
    """

    :param x: value to convert
    :param default: default value to return if cannot convert
    :param timestamp: return date if False and with time if True
    :return:
    """
    if type(x) is datetime.date:
        result = x
    elif type(x) is datetime.datetime:
        result = x if timestamp else x.date()
    # elif type(dt) == str or type(dt) == unicode:
    elif isinstance(x, six.string_types):
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

    if type(numstr) in [str, str] and numstr == '':
        return float(0)

    try:
        result = float(numstr.replace(', ', ''))
    except ValueError:
        result = defaultvalue
    except AttributeError:
        result = defaultvalue

    return result


def toint(numstr, default=None):
    if type(numstr) in [int, float]:
        result = int(numstr)
    elif type(numstr) in [str, str]:
        if numstr == '':
            result = default
        else:
            try:
                result = int(numstr.replace(', ', ''))
            except ValueError:
                result = default
            except AttributeError:
                result = default
    else:
        result = default
    return result


>>>>>>> 188cda8 (modifications for use in racecar)
