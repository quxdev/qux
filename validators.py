from django.utils.deconstruct import deconstructible
from django.core.exceptions import ValidationError


@deconstructible
class ValidateListOfN(object):
    """
    Validator to check presence of n comma separated values
    """

    def __init__(self, n):
        self.count = n
        err = "Field must contain {} comma separated values".format(self.count)
        self.error_message = err

    def __call__(self, value):
        if value:
            listofnumbers = value.split(",")
            if len(listofnumbers) == self.count:
                return value
            else:
                raise ValidationError(self.error_message)
        else:
            raise ValidationError(self.error_message)

    def __eq__(self, other):
        return self.count == other.count
