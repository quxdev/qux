from core.models import CoreModelPlusAdmin
from .models import *
from django.contrib import admin


class CustomTokenAdmin(CoreModelPlusAdmin):
    list_display = ('id', 'user', 'name',) + CoreModelPlusAdmin.list_display
    search_fields = ('id', 'user__username', 'name',)
    raw_id_fields = ('user',)
    readonly_fields = ('key', )


admin.site.register(CustomToken, CustomTokenAdmin)
