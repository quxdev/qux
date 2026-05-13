from django.test import SimpleTestCase

from qux.utils.phone import format_phone_number, phone_number


class TestPhoneNumber(SimpleTestCase):
    def test_valid_e164(self):
        result = phone_number("+14155552671")
        assert result == "+14155552671"

    def test_valid_indian_local(self):
        result = phone_number("9876543210", country="IN")
        assert result is not None
        assert result.startswith("+91")

    def test_invalid_number(self):
        result = phone_number("12345")
        assert result is None

    def test_none_input(self):
        result = phone_number(None)
        assert result is None

    def test_garbage_input(self):
        result = phone_number("not a phone number")
        assert result is None

    def test_us_number_without_plus(self):
        result = phone_number("14155552671", "US")
        assert result == "+14155552671"


class TestFormatPhoneNumber(SimpleTestCase):
    def test_national_format_indian(self):
        result = format_phone_number("+919876543210", fmt="national")
        assert result is not None
        assert not result.startswith("+")

    def test_international_format(self):
        result = format_phone_number("+14155552671", fmt="international")
        assert result is not None
        assert "+" in result

    def test_invalid_returns_original(self):
        result = format_phone_number("invalid")
        assert result == "invalid"

    def test_international_format_non_in_non_us(self):
        """Non-IN, non-US number in national format falls to international."""
        # UK number — country_code 44, not 91 (IN) and not 1 (US)
        result = format_phone_number("+442071234567", fmt="national")
        assert result is not None


class TestPhoneNumberPlusPrefixBranch(SimpleTestCase):
    """Phone_number parsing with '+' prefix succeeds."""

    def test_valid_number_with_plus_prefix_attempt(self):
        # A number that fails initial parse but works with '+' prefix
        # "14155552671" without country — parse(None) may fail, then parse(country)
        # succeeds for "IN" context but then is_valid_number fails, tries with '+'
        result = phone_number("14155552671", country="IN")
        assert result == "+14155552671"


class TestPhoneNumberElseBranch(SimpleTestCase):
    """NumberParseException and else branches."""

    def test_plus_prefixed_parsed_but_not_valid(self):
        # "+919999" parses (CC=91, NN=9999) but is_valid_number returns False.
        # Because it starts with '+', the else branch (lines 38-39) is hit.
        result = phone_number("+919999")
        assert result is None

    def test_plus_prefix_triggers_number_parse_exception(self):
        # "000" with country='IN': parse(None) fails, parse('IN') succeeds
        # but is_valid_number is False. Does not start with '+', so tries
        # parse('+000', None) which raises NumberParseException (lines 35-36).
        result = phone_number("000")
        assert result is None

    def test_short_number_triggers_exception(self):
        # Very short input that may raise NumberParseException
        result = phone_number("1")
        assert result is None
