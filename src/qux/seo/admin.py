from django.contrib import admin

from qux.admin import QuxModelAdmin

from .models import SEOAudit, SEOAuditURL, SEOPage, SEOSite


@admin.register(SEOSite)
class SEOSiteAdmin(QuxModelAdmin):
    list_display = ("site", "name", "domain", "twitter")
    search_fields = ("name", "domain")


@admin.register(SEOPage)
class SEOPageAdmin(QuxModelAdmin):
    list_display = ("site", "canonical", "page_name", "page_title")
    list_filter = ("site",)
    search_fields = ("canonical", "page_name", "page_title")


class SEOAuditURLInline(admin.TabularInline):
    model = SEOAuditURL
    fields = ("url", "status_code", "title", "canonical", "errors", "warnings")
    readonly_fields = fields
    extra = 0
    show_change_link = True


@admin.register(SEOAudit)
class SEOAuditAdmin(admin.ModelAdmin):
    list_display = (
        "domain",
        "status",
        "total_urls",
        "total_errors",
        "total_warnings",
        "dtm_audited",
    )
    list_filter = ("status", "domain")
    search_fields = ("domain",)
    readonly_fields = (
        "domain",
        "status",
        "total_urls",
        "total_errors",
        "total_warnings",
        "dtm_audited",
    )
    inlines = [SEOAuditURLInline]


@admin.register(SEOAuditURL)
class SEOAuditURLAdmin(admin.ModelAdmin):
    list_display = (
        "url",
        "audit",
        "status_code",
        "title",
        "error_count",
        "warning_count",
    )
    list_filter = ("audit__domain", "status_code")
    search_fields = ("url", "title", "canonical")
    readonly_fields = (
        "audit",
        "url",
        "status_code",
        "title",
        "meta_description",
        "canonical",
        "og_url",
        "og_title",
        "og_description",
        "og_image",
        "og_site_name",
        "twitter_card",
        "twitter_title",
        "twitter_description",
        "twitter_image",
        "errors",
        "warnings",
    )

    @admin.display(description="Errors")
    def error_count(self, obj):
        return len(obj.errors)

    @admin.display(description="Warnings")
    def warning_count(self, obj):
        return len(obj.warnings)
