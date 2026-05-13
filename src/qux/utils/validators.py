"""Reusable Django field validators.

``ValidateListOfN(n)`` — class-based, ``@deconstructible`` (safe to put in
migrations) validator that checks a comma-separated string has exactly ``n``
parts. Pair with ``qux.utils.modelfields.FloatListField`` when you need a
fixed-length numeric tuple stored as text. Defines ``__eq__`` so two
instances with the same ``n`` compare equal — required for migration
serialization to be stable.
"""

from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


@deconstructible
class ValidateListOfN:
    """
    Validator to check presence of n comma separated values
    """

    def __init__(self, n):
        self.count = n
        self.error_message = f"Field must contain {self.count} comma separated values"

    def __call__(self, value):
        if value:
            listofnumbers = value.split(",")
            if len(listofnumbers) == self.count:
                return value
            raise ValidationError(self.error_message)
        raise ValidationError(self.error_message)

    def __eq__(self, other):
        if not isinstance(other, ValidateListOfN):
            return NotImplemented
        return self.count == other.count
