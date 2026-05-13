from unittest.mock import MagicMock, patch

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import reverse

from qux.auth.views.appviews import MagicLinkRequestView


def _add_middleware(request):
    # Mock session
    request.session = MagicMock()
    # Mock messages
    request._messages = MagicMock()


@override_settings(USE_MAGIC_LINK=True)
class MagicLinkDomainBlockingTest(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.url = reverse("qux_auth:magic_link")

    @override_settings(BLOCKED_DOMAIN_FOR_MAGIC_LINK=["aol.com", "hotmail.com"])
    @patch("qux.auth.views.appviews.render")
    def test_request_with_blocked_domain(self, mock_render):
        mock_render.return_value = HttpResponse("Domain not allowed page")

        request = self.factory.post(self.url, {"email": "test@aol.com", "render_ts": 0})
        _add_middleware(request)

        response = MagicLinkRequestView.as_view()(request)

        # Verify it calls the error response (rendered with "Domain not allowed")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Domain not allowed", response.content)

    @override_settings(BLOCKED_DOMAIN_FOR_MAGIC_LINK=["aol.com", "hotmail.com"])
    @patch("qux.auth.views.appviews.User")
    @patch("qux.auth.views.appviews.cache")
    @patch("qux.auth.views.appviews.send_mail")
    @patch("qux.auth.views.appviews.render")
    def test_request_with_allowed_domain(self, mock_render, mock_send_mail, mock_cache, mock_user):
        mock_render.return_value = HttpResponse("Success page")
        # Mock cache to avoid DB queries
        mock_cache.get.return_value = 0
        # Mock User.objects.get to return a mock user
        mock_user.objects.get.return_value = MagicMock(pk=1, email="test@example.com")

        request = self.factory.post(
            self.url, {"email": "test@example.com", "render_ts": 1234567890}
        )
        _add_middleware(request)

        with patch("time.time", return_value=1234567895):  # 5 seconds later
            response = MagicLinkRequestView.as_view()(request)

        # Verify success
        self.assertEqual(response.status_code, 200)
        mock_send_mail.assert_called_once()
