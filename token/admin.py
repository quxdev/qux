from django.contrib import admin

from .models import CustomToken


@admin.register(CustomToken)
class CustomTokenAdmin(admin.ModelAdmin):
    fields = (
        "user",
        "name",
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
