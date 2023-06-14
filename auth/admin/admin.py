from django.contrib import admin

from ..models import *


class ServiceAdmin(admin.ModelAdmin):
    model_fields = (
        "id",
        "slug",
        "name",
        "description",
    )
    list_display = model_fields
    search_fields = model_fields
    list_per_page = 25


admin.site.register(Service, ServiceAdmin)


class PreferenceAdmin(admin.ModelAdmin):
    fields = (
        "user",
        "service",
        "category",
        "name",
        "value",
    )
    list_display = fields
    search_fields = (
        "user__email",
        "service__name",
        "value",
    )
    raw_id_fields = ("user", "service")
    list_per_page = 25


admin.site.register(Preference, PreferenceAdmin)
