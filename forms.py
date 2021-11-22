from django import forms


class QuxForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(QuxForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

            # Identify file uploads and adjusts
            # getbootstrap.com/docs/4.6/components/input-group/#custom-file-input
            if type(visible.field.widget) is forms.widgets.ClearableFileInput:
                visible.field.widget.attrs['class'] += ' custom-file-input'
