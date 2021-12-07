from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ObjectDoesNotExist
from django.forms import ValidationError
from django.contrib.auth.models import User


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label='Email address',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control foo-border',
                'placeholder': 'email@qux.dev'
            }
        )
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control foo-border',
                'placeholder': 'password'
            }
        )
    )

    error_messages = {
        'invalid_login': "Please enter a correct %(username)s and password. "
                         "Note that both fields may be case-sensitive.",
        'inactive': "This account is inactive.",
    }

    def clean_username(self):
        username = self.data['username']
        if '@' in username:
            try:
                username = User.objects.get(email=username).username
            except ObjectDoesNotExist:
                raise ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                    params={'username': self.username_field.verbose_name},
                )
        return username


class SignupForm(UserCreationForm):
    email = forms.EmailField(
        label='Email address',
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                'class': 'form-control foo-border',
                'placeholder': 'Enter valid email address',
                'autocomplete': 'email'
            }
        ),
        help_text='Required'
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super(SignupForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control foo-border',
            'placeholder': 'enter username or email address'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control foo-border',
            'placeholder': 'Enter password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control foo-border',
            'placeholder': 'Enter same password again'
        })



class ChangePasswordForm(forms.Form):
    old_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
            }
        )
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
            }
        )
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control'
            }
        )
    )

    def __init__(self, *args, **kwargs):
        print(args, kwargs, "\n\n context printing")
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')
        if not old_password:
            raise forms.ValidationError("Enter valid password")
        if not self.user.check_password(old_password):
            raise forms.ValidationError("Your password doesn't match")
        return old_password

    def clean(self):
        new_pass = self.cleaned_data.get('new_password')
        if not new_pass:
            raise forms.ValidationError(
                {
                    'new_password': 'Please enter a new password'
                }
            )

        confirm_pass = self.cleaned_data.get('confirm_password')
        if not new_pass == confirm_pass:
            raise forms.ValidationError(
                {
                    'confirm_password': 'New passwords do not match each other'
                }
            )

        return self.cleaned_data


class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        label='Email address',
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                'class': 'form-control foo-border',
                'placeholder': 'email@qux.dev',
                'autocomplete': 'email'
            }
        )
    )


class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label="New password",
        widget=forms.PasswordInput(
            attrs={'class': 'form-control foo-border', 'autocomplete': 'new-password'}),
        strip=False,
        help_text=password_validation.password_validators_help_text_html(),
    )
    new_password2 = forms.CharField(
        label="New password confirmation",
        strip=False,
        widget=forms.PasswordInput(
            attrs={'class': 'form-control foo-border', 'autocomplete': 'new-password'}),
    )
