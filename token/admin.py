from django.contrib import admin

from .models import *


@admin.register(CustomToken)
class CustomTokenAdmin(admin.ModelAdmin):
    fields = (
        "name",
        "user",
        "key",
    )
    list_display = (
        "id",
        "user",
        "name",
    )
    search_fields = (
        "id",
        "user__username",
        "name",
    )
    raw_id_fields = ("user",)
    readonly_fields = ("key",)
