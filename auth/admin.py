from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from rangefilter.filters import DateRangeFilter

from .models import *
from qux.models import CoreModelAdmin


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
    ordering = ('-id',)

    def get_queryset(self, request):
        return super(CoreUserAdmin, self).get_queryset(request).prefetch_related('groups')

    @staticmethod
    def groups_name(obj):
        arr = [group.name for group in obj.groups.all()]
        return ', '.join(arr)


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
