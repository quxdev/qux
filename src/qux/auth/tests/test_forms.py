from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from qux.auth.forms import ChangePasswordForm, CustomAuthenticationForm, SignupForm

User = get_user_model()


class TestCustomAuthenticationFormInit(TestCase):
    """SignupForm.__init__ setting widget attrs."""

    def test_signup_form_init_sets_username_widget_attrs(self):
        form = SignupForm()
        attrs = form.fields["username"].widget.attrs
        assert "form-control foo-border" in attrs.get("class", "")
        assert "enter username or email address" in attrs.get("placeholder", "")


class TestCustomAuthenticationFormWidgetAttrs(TestCase):
    """CustomAuthenticationForm.__init__ sets widget attrs."""

    def test_init_sets_widget_attrs(self):
        form = CustomAuthenticationForm()
        username_attrs = form.fields["username"].widget.attrs
        assert "form-control foo-border" in username_attrs.get("class", "")
        password_attrs = form.fields["password"].widget.attrs
        assert "form-control foo-border" in password_attrs.get("class", "")


class TestChangePasswordFormCleanOldPasswordEmpty(TestCase):
    """Raising ValidationError for empty old_password."""

    def setUp(self):
        self.user = User.objects.create_user(username="cpuser", password="oldpass1234")

    def test_empty_old_password_raises_error(self):
        form = ChangePasswordForm(
            data={
                "old_password": "",
                "new_password": "newpass1234",
                "confirm_password": "newpass1234",
            },
            user=self.user,
        )
        assert not form.is_valid()
        assert "old_password" in form.errors

    def test_clean_old_password_empty_via_direct_call(self):
        """Clean_old_password with falsy old_password value."""
        form = ChangePasswordForm(
            data={
                "old_password": "placeholder",
                "new_password": "newpass1234",
                "confirm_password": "newpass1234",
            },
            user=self.user,
        )
        # Override cleaned_data to simulate a falsy old_password
        form.cleaned_data = {
            "old_password": "",
            "new_password": "newpass1234",
            "confirm_password": "newpass1234",
        }
        with self.assertRaises(ValidationError) as ctx:
            form.clean_old_password()
        assert "Enter valid password" in str(ctx.exception)

    def test_empty_new_password_raises_error(self):
        """Raising ValidationError for empty new_password."""
        form = ChangePasswordForm(
            data={
                "old_password": "oldpass1234",
                "new_password": "",
                "confirm_password": "",
            },
            user=self.user,
        )
        assert not form.is_valid()
        assert "new_password" in form.errors
