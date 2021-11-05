import re
from django.db import models
from django.core.validators import RegexValidator

comma_separated_float_list_regexp = re.compile(r"^([-+]?\d*\.?\d+[,\s]*)+$")

validate_comma_separated_float_list = RegexValidator(
        comma_separated_float_list_regexp,
        'Field must contain comma separated float values'
)


class FloatListField(models.TextField):
    default_validators = [validate_comma_separated_float_list]
    description = "Comma-separated floats"
