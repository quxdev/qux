from django import forms

from .models import CustomToken


class CustomTokenForm(forms.ModelForm):
    class Meta:
        model = CustomToken
        fields = [
            "name",
        ]

    def save(self, commit=None, user=None):  # pylint: disable=unused-argument
        newform = super().save(commit=False)
        if user:
            newform.user = user
        newform.save()
        return newform

    name = forms.CharField(
        label="Name",
        widget=forms.TextInput(
            attrs={
                "class": "form-control foo-border",
                "placeholder": "Enter name",
            }
        ),
    )
