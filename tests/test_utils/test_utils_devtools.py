import logging

from django.test import SimpleTestCase

from qux.utils.devtools import cast, stacktrace


class TestCast(SimpleTestCase):
    def test_int_valid(self):
        assert cast("int", "42") == 42

    def test_int_none_value(self):
        assert cast("int", None) is None

    def test_int_invalid_returns_default(self):
        assert cast("int", None, default=-1) == -1

    def test_float_valid(self):
        assert cast("float", "3.14") == 3.14

    def test_float_none_value(self):
        assert cast("float", None) is None

    def test_float_invalid_returns_default(self):
        assert cast("float", None, default=0.0) == 0.0

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
        # bool with no .lower() attribute returns value as-is
        assert cast("bool", 1) == 1

    def test_none_string(self):
        assert cast("int", "none") is None
        assert cast("int", "None") is None

    def test_null_string(self):
        assert cast("float", "null") is None
        assert cast("float", "Null") is None

    def test_unknown_type_returns_value(self):
        assert cast("str", "hello") == "hello"

    def test_uppercase_valtype(self):
        assert cast("INT", "5") == 5


class TestStacktrace(SimpleTestCase):
    def test_stacktrace_logs_debug(self):
        try:
            raise ValueError("test error")
        except ValueError:
            with self.assertLogs("qux.utils.devtools", level=logging.DEBUG) as cm:
                stacktrace()
            assert len(cm.output) > 0

    def test_stacktrace_truncates_deep_stack(self):
        """Cover lines 49-50: stack depth > depth param logs '...' and last frame."""
        try:
            raise ValueError("deep error")
        except ValueError:
            with self.assertLogs("qux.utils.devtools", level=logging.DEBUG) as cm:
                stacktrace(depth=1)
            # Should contain "..." indicating truncation
            output = "\n".join(cm.output)
            assert "..." in output
