import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException
from phonenumbers.phonenumberutil import PhoneNumberFormat
import random


def phone_number(phone, country: str = 'IN'):
    if phone is None:
        return None

    try:
        result = phonenumbers.parse(phone, None)
    except NumberParseException:
        result = None

    if result is None:
        try:
            result = phonenumbers.parse(phone, country)
        except NumberParseException:
            result = None

    if result:
        if phonenumbers.is_valid_number(result):
            result = phonenumbers.format_number(result, PhoneNumberFormat.E164)

        # Number is not a valid number as is. Does prefixing with a '+' help?
        elif not phone.startswith('+'):
            try:
                result = phonenumbers.parse('+' + phone, None)
                if phonenumbers.is_valid_number(result):
                    result = phonenumbers.format_number(result, PhoneNumberFormat.E164)
                else:
                    result = None
            except NumberParseException:
                result = None

        else:
            result = None

    return result


# def random_phone_number(numdigits=10, prefix="+91"):
#     result = None
#     while result is None:
#         number = random.randrange(10 ** numdigits)
#         number = prefix + str(number)
#         number = phone_number(number)
#         result = number if number else None
#
#     return result


def fakephonenumber(countrycode: str = 'IN'):
    if countrycode == 'IN':
        result = None
        while phone_number(result) is None:
            result = ''.join(
                [str(random.randint(6, 9))] +
                [str(random.randint(0, 9)) for _ in range(9)]
            )

        return phone_number(result)
    else:
        return None


def format_phone_number(phone, fmt="national"):
    try:
        p = phonenumbers.parse(phone_number(phone))
    except NumberParseException:
        return phone

    if fmt == 'international':
        result = phonenumbers.format_number(p, PhoneNumberFormat.INTERNATIONAL)
    elif p.country_code == 91:
        result = phonenumbers.format_number(p, PhoneNumberFormat.NATIONAL)
    else:
        result = phonenumbers.format_number(p, PhoneNumberFormat.INTERNATIONAL)
    return result
