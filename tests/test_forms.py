from django import forms
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from qux.auth.forms import (
    BaseSignupForm,
    ChangePasswordForm,
    CustomAuthenticationForm,
)
from qux.forms import QuxForm, QuxModelForm

User = get_user_model()


# ---------------------------------------------------------------------------
# QuxForm CSS class tests (no DB needed)
# ---------------------------------------------------------------------------


class SampleQuxForm(QuxForm):
    name = forms.CharField()
    agree = forms.BooleanField()
    document = forms.FileField()
    choice = forms.ChoiceField(choices=[("a", "A"), ("b", "B")])


class TestQuxFormCSSClasses(SimpleTestCase):
    def test_charfield_gets_form_control(self):
        form = SampleQuxForm()
        widget_attrs = form.fields["name"].widget.attrs
        assert widget_attrs["class"] == "form-control"

    def test_booleanfield_gets_form_check_input(self):
        form = SampleQuxForm()
        widget_attrs = form.fields["agree"].widget.attrs
        assert widget_attrs["class"] == "form-check-input"

    def test_filefield_gets_custom_file_input(self):
        form = SampleQuxForm()
        widget_attrs = form.fields["document"].widget.attrs
        assert "form-control" in widget_attrs["class"]
        assert "custom-file-input" in widget_attrs["class"]

    def test_choicefield_gets_form_select(self):
        form = SampleQuxForm()
        widget_attrs = form.fields["choice"].widget.attrs
        assert widget_attrs["class"] == "form-select"


# ---------------------------------------------------------------------------
# Auth form tests (need DB)
# ---------------------------------------------------------------------------


class TestCustomAuthenticationForm(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )

    def test_email_login_resolves_to_username(self):
        form = CustomAuthenticationForm(
            data={"username": "test@example.com", "password": "testpass123"}
        )
        # clean_username should resolve the email to the username
        _cleaned = form.fields["username"]
        # We call clean_username via is_valid; even if auth fails, clean_username runs
        form.is_valid()
        # After cleaning, the username field data should have been resolved
        assert form.cleaned_data.get("username") == "testuser"

    def test_nonexistent_email_raises_validation_error(self):
        form = CustomAuthenticationForm(
            data={"username": "nobody@example.com", "password": "testpass123"}
        )
        valid = form.is_valid()
        assert valid is False
        # The error should be in the username field
        assert "username" in form.errors

    def test_regular_username_passes_through(self):
        form = CustomAuthenticationForm(
            data={"username": "testuser", "password": "testpass123"}
        )
        form.is_valid()
        assert form.cleaned_data.get("username") == "testuser"


class TestBaseSignupForm(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="existing",
            email="taken@example.com",
            password="testpass123",
        )

    def test_duplicate_email_raises_validation_error(self):
        form = BaseSignupForm(
            data={
                "email": "taken@example.com",
                "password1": "Str0ngP@ssword!",
                "password2": "Str0ngP@ssword!",
            }
        )
        valid = form.is_valid()
        assert valid is False
        assert "email" in form.errors

    def test_unique_email_passes(self):
        form = BaseSignupForm(
            data={
                "email": "new@example.com",
                "password1": "Str0ngP@ssword!",
                "password2": "Str0ngP@ssword!",
            }
        )
        # BaseSignupForm also requires username from UserCreationForm Meta
        # but Meta.fields = ("email", "password1", "password2"), so username
        # may or may not be required depending on the User model.
        # We check that at least the email field itself has no errors.
        form.is_valid()
        assert "email" not in form.errors


class TestChangePasswordForm(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="chgpwduser",
            email="chgpwd@example.com",
            password="OldPass123!",
        )

    def test_wrong_old_password_raises(self):
        form = ChangePasswordForm(
            data={
                "old_password": "WrongPassword",
                "new_password": "NewPass456!",
                "confirm_password": "NewPass456!",
            },
            user=self.user,
        )
        valid = form.is_valid()
        assert valid is False
        assert "old_password" in form.errors

    def test_mismatched_new_passwords_raises(self):
        form = ChangePasswordForm(
            data={
                "old_password": "OldPass123!",
                "new_password": "NewPass456!",
                "confirm_password": "DifferentPass789!",
            },
            user=self.user,
        )
        valid = form.is_valid()
        assert valid is False
        assert "confirm_password" in form.errors

    def test_correct_data_passes(self):
        form = ChangePasswordForm(
            data={
                "old_password": "OldPass123!",
                "new_password": "NewPass456!",
                "confirm_password": "NewPass456!",
            },
            user=self.user,
        )
        valid = form.is_valid()
        assert valid is True


# ---------------------------------------------------------------------------
# QuxModelForm CSS class tests (lines 24-37)
# ---------------------------------------------------------------------------


class SampleQuxModelForm(QuxModelForm):
    """A model form using QuxModelForm to test CSS class assignment."""

    name = forms.CharField()
    agree = forms.BooleanField()
    document = forms.FileField()
    choice = forms.ChoiceField(choices=[("a", "A"), ("b", "B")])

    class Meta:
        # Use auth.User as a stand-in model — we only care about the form fields
        model = User
        fields = []  # No model fields; all fields are declared above


class TestQuxModelFormCSSClasses(SimpleTestCase):
    """Cover QuxModelForm.__init__ lines 24-37."""

    def test_charfield_gets_form_control(self):
        form = SampleQuxModelForm()
        widget_attrs = form.fields["name"].widget.attrs
        assert widget_attrs["class"] == "form-control"

    def test_booleanfield_gets_form_check_input(self):
        form = SampleQuxModelForm()
        widget_attrs = form.fields["agree"].widget.attrs
        assert widget_attrs["class"] == "form-check-input"

    def test_filefield_gets_custom_file_input(self):
        form = SampleQuxModelForm()
        widget_attrs = form.fields["document"].widget.attrs
        assert "form-control" in widget_attrs["class"]
        assert "custom-file-input" in widget_attrs["class"]

    def test_choicefield_gets_form_select(self):
        form = SampleQuxModelForm()
        widget_attrs = form.fields["choice"].widget.attrs
        assert widget_attrs["class"] == "form-select"
