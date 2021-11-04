from django.contrib import admin

from qux.models import CoreModelAdmin
from .models import SEOSite, SEOPage


class SEOSiteAdmin(CoreModelAdmin):
    model_fields = ('id', 'site', 'name', 'title', 'domain', 'twitter')
    list_display = model_fields + CoreModelAdmin.list_display
    search_fields = model_fields


admin.site.register(SEOSite, SEOSiteAdmin)


class SEOPageAdmin(CoreModelAdmin):
    model_fields = ('id', 'canonical', 'page_name', 'page_title', 'description', 'keywords')
    list_display = model_fields + CoreModelAdmin.list_display
    search_fields = model_fields


admin.site.register(SEOPage, SEOPageAdmin)
