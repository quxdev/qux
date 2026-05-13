import datetime
import decimal
import importlib
import importlib.util
import json
import sys
import unittest
import uuid
from unittest.mock import patch

from django.test import SimpleTestCase

import qux.utils.json as qux_json
from qux.utils.coerce import cast, tobool, tofloat, toint, tonumericlist, tostring
from qux.utils.date import todate
from qux.utils.json import QuxComplexEncoder
from qux.utils.random import random_number, random_string

HAVE_NUMPY = importlib.util.find_spec("numpy") is not None
if HAVE_NUMPY:
    import numpy as np


class TestRandomString(SimpleTestCase):
    def test_default_length(self):
        result = random_string()
        assert len(result) == 8
        assert result.isalpha()

    def test_custom_length(self):
        result = random_string(16)
        assert len(result) == 16

    def test_returns_only_ascii_letters(self):
        result = random_string(100)
        assert result.isalpha()


class TestRandomNumber(SimpleTestCase):
    def test_default_length(self):
        result = random_number()
        assert len(result) == 10
        assert result.isdigit()

    def test_custom_length(self):
        result = random_number(5)
        assert len(result) == 5
        assert result.isdigit()


class TestQuxComplexEncoder(SimpleTestCase):
    def test_date(self):
        d = datetime.date(2024, 1, 15)
        result = json.dumps(d, cls=QuxComplexEncoder)
        assert result == '"2024-01-15"'

    def test_datetime(self):
        dt = datetime.datetime(2024, 1, 15, 10, 30, 0)
        result = json.dumps(dt, cls=QuxComplexEncoder)
        assert "2024-01-15" in result

    def test_decimal(self):
        d = decimal.Decimal("3.14")
        result = json.dumps(d, cls=QuxComplexEncoder)
        assert result == '"3.14"'

    def test_uuid(self):
        u = uuid.UUID("12345678-1234-5678-1234-567812345678")
        result = json.dumps(u, cls=QuxComplexEncoder)
        assert result == '"12345678123456781234567812345678"'

    def test_unknown_type_raises(self):
        with self.assertRaises(TypeError):
            json.dumps(object(), cls=QuxComplexEncoder)


class TestTodate(SimpleTestCase):
    def test_datetime_input_no_timestamp(self):
        dt = datetime.datetime(2024, 3, 15, 10, 30)
        result = todate(dt)
        assert result == datetime.date(2024, 3, 15)

    def test_datetime_input_with_timestamp(self):
        dt = datetime.datetime(2024, 3, 15, 10, 30)
        result = todate(dt, timestamp=True)
        assert result == dt

    def test_date_input(self):
        d = datetime.date(2024, 3, 15)
        result = todate(d)
        assert result == d

    def test_string_ymd(self):
        result = todate("2024-03-15")
        assert result == datetime.date(2024, 3, 15)

    def test_string_with_timestamp_flag(self):
        result = todate("2024-03-15", timestamp=True)
        assert isinstance(result, datetime.datetime)

    def test_string_invalid(self):
        result = todate("not-a-date")
        assert result is None

    def test_string_invalid_with_default(self):
        result = todate("not-a-date", default="fallback")
        assert result == "fallback"

    def test_string_mon_year(self):
        result = todate("Jan 2024")
        assert result == datetime.date(2024, 1, 1)

    def test_non_string_returns_default(self):
        result = todate([1, 2, 3], default="fallback")
        assert result == "fallback"

    def test_none_input(self):
        result = todate(None)
        assert result is None

    def test_int_input(self):
        result = todate(12345)
        assert result is None

    def test_string_slash_format(self):
        result = todate("03/15/24")
        assert result == datetime.date(2024, 3, 15)


class TestTofloat(SimpleTestCase):
    def test_int_input(self):
        assert tofloat(5) == 5.0

    def test_float_input(self):
        assert tofloat(3.14) == 3.14

    def test_empty_string(self):
        assert tofloat("") == 0.0

    def test_valid_string(self):
        assert tofloat("3.14") == 3.14

    def test_string_with_comma(self):
        assert tofloat("1, 234.56") == 1234.56

    def test_invalid_string(self):
        assert tofloat("abc") is None

    def test_invalid_string_with_default(self):
        assert tofloat("abc", defaultvalue=0.0) == 0.0

    def test_none_input(self):
        assert tofloat(None) is None


class TestToint(SimpleTestCase):
    def test_int_input(self):
        assert toint(5) == 5

    def test_float_input(self):
        assert toint(3.9) == 3

    def test_empty_string(self):
        assert toint("") is None

    def test_valid_string(self):
        assert toint("42") == 42

    def test_string_with_comma(self):
        assert toint("1, 234") == 1234

    def test_invalid_string(self):
        assert toint("abc") is None

    def test_invalid_string_with_default(self):
        assert toint("abc", default=0) == 0

    def test_none_input(self):
        assert toint(None) is None

    def test_list_input(self):
        assert toint([1, 2]) is None


class TestTostring(SimpleTestCase):
    def test_float_value(self):
        result = tostring(1234.5)
        assert result == "1,234.50"

    def test_int_value(self):
        result = tostring(1234)
        assert result == "1,234"

    def test_string_passthrough(self):
        result = tostring("hello")
        assert result == "hello"

    def test_none_passthrough(self):
        result = tostring(None)
        assert result is None


class TestTonumericlist(SimpleTestCase):
    def test_not_a_list(self):
        assert tonumericlist("hello") is None

    def test_all_numeric(self):
        result = tonumericlist([1, 2.5, 3])
        assert result == [1, 2.5, 3]

    def test_mixed_list(self):
        result = tonumericlist([1, "a", 3])
        assert result == [1, 0, 3]

    def test_empty_list(self):
        result = tonumericlist([])
        assert result == []


class TestTobool(SimpleTestCase):
    def test_true_values(self):
        for val in ("yes", "y", "true", "1", "Yes", "TRUE", "Y"):
            assert tobool(val) is True, f"Expected True for {val}"

    def test_false_values(self):
        for val in ("no", "false", "0", "n", ""):
            assert tobool(val) is False, f"Expected False for {val}"

    def test_non_string(self):
        assert tobool(1) is True
        assert tobool(0) is False


class TestNumpyImportFallback(SimpleTestCase):
    """Np = None when numpy import fails."""

    def test_numpy_import_failure_sets_np_none(self):
        """Reload qux.utils.json with numpy import blocked to cover except branch."""
        original_numpy = sys.modules.get("numpy")
        try:
            with patch.dict("sys.modules", {"numpy": None}):
                importlib.reload(qux_json)
                assert qux_json.np is None
        finally:
            if original_numpy is not None:
                sys.modules["numpy"] = original_numpy
            importlib.reload(qux_json)


@unittest.skipUnless(HAVE_NUMPY, "numpy not installed (optional extra: pip install qux[numpy])")
class TestQuxComplexEncoderNumpyGeneric(SimpleTestCase):
    """O.item() for numpy generic types."""

    def test_numpy_generic_encoded(self):
        val = np.int64(42)
        result = json.dumps(val, cls=QuxComplexEncoder)
        assert result == "42"

    def test_numpy_float_encoded(self):
        val = np.float64(3.14)
        result = json.dumps(val, cls=QuxComplexEncoder)
        assert "3.14" in result


class TestQuxComplexEncoderSuperDefault(SimpleTestCase):
    """Super().default() call for unhandled type."""

    def test_set_type_raises_type_error(self):
        # A set is not date/Decimal/UUID/numpy, so super().default() is called
        with self.assertRaises(TypeError):
            json.dumps({1, 2, 3}, cls=QuxComplexEncoder)


class TestTointValueErrorBranch(SimpleTestCase):
    """Toint ValueError/AttributeError branches."""

    def test_string_with_letters_returns_default(self):
        # "12abc" cannot be converted to int even after replace
        assert toint("12abc") is None

    def test_string_with_letters_returns_custom_default(self):
        assert toint("12abc", default=-1) == -1


class TestCast(SimpleTestCase):
    """``cast(valtype, value, default=None)`` — string-typed dispatch coercion."""

    def test_int_valid(self):
        assert cast("int", "42") == 42

    def test_int_none_value(self):
        assert cast("int", None) is None

    def test_int_invalid_returns_default(self):
        assert cast("int", None, default=-1) == -1

    def test_int_unparseable_returns_default(self):
        # Pre-May-2026 bug: this raised ValueError because the except clause
        # only caught TypeError. Fixed in the move to qux.utils.coerce.
        assert cast("int", "abc") is None
        assert cast("int", "abc", default=-1) == -1

    def test_float_valid(self):
        assert cast("float", "3.14") == 3.14

    def test_float_none_value(self):
        assert cast("float", None) is None

    def test_float_invalid_returns_default(self):
        assert cast("float", None, default=0.0) == 0.0

    def test_float_unparseable_returns_default(self):
        # Pre-May-2026 bug: ValueError leaked. Fixed in the move.
        assert cast("float", "not-a-float") is None
        assert cast("float", "not-a-float", default=-1.5) == -1.5

    def test_bool_true(self):
        assert cast("bool", "true") is True
        assert cast("bool", "1") is True

    def test_bool_false(self):
        assert cast("bool", "false") is False
        assert cast("bool", "0") is False

    def test_bool_invalid_returns_default(self):
        assert cast("bool", "maybe") is None
        assert cast("bool", "maybe", default=False) is False

    def test_bool_non_string_returns_value(self):
        # bool path requires .lower(); non-strings fall through to return-value.
        assert cast("bool", 1) == 1

    def test_none_string_returns_none(self):
        assert cast("int", "none") is None
        assert cast("int", "None") is None

    def test_null_string_returns_none(self):
        assert cast("float", "null") is None
        assert cast("float", "Null") is None

    def test_unknown_valtype_returns_value(self):
        assert cast("str", "hello") == "hello"

    def test_uppercase_valtype(self):
        assert cast("INT", "5") == 5
