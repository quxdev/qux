from django.test import RequestFactory, TestCase

from qux.drf.log.mixins import LoggingMixin


class DummyView(LoggingMixin):
    def __init__(self):
        super().__init__()
        self.log = {}

    def _get_user(self, request):  # type: ignore[override]
        return "userid_1"


class TestSampling(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()

    def test_basic_methods_exist(self):
        # smoke test: ensure mixin has handle_log method
        self.assertTrue(callable(LoggingMixin.handle_log))
