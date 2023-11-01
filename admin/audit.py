from django.contrib import admin


class AuditSummaryAdmin(admin.ModelAdmin):
    fields = (
        "id",
        "user",
        "content_type",
        "object_id",
        "content_object",
    )
    list_display = (
        "id",
        "user",
        "content_type",
        "object_id",
        "content_object",
    )
    readonly_fields = fields


class AuditDetailsAdmin(admin.ModelAdmin):
    fields = (
        "id",
        "audit_summary",
        "field_name",
        "old_value",
        "new_value",
    )
    list_display = (
        "id",
        "audit_summary",
        "field_name",
        "old_value",
        "new_value",
    )

    readonly_fields = fields
