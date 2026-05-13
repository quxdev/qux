"""Bootstrap-styled Django form base classes.

Subclass ``QuxForm`` (instead of ``forms.Form``) or ``QuxModelForm`` (instead
of ``forms.ModelForm``) to get Bootstrap CSS classes auto-applied to every
visible widget: ``form-control`` for inputs, ``form-check-input`` for
checkboxes, ``form-select`` for selects, ``custom-file-input`` for file
uploads. Saves operators from manually decorating every widget in their
form ``Meta.widgets`` map.
"""

from django import forms


class QuxForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs["class"] = "form-control"

            # Identify file uploads and adjusts
            # getbootstrap.com/docs/4.6/components/input-group/#custom-file-input
            if isinstance(visible.field.widget, forms.widgets.ClearableFileInput):
                visible.field.widget.attrs["class"] += " custom-file-input"

            if isinstance(visible.field.widget, forms.widgets.CheckboxInput):
                visible.field.widget.attrs["class"] = "form-check-input"

            if isinstance(visible.field.widget, forms.widgets.Select):
                visible.field.widget.attrs["class"] = "form-select"


class QuxModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs["class"] = "form-control"

            # Identify file uploads and adjusts
            # getbootstrap.com/docs/4.6/components/input-group/#custom-file-input
            if isinstance(visible.field.widget, forms.widgets.ClearableFileInput):
                visible.field.widget.attrs["class"] += " custom-file-input"

            if isinstance(visible.field.widget, forms.widgets.CheckboxInput):
                visible.field.widget.attrs["class"] = "form-check-input"

            if isinstance(visible.field.widget, forms.widgets.Select):
                visible.field.widget.attrs["class"] = "form-select"
