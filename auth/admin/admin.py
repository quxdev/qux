from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from qux.models import CoreModelAdmin
from ..models import *


class CoreUserAdmin(UserAdmin):
    list_display = (
        "id",
        "is_active",
        "username",
        "email",
        "first_name",
        "last_name",
        "is_superuser",
        "date_joined",
        "last_login",
        "groups_name",
    )
    list_filter = (
        "is_staff",
        "is_superuser",
        "is_active",
        "groups",
    )
    search_fields = (
        "id",
        "username",
        "email",
        "date_joined",
        "last_login",
        "is_superuser",
        "is_staff",
        "is_active",
    )
    ordering = ("-id",)

    def get_queryset(self, request):
        return (
            super(CoreUserAdmin, self).get_queryset(request).prefetch_related("groups")
        )

    @staticmethod
    def groups_name(obj):
        arr = [group.name for group in obj.groups.all()]
        return ", ".join(arr)


admin.site.unregister(User)
admin.site.register(User, CoreUserAdmin)


class ServiceModeAdmin(admin.ModelAdmin):
    fields = (
        "slug",
        "name",
        "description",
    )
    readonly_fields = (
        "slug",
    )
    list_display = ("id", ) + fields
    list_editable = ("slug", "name",)


admin.site.register(ServiceMode, ServiceModeAdmin)


class ProfileAdmin(CoreModelAdmin):
    fields = (
        "id",
        "slug",
        "user",
        "phone",
        "company",
        "title",
        "is_live",
    )
    readonly_fields = ("id", "slug",)
    list_display = fields
    search_fields = (
        "user__email",
        "phone",
        "company__name",
        "title",
    )
    raw_id_fields = (
        "user",
        "company",
    )
    list_editable = (
        "is_live",
    )


admin.site.register(Profile, ProfileAdmin)


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
