from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext as _

from .models import *


class CoreUserAdmin(UserAdmin):
    list_display = (
        'id', 'is_active', 'username', 'email', 'first_name', 'last_name',
        'is_superuser', 'date_joined', 'last_login', 'groups_name'
    )
    list_filter = (
        'is_staff', 'is_superuser', 'is_active', 'groups',
        ('date_joined', DateRangeFilter),
        ('last_login', DateRangeFilter),
    )
    search_fields = (
        'id', 'username', 'email', 'date_joined',
        'last_login', 'is_superuser', 'is_staff', 'is_active'
    )
    # fieldsets = (
    #     (None, {'fields': ('username', 'password')}),
    #     (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
    #     (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'user_permissions')}),
    #     (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    # )
    ordering = ('-id',)

    def get_queryset(self, request):
        return super(CoreUserAdmin, self).get_queryset(request).prefetch_related('groups')

    # def save_model(self, request, obj, form, change):
    #     obj.save()
    #     if 'is_staff' in form.changed_data:
    #         staff_default = Group.objects.get(name='staff_default')
    #         if obj.is_staff:
    #             obj.groups.add(staff_default)
    #         else:
    #             obj.groups.remove(staff_default)
    #         obj.save()

    @staticmethod
    def groups_name(obj):
        try:
            arr = []
            for group in obj.groups.all():
                arr.append(group.name)
            return ', '.join(arr)
        except:
            return ""


admin.site.unregister(User)
admin.site.register(User, CoreUserAdmin)


class CompanyAdmin(CoreModelAdmin):
    model_fields = ('id', 'name', 'domain')
    list_display = model_fields + CoreModelAdmin.list_display
    search_fields = model_fields


admin.site.register(Company, CompanyAdmin)


class ProfileAdmin(CoreModelAdmin):
    model_fields = ('id', 'user', 'phone', 'company', 'title')
    list_display = model_fields + CoreModelAdmin.list_display
    search_fields = ('id', 'user__email', 'phone', 'company__name', 'title')
    raw_id_fields = ('user', 'company',)


admin.site.register(Profile, ProfileAdmin)
