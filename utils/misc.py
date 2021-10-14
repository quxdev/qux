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
