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
