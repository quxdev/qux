from django.utils.deconstruct import deconstructible
from django.core.exceptions import ValidationError


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
