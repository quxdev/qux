from django import forms
from django.contrib import admin

from ..models import *


class CompanyField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.slug}: {obj.name}" if obj.name else obj.slug


class CompanyAdmin(admin.ModelAdmin):
    fields = (
        "name",
        "domain",
    )
    list_display = (
        "id",
        "slug",
    ) + fields
    list_editable = (
        "slug",
        "name",
        "domain",
    )


admin.site.register(Company, CompanyAdmin)
