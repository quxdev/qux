from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from qux.decorators import qux_debug


class QuxDebugDecoratorTest(SimpleTestCase):
    """Tests for the qux_debug decorator."""

    @override_settings(DEBUG=False)
    def test_debug_false_calls_function_returns_result(self):
        """When DEBUG=False, qux_debug calls the function and returns its result without logging."""

        @qux_debug
        def add(a, b):
            return a + b

        with patch("qux.decorators.logger") as mock_logger:
            result = add(2, 3)

        assert result == 5
        mock_logger.debug.assert_not_called()

    @override_settings(DEBUG=True, BASE_DIR="/tmp")
    def test_debug_true_calls_function_returns_result(self):
        """When DEBUG=True, qux_debug calls the function, logs debug info,
        and returns its result."""

        @qux_debug
        def add(a, b):
            return a + b

        with patch("qux.decorators.logger") as mock_logger:
            result = add(2, 3)

        assert result == 5
        assert mock_logger.debug.call_count == 2

    @override_settings(DEBUG=False)
    def test_decorated_function_preserves_metadata(self):
        """The decorated function preserves __name__ and __doc__ via @wraps."""

        @qux_debug
        def my_function(x):
            """This is my docstring."""
            return x

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "This is my docstring."
