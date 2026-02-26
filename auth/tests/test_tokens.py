from django.contrib.auth import get_user_model
from django.test import TestCase

from qux.auth.tokens import account_activation_token

User = get_user_model()


class TestAccountActivationToken(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="tokenuser", password="pass1234", is_active=False
        )

    def test_make_token_returns_string(self):
        token = account_activation_token.make_token(self.user)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_check_token_valid(self):
        token = account_activation_token.make_token(self.user)
        assert account_activation_token.check_token(self.user, token) is True

    def test_invalid_after_password_change(self):
        token = account_activation_token.make_token(self.user)
        self.user.set_password("newpassword")
        self.user.save()
        self.user.refresh_from_db()
        assert account_activation_token.check_token(self.user, token) is False

    def test_invalid_after_is_active_change(self):
        token = account_activation_token.make_token(self.user)
        self.user.is_active = True
        self.user.save()
        self.user.refresh_from_db()
        assert account_activation_token.check_token(self.user, token) is False
