from django import forms

from .models import CustomToken


class CustomTokenForm(forms.ModelForm):
    class Meta:
        model = CustomToken
        fields = [
            "name",
        ]

    def save(self, commit=True, user=None):
        newform = super().save(commit=False)
        if user:
            newform.user = user

        if commit:
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
