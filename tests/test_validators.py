from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from qux.validators import ValidateListOfN


class TestValidateListOfN(SimpleTestCase):
    def test_valid_list(self):
        validator = ValidateListOfN(3)
        result = validator("a,b,c")
        assert result == "a,b,c"

    def test_too_few_raises(self):
        validator = ValidateListOfN(3)
        with self.assertRaises(ValidationError):
            validator("a,b")

    def test_empty_string_raises(self):
        validator = ValidateListOfN(3)
        with self.assertRaises(ValidationError):
            validator("")

    def test_equal_same_count(self):
        assert ValidateListOfN(3) == ValidateListOfN(3)

    def test_not_equal_different_count(self):
        assert ValidateListOfN(3) != ValidateListOfN(2)

    def test_eq_different_type_returns_not_implemented(self):
        result = ValidateListOfN(3).__eq__(  # pylint: disable=unnecessary-dunder-call
            "other"
        )
        assert result is NotImplemented
