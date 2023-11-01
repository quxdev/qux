from django.contrib import admin
from django.contrib.admin.utils import flatten_fieldsets


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
        fields = tuple([f for f in fields if f not in self.excluded])
        return fields

    def get_readonly_fields(self, request, obj=None):
        fields = list(set(
            [field.name for field in self.opts.local_fields] +
            [field.name for field in self.opts.local_many_to_many]
        ))
        fields = tuple([f for f in fields if f in self.readonly])
        return fields

    def get_list_display(self, request):
        fields = super().get_list_display(request)
        fields = tuple([f for f in fields if f not in self.excluded])
        return fields
