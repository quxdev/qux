from django.contrib import admin


class QuxModelAdmin(admin.ModelAdmin):
    excluded = (
        "dtm_created",
        "dtm_updated",
    )
    readonly = (
        "id",
        "slug",
    )

    list_per_page = 50
    show_full_result_count = False

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        fields = [f for f in fields if f not in self.excluded]
        return fields

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        fields = [f for f in fields if f in self.readonly]
        return fields

    def get_list_display(self, request):
        fields = super().list_display(request)
        fields = [f for f in fields if f not in self.excluded]
        return fields
