from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from qux.utils.modelfields import FloatListField, validate_comma_separated_float_list


class TestValidateCommaSeparatedFloatList(SimpleTestCase):
    def test_single_float(self):
        validate_comma_separated_float_list("1.5")

    def test_multiple_floats(self):
        validate_comma_separated_float_list("1.5,2.3,3.1")

    def test_signed_floats(self):
        validate_comma_separated_float_list("-1.5,+2.3")

    def test_trailing_comma_raises(self):
        with self.assertRaises(ValidationError):
            validate_comma_separated_float_list("1.5,")

    def test_non_numeric_raises(self):
        with self.assertRaises(ValidationError):
            validate_comma_separated_float_list("abc")

    def test_empty_string_raises(self):
        with self.assertRaises(ValidationError):
            validate_comma_separated_float_list("")


class TestFloatListField(SimpleTestCase):
    def test_description(self):
        assert FloatListField.description == "Comma-separated floats"
