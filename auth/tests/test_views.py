from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import TestCase, RequestFactory, override_settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from qux.auth.forms import CustomAuthenticationForm
from qux.auth.tokens import account_activation_token
from qux.auth.views.appviews import (
    QuxSignupView,
    QuxActivateView,
    QuxLoginView,
    QuxChangePasswordView,
    QuxPasswordResetView,
    QuxPasswordResetDoneView,
    QuxPasswordResetConfirmView,
    QuxPasswordResetCompleteView,
    logout_request,
    login_request,
    send_signup_verification_email,
)

User = get_user_model()


def _add_middleware(request):
    """Add session and message middleware to a RequestFactory request."""
    middleware = SessionMiddleware(lambda req: HttpResponse())
    middleware.process_request(request)
    request.session.save()
    middleware = MessageMiddleware(lambda req: HttpResponse())
    middleware.process_request(request)


def _mock_render(*args, **kwargs):
    """Replacement for render that avoids TemplateNotFound."""
    return HttpResponse("rendered")


class TestQuxSignupViewGet(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("qux.auth.views.appviews.render", side_effect=_mock_render)
    def test_get_renders_signup_form(self, mock_render):
        request = self.factory.get("/auth/signup/")
        _add_middleware(request)
        response = QuxSignupView.as_view()(request)
        assert response.status_code == 200
        mock_render.assert_called_once()


class TestQuxSignupViewPost(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("qux.auth.views.appviews.render", side_effect=_mock_render)
    @patch(
        "qux.auth.views.appviews.send_signup_verification_email",
        return_value="test@qux.dev",
    )
    def test_post_valid_form(self, mock_send, _mock_render):
        request = self.factory.post(
            "/auth/signup/",
            {
                "email": "newuser@qux.dev",
                "password1": "Str0ngP@ss123!",
                "password2": "Str0ngP@ss123!",
            },
        )
        _add_middleware(request)
        response = QuxSignupView.as_view()(request)
        assert response.status_code == 200
        mock_send.assert_called_once()

    @patch("qux.auth.views.appviews.render", side_effect=_mock_render)
    def test_post_invalid_form(self, mock_render):
        request = self.factory.post(
            "/auth/signup/",
            {
                "email": "bad",
                "password1": "x",
                "password2": "y",
            },
        )
        _add_middleware(request)
        response = QuxSignupView.as_view()(request)
        assert response.status_code == 200
        # Should have been called (renders error message)
        mock_render.assert_called()


class TestQuxSignupViewUsernameCollision(TestCase):
    """Cover lines 67-68: username collision loop in signup."""

    def setUp(self):
        self.factory = RequestFactory()

    @patch("qux.auth.views.appviews.render", side_effect=_mock_render)
    @patch(
        "qux.auth.views.appviews.send_signup_verification_email",
        return_value="collision@qux.dev",
    )
    def test_username_collision_generates_unique(self, mock_send, _mock_render):
        # Create a user whose username matches the email we'll sign up with
        User.objects.create_user(
            username="collision@qux.dev",
            email="other@qux.dev",
            password="pass1234",
        )
        request = self.factory.post(
            "/auth/signup/",
            {
                "email": "collision@qux.dev",
                "password1": "Str0ngP@ss123!",
                "password2": "Str0ngP@ss123!",
            },
        )
        _add_middleware(request)
        response = QuxSignupView.as_view()(request)
        assert response.status_code == 200
        mock_send.assert_called_once()
        # The new user should have a modified username
        new_user = User.objects.get(email="collision@qux.dev")
        assert new_user.username != "collision@qux.dev"
        assert new_user.username.startswith("collision@qux.dev")


class TestSendSignupVerificationEmail(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="emailuser", email="emailuser@qux.dev", password="pass1234"
        )

    @patch(
        "qux.auth.views.appviews.render_to_string", return_value="<html>activate</html>"
    )
    @patch("qux.auth.views.appviews.EmailMessage")
    def test_sends_email(self, mock_email_cls, _mock_render_to_string):
        mock_email_instance = MagicMock()
        mock_email_cls.return_value = mock_email_instance

        request = self.factory.get("/auth/signup/")
        _add_middleware(request)

        form = MagicMock()
        form.cleaned_data.get.return_value = "emailuser@qux.dev"

        result = send_signup_verification_email(request, self.user, form)
        assert result == "emailuser@qux.dev"
        mock_email_instance.send.assert_called_once()


class TestQuxActivateView(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="activateuser",
            email="act@qux.dev",
            password="pass1234",
            is_active=False,
        )

    @patch("qux.auth.views.appviews.render", side_effect=_mock_render)
    def test_valid_activation(self, _mock_render):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = account_activation_token.make_token(self.user)
        request = self.factory.get(f"/auth/activate/{uid}/{token}/")
        _add_middleware(request)
        response = QuxActivateView.as_view()(request, uidb64=uid, token=token)
        assert response.status_code == 200
        self.user.refresh_from_db()
        assert self.user.is_active

    @patch("qux.auth.views.appviews.render", side_effect=_mock_render)
    def test_invalid_token(self, _mock_render):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        request = self.factory.get(f"/auth/activate/{uid}/bad-token/")
        _add_middleware(request)
        response = QuxActivateView.as_view()(request, uidb64=uid, token="bad-token")
        assert response.status_code == 200
        self.user.refresh_from_db()
        assert not self.user.is_active

    @patch("qux.auth.views.appviews.render", side_effect=_mock_render)
    def test_invalid_uid(self, _mock_render):
        uid = urlsafe_base64_encode(b"999999")
        request = self.factory.get(f"/auth/activate/{uid}/bad-token/")
        _add_middleware(request)
        response = QuxActivateView.as_view()(request, uidb64=uid, token="bad-token")
        assert response.status_code == 200


class TestQuxLoginView(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="loginuser", email="login@qux.dev", password="pass1234"
        )

    @patch("qux.auth.views.appviews.render", side_effect=_mock_render)
    def test_form_invalid_adds_message(self, _mock_render):
        request = self.factory.post(
            "/auth/login/",
            {
                "username": "loginuser",
                "password": "wrongpassword",
            },
        )
        _add_middleware(request)
        view = QuxLoginView()
        view.request = request
        view.setup(request)
        # Call form_invalid directly
        form = CustomAuthenticationForm(
            request=request,
            data={
                "username": "loginuser",
                "password": "wrong",
            },
        )
        form.is_valid()  # populate errors
        response = view.form_invalid(form)
        assert response.status_code == 200


class TestQuxChangePasswordView(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="cpuser", email="cp@qux.dev", password="oldpass1234"
        )

    @patch("qux.auth.views.appviews.render", side_effect=_mock_render)
    def test_get_requires_login(self, _mock_render):
        request = self.factory.get("/auth/change-password/")
        _add_middleware(request)
        request.user = AnonymousUser()
        response = QuxChangePasswordView.as_view()(request)
        assert response.status_code == 302  # redirect to login

    @patch("qux.auth.views.appviews.render", side_effect=_mock_render)
    def test_get_authenticated(self, _mock_render):
        request = self.factory.get("/auth/change-password/")
        _add_middleware(request)
        request.user = self.user
        response = QuxChangePasswordView.as_view()(request)
        assert response.status_code == 200

    @patch("qux.auth.views.appviews.render", side_effect=_mock_render)
    def test_post_valid(self, _mock_render):
        request = self.factory.post(
            "/auth/change-password/",
            {
                "old_password": "oldpass1234",
                "new_password": "newpass5678",
                "confirm_password": "newpass5678",
            },
        )
        _add_middleware(request)
        request.user = self.user
        response = QuxChangePasswordView.as_view()(request)
        assert response.status_code == 302  # redirect to /

    @patch("qux.auth.views.appviews.render", side_effect=_mock_render)
    def test_post_invalid(self, _mock_render):
        request = self.factory.post(
            "/auth/change-password/",
            {
                "old_password": "wrongpass",
                "new_password": "newpass5678",
                "confirm_password": "newpass5678",
            },
        )
        _add_middleware(request)
        request.user = self.user
        response = QuxChangePasswordView.as_view()(request)
        assert response.status_code == 200


class TestPasswordResetViews(TestCase):
    """Cover the password reset view classes by instantiation."""

    def test_password_reset_view_attrs(self):
        view = QuxPasswordResetView()
        assert view.email_template_name == "password_reset_email.html"

    def test_password_reset_done_view_attrs(self):
        view = QuxPasswordResetDoneView()
        assert view.template_name == "password_reset_done.html"

    def test_password_reset_confirm_view_attrs(self):
        view = QuxPasswordResetConfirmView()
        assert view.template_name is not None

    def test_password_reset_complete_view_attrs(self):
        view = QuxPasswordResetCompleteView()
        assert view.template_name == "password_reset_complete.html"


class TestLogoutRequest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="logoutuser", password="pass1234")

    def test_logout_redirects(self):
        request = self.factory.get("/auth/logout/")
        _add_middleware(request)
        request.user = self.user
        response = logout_request(request)
        assert response.status_code == 302
        assert response.url == "/"


@override_settings(LOGIN_REDIRECT_URL="/dashboard/")
class TestLoginRequest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="lruser", email="lr@qux.dev", password="pass1234"
        )

    @patch("qux.auth.views.appviews.render", side_effect=_mock_render)
    def test_authenticated_user_redirects(self, _mock_render):
        request = self.factory.get("/auth/login/")
        _add_middleware(request)
        request.user = self.user
        response = login_request(request)
        assert response.status_code == 302
        assert response.url == "/dashboard/"

    @patch("qux.auth.views.appviews.render", side_effect=_mock_render)
    def test_post_valid_login(self, _mock_render):
        request = self.factory.post(
            "/auth/login/",
            {
                "username": "lruser",
                "password": "pass1234",
            },
        )
        _add_middleware(request)
        request.user = AnonymousUser()
        response = login_request(request)
        assert response.status_code == 302
        assert response.url == "/dashboard/"

    @patch("qux.auth.views.appviews.render", side_effect=_mock_render)
    def test_post_valid_login_with_next(self, _mock_render):
        request = self.factory.post(
            "/auth/login/?next=/profile/",
            {
                "username": "lruser",
                "password": "pass1234",
            },
        )
        _add_middleware(request)
        request.user = AnonymousUser()
        response = login_request(request)
        assert response.status_code == 302
        assert response.url == "/profile/"

    @patch("qux.auth.views.appviews.render", side_effect=_mock_render)
    def test_post_invalid_credentials(self, _mock_render):
        request = self.factory.post(
            "/auth/login/",
            {
                "username": "lruser",
                "password": "wrongpass",
            },
        )
        _add_middleware(request)
        request.user = AnonymousUser()
        response = login_request(request)
        assert response.status_code == 200

    @patch("qux.auth.views.appviews.render", side_effect=_mock_render)
    def test_post_invalid_form(self, _mock_render):
        request = self.factory.post(
            "/auth/login/",
            {
                "username": "",
                "password": "",
            },
        )
        _add_middleware(request)
        request.user = AnonymousUser()
        response = login_request(request)
        assert response.status_code == 200

    @patch("qux.auth.views.appviews.render", side_effect=_mock_render)
    def test_get_renders_login_form(self, _mock_render):
        request = self.factory.get("/auth/login/")
        _add_middleware(request)
        request.user = AnonymousUser()
        response = login_request(request)
        assert response.status_code == 200

    @patch("qux.auth.views.appviews.render", side_effect=_mock_render)
    @patch("qux.auth.views.appviews.authenticate", return_value=None)
    def test_post_form_valid_but_authenticate_none(self, _mock_auth, _mock_render):
        """Cover line 312: form.is_valid() True but authenticate returns None."""
        request = self.factory.post(
            "/auth/login/",
            {
                "username": "lruser",
                "password": "pass1234",
            },
        )
        _add_middleware(request)
        request.user = AnonymousUser()
        response = login_request(request)
        assert response.status_code == 200
