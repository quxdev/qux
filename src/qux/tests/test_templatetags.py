import datetime
from unittest.mock import patch

from django import forms, template
from django.http import QueryDict
from django.test import SimpleTestCase, override_settings

from qux.templatetags.qux import (
    addstr,
    atleast,
    date_before,
    divide,
    getconfig,
    multiply,
    qux_floatformat,
    qux_floatformat_in,
    qux_floatformat_us,
    qux_min,
    qux_static,
    strip,
)
from qux.templatetags.quxform import is_checkbox


class MultiplyFilterTest(SimpleTestCase):
    """Tests for the multiply template filter."""

    def test_multiply_integers(self):
        assert multiply(10, 3) == 30

    def test_multiply_string_repetition(self):
        assert multiply("a", 3) == "aaa"

    def test_multiply_none_returns_none(self):
        assert multiply(None, 3) is None


class DivideFilterTest(SimpleTestCase):
    """Tests for the divide template filter."""

    def test_divide_integers(self):
        assert divide(10, 2) == 5.0

    def test_divide_by_zero_returns_none(self):
        assert divide(10, 0) is None

    def test_divide_none_returns_none(self):
        assert divide(None, 2) is None


class AtleastFilterTest(SimpleTestCase):
    """Tests for the atleast template filter."""

    def test_atleast_value_below_minimum(self):
        assert atleast(5, 10) == 10

    def test_atleast_value_above_minimum(self):
        assert atleast(15, 10) == 15


class QuxMinFilterTest(SimpleTestCase):
    """Tests for the qux_min template filter."""

    def test_min_returns_smaller_value(self):
        assert qux_min(5, 10) == 5

    def test_min_returns_smaller_arg(self):
        assert qux_min(15, 10) == 10


class StripFilterTest(SimpleTestCase):
    """Tests for the strip template filter."""

    def test_strip_removes_characters(self):
        assert strip(" hello ", " ") == "hello"

    def test_strip_non_string_passthrough(self):
        assert strip(123, " ") == 123


class AddstrFilterTest(SimpleTestCase):
    """Tests for the addstr template filter."""

    def test_addstr_concatenates_with_underscore(self):
        assert addstr("foo", "bar") == "foo_bar"


class QuxFloatformatTest(SimpleTestCase):
    """Tests for the qux_floatformat function."""

    def test_us_format_with_commas(self):
        result = qux_floatformat(1234567, 2, "us")
        assert "," in result
        # 1,234,567 — commas every 3 digits
        assert result.startswith("1,234,567")

    def test_indian_format(self):
        result = qux_floatformat(1234567, 2, "in")
        assert "," in result
        # Indian format: 12,34,567
        assert result.startswith("12,34,567")

    def test_zero_returns_dash(self):
        assert qux_floatformat(0, 2, "us") == "-"

    def test_negative_number(self):
        result = qux_floatformat(-1234, 2, "us")
        assert result.startswith("-")
        assert "1,234" in result

    def test_invalid_value_returns_value(self):
        assert qux_floatformat("abc", 2, "us") == "abc"


@override_settings(DEBUG=True)
class GetconfigFilterTest(SimpleTestCase):
    """Tests for the getconfig template filter."""

    def test_getconfig_returns_setting_value(self):
        assert getconfig("DEBUG") is True

    def test_getconfig_blocks_secret_key(self):
        assert getconfig("SECRET_KEY") is None

    def test_getconfig_blocks_databases(self):
        assert getconfig("DATABASES") is None

    def test_getconfig_blocks_password_keyword(self):
        assert getconfig("MY_PASSWORD_SETTING") is None

    def test_getconfig_nonexistent_returns_none(self):
        assert getconfig("NONEXISTENT") is None

    def test_getconfig_nonexistent_with_default(self):
        assert getconfig("NONEXISTENT", "fallback") == "fallback"


class IsCheckboxFilterTest(SimpleTestCase):
    """Tests for the is_checkbox template filter from quxform.py."""

    def test_boolean_field_is_checkbox(self):

        # Create a minimal form to get a BoundField
        class TestForm(forms.Form):
            flag = forms.BooleanField()

        form = TestForm(data={"flag": True})
        bound = form["flag"]
        assert is_checkbox(bound) is True

    def test_char_field_is_not_checkbox(self):
        class TestForm(forms.Form):
            name = forms.CharField()

        form = TestForm(data={"name": "test"})
        bound = form["name"]
        assert is_checkbox(bound) is False


# ---------------------------------------------------------------------------
# atleast — lines 36-37 (happy path returning arg > value)
# ---------------------------------------------------------------------------


class AtleastFilterHappyPathTest(SimpleTestCase):
    """Cover the try body in atleast: return arg if arg > value else value."""

    def test_arg_greater_returns_arg(self):
        # arg > value => returns arg (line 35)
        assert atleast(3, 10) == 10

    def test_value_greater_returns_value(self):
        # arg <= value => returns value (line 35)
        assert atleast(20, 10) == 20

    def test_type_error_returns_value(self):
        # TypeError branch — lines 36-37
        assert atleast("string", 10) == "string"


# ---------------------------------------------------------------------------
# qux_min — lines 44-45 (happy path + TypeError)
# ---------------------------------------------------------------------------


class QuxMinFilterHappyPathTest(SimpleTestCase):
    """Cover the try body in qux_min and the TypeError branch."""

    def test_min_happy_path(self):
        assert qux_min(7, 3) == 3

    def test_min_type_error_returns_value(self):
        # TypeError branch — lines 44-45
        assert qux_min("string", 3) == "string"


# ---------------------------------------------------------------------------
# qux_floatformat_in / qux_floatformat_us — lines 50, 55
# ---------------------------------------------------------------------------


class FloatformatFilterWrappersTest(SimpleTestCase):
    """Cover the qux_floatformat_in and qux_floatformat_us wrappers."""

    def test_floatformat_in_wrapper(self):
        # line 50: calls qux_floatformat with "in"
        result = qux_floatformat_in(1234567, 2)
        assert result.startswith("12,34,567")

    def test_floatformat_us_wrapper(self):
        # line 55: calls qux_floatformat with "us"
        result = qux_floatformat_us(1234567, 2)
        assert result.startswith("1,234,567")


# ---------------------------------------------------------------------------
# qux_floatformat — line 81 (right decimal part)
# ---------------------------------------------------------------------------


class FloatformatDecimalPartTest(SimpleTestCase):
    """Result = f'{result}{str(right)[1:]}'."""

    def test_decimal_value_includes_fraction(self):
        result = qux_floatformat(1234.56, 2, "us")
        assert "1,234" in result
        assert ".56" in result

    def test_decimal_value_indian_format(self):
        result = qux_floatformat(1234.56, 2, "in")
        assert "1,234" in result
        assert ".56" in result


# ---------------------------------------------------------------------------
# date_before — lines 99-100
# ---------------------------------------------------------------------------


class DateBeforeFilterTest(SimpleTestCase):
    """Cover date_before filter."""

    def test_date_before_returns_iso_string(self):
        result = date_before(7)
        expected = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
        assert result == expected

    def test_date_before_zero_days(self):
        result = date_before(0)
        assert result == datetime.date.today().isoformat()


# ---------------------------------------------------------------------------
# url_replace — lines 111-116
# ---------------------------------------------------------------------------


class URLReplaceTagTest(SimpleTestCase):
    """Cover url_replace simple tag (lines 111-116)."""

    def test_url_replace_adds_new_param(self):
        class MockRequest:
            GET = QueryDict("page=1&sort=name")

        context = {"request": MockRequest()}
        result = template.Template("{% load qux %}{% url_replace page=2 %}").render(
            template.Context(context)
        )
        assert "page=2" in result
        assert "sort=name" in result

    def test_url_replace_replaces_existing_param(self):
        class MockRequest:
            GET = QueryDict("page=1&sort=name")

        context = {"request": MockRequest()}
        result = template.Template("{% load qux %}{% url_replace page=5 %}").render(
            template.Context(context)
        )
        assert "page=5" in result
        # The old page=1 should be gone
        assert "page=1" not in result


# ---------------------------------------------------------------------------
# lineless / LinelessNode — lines 147-149, 154, 157-162
# ---------------------------------------------------------------------------


class LinelessTagTest(SimpleTestCase):
    """Cover lineless template tag and LinelessNode."""

    def test_lineless_strips_blank_lines(self):
        tpl = template.Template(
            "{% load qux %}{% lineless %}\n" "Hello\n" "\n" "   \n" "World\n" "{% endlineless %}"
        )
        result = tpl.render(template.Context({}))
        # Blank lines should be removed
        assert "Hello" in result
        assert "World" in result
        # Check no blank lines remain
        for line in result.splitlines():
            if line:
                assert line.strip() != ""


# ---------------------------------------------------------------------------
# qux_static — lines 168-191
# ---------------------------------------------------------------------------


class QuxStaticTagTest(SimpleTestCase):
    """Cover qux_static (lines 168-191)."""

    @override_settings(DEBUG=True)
    @patch("qux.templatetags.qux.static", return_value="/static/css/style.css")
    def test_css_lazy_debug_true(self, _mock_static):
        # DEBUG=True, so no minified lookup. CSS lazy loads.
        result = qux_static("css/style.css", lazy=True)
        assert 'media="print"' in result
        assert "onload" in result
        assert "<noscript>" in result

    @override_settings(DEBUG=True)
    @patch("qux.templatetags.qux.static", return_value="/static/css/style.css")
    def test_css_not_lazy(self, _mock_static):
        result = qux_static("css/style.css", lazy=False)
        assert 'rel="stylesheet"' in result
        assert "onload" not in result

    @override_settings(DEBUG=True)
    @patch("qux.templatetags.qux.static", return_value="/static/js/app.js")
    def test_js_lazy(self, _mock_static):
        result = qux_static("js/app.js", lazy=True)
        assert "defer" in result
        assert "<script" in result

    @override_settings(DEBUG=True)
    @patch("qux.templatetags.qux.static", return_value="/static/js/app.js")
    def test_js_not_lazy(self, _mock_static):
        result = qux_static("js/app.js", lazy=False)
        assert "<script" in result
        assert "defer" not in result

    @override_settings(DEBUG=True)
    @patch("qux.templatetags.qux.static", return_value="/static/img/logo.png")
    def test_other_extension_returns_url(self, _mock_static):
        result = qux_static("img/logo.png")
        assert "/static/img/logo.png" in result

    @override_settings(DEBUG=False)
    @patch("qux.templatetags.qux.static", return_value="/static/css/style.min.css")
    @patch("qux.templatetags.qux.staticfiles_find", return_value="/full/path/style.min.css")
    def test_non_debug_uses_minified_css(self, mock_find, _mock_static):
        result = qux_static("css/style.css", lazy=True)
        # Should have looked for the .min version
        mock_find.assert_called_once_with("css/style.min.css")
        assert 'media="print"' in result

    @override_settings(DEBUG=False)
    @patch("qux.templatetags.qux.static", return_value="/static/js/app.js")
    @patch("qux.templatetags.qux.staticfiles_find", return_value=None)
    def test_non_debug_no_minified_fallback(self, mock_find, _mock_static):
        # .min file not found, falls back to original
        result = qux_static("js/app.js", lazy=True)
        mock_find.assert_called_once_with("js/app.min.js")
        assert "<script" in result

    @override_settings(DEBUG=False)
    @patch("qux.templatetags.qux.static", return_value="/static/css/style.min.css")
    @patch("qux.templatetags.qux.staticfiles_find", return_value=None)
    def test_non_debug_already_min_no_double_min(self, mock_find, _mock_static):
        # Already has .min, should not look for .min.min
        result = qux_static("css/style.min.css", lazy=False)
        mock_find.assert_not_called()
        assert 'rel="stylesheet"' in result
