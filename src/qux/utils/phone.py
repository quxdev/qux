"""Phone number parsing, validation, and formatting.

Wraps Google's ``phonenumbers`` library for the qux-typical case (Indian
numbers with international fallback).

- ``phone_number(phone, country="IN")`` — parse + validate; returns the E.164
  form (``+919876543210``) or None if unparseable. Tries no-country-hint
  first, then the supplied default country, then tries prefixing ``+``.
- ``format_phone_number(phone, fmt="national")`` — render an existing number
  in NATIONAL or INTERNATIONAL form. Indian numbers default to NATIONAL;
  others fall through to INTERNATIONAL.
"""

import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException, PhoneNumberFormat


def phone_number(phone, country: str = "IN"):
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
        elif not phone.startswith("+"):
            try:
                result = phonenumbers.parse("+" + phone, None)
                if phonenumbers.is_valid_number(result):
                    result = phonenumbers.format_number(result, PhoneNumberFormat.E164)
                else:
                    result = None
            except NumberParseException:
                result = None

        else:
            result = None

    return result


def format_phone_number(phone, fmt="national"):
    try:
        p = phonenumbers.parse(phone_number(phone))
    except NumberParseException:
        return phone

    if fmt == "international":
        result = phonenumbers.format_number(p, PhoneNumberFormat.INTERNATIONAL)
    elif p.country_code == 91:
        result = phonenumbers.format_number(p, PhoneNumberFormat.NATIONAL)
    else:
        result = phonenumbers.format_number(p, PhoneNumberFormat.INTERNATIONAL)
    return result
