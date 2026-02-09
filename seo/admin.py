from django.contrib import admin

from qux.admin import QuxModelAdmin
from .models import SEOSite, SEOPage


@admin.register(SEOSite)
class SEOSiteAdmin(QuxModelAdmin):
    list_display = ("site", "name", "domain", "twitter")
    search_fields = ("name", "domain")


@admin.register(SEOPage)
class SEOPageAdmin(QuxModelAdmin):
    list_display = ("site", "canonical", "page_name", "page_title")
    list_filter = ("site",)
    search_fields = ("canonical", "page_name", "page_title")
