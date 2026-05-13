import logging

from django.test import SimpleTestCase

from qux.utils.devtools import stacktrace


class TestStacktrace(SimpleTestCase):
    def test_stacktrace_logs_debug(self):
        try:
            raise ValueError("test error")
        except ValueError:
            with self.assertLogs("qux", level=logging.DEBUG) as cm:
                stacktrace()
            assert len(cm.output) > 0

    def test_stacktrace_truncates_deep_stack(self):
        """Stack depth > depth param logs '...' and last frame."""
        try:
            raise ValueError("deep error")
        except ValueError:
            with self.assertLogs("qux", level=logging.DEBUG) as cm:
                stacktrace(depth=1)
            # Should contain "..." indicating truncation
            output = "\n".join(cm.output)
            assert "..." in output
