from django import forms

from .models import CustomToken


class CustomTokenForm(forms.ModelForm):
    class Meta:
        model = CustomToken
        fields = [
            "name",
        ]

    def save(self, user=None):
        newform = super(CustomTokenForm, self).save(commit=False)
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
