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
        fields = list(
            dict.fromkeys(
                [field.name for field in self.opts.local_fields]
                + [field.name for field in self.opts.local_many_to_many]
            )
        )
        return tuple(f for f in fields if f not in self.excluded)

    def get_readonly_fields(self, request, obj=None):
        fields = list(
            dict.fromkeys(
                [field.name for field in self.opts.local_fields]
                + [field.name for field in self.opts.local_many_to_many]
            )
        )
        return tuple(f for f in fields if f in self.readonly)

    def get_list_display(self, request):
        fields = [field.name for field in self.opts.local_fields]
        return tuple(f for f in fields if f not in self.excluded)
