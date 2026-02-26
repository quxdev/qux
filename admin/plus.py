from .base import QuxModelAdmin


class QuxPlusModelAdmin(QuxModelAdmin):
    list_filter = ("is_deleted",)

    def get_queryset(self, request):
        """
        Returns a QuerySet of all model instances that can be edited by the
        admin site. This is used by changelist_view.
        """

        # Default: qs = self.model._default_manager.get_query_set()
        # pylint: disable=protected-access
        qs = self.model._default_manager.all_with_deleted()

        ordering = self.ordering or ()
        if ordering:
            qs = qs.order_by(*ordering)
        return qs
