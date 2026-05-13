"""Custom Django model fields.

``FloatListField`` — TextField subclass that validates the stored string is
a comma-separated list of floats (``"1.5,2.0,-3.7"``). Use when an array of
floats is the natural shape but you don't want a JSONField or per-row child
table. Pair with ``qux.utils.validators.ValidateListOfN`` if you also need to
constrain the count.
"""

import re

from django.core.validators import RegexValidator
from django.db import models

comma_separated_float_list_regexp = re.compile(r"^[-+]?\d*\.?\d+(,\s*[-+]?\d*\.?\d+)*$")

validate_comma_separated_float_list = RegexValidator(
    comma_separated_float_list_regexp, "Field must contain comma separated float values"
)


class FloatListField(models.TextField):
    default_validators = [validate_comma_separated_float_list]
    description = "Comma-separated floats"
