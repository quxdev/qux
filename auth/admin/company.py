from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from ..models import Company, Profile


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


class ProfileAdmin(admin.ModelAdmin):
    fields = (
        "id",
        "slug",
        "user",
        "phone",
        "company",
        "title",
        "is_live",
    )
    readonly_fields = (
        "id",
        "slug",
    )
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
    list_editable = ("is_live",)


admin.site.register(Profile, ProfileAdmin)
