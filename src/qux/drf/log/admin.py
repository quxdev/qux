import datetime

from django.contrib import admin
from django.db.models import Count, Q
from django.db.models.functions import TruncDay
from django.http import JsonResponse
from django.urls import path

from .app_settings import app_settings
from .models import APILoggingRule, APIRequestLog


class APIRequestLogAdmin(admin.ModelAdmin):
    date_hierarchy = "requested_at"
    list_display = (
        "id",
        "requested_at",
        "response_ms",
        "method",
        "path",
        "status_code",
        "get_username",
        "view_method",
        "remote_addr",
        "host",
        # "query_params",
    )
    ordering = ("-requested_at",)
    list_filter = ("view_method", "status_code", "method")
    search_fields = ("path", "username_persistent", "remote_addr", "host")

    if app_settings.ADMIN_LOG_READONLY:
        readonly_fields = (
            "user",
            "username_persistent",
            "requested_at",
            "response_ms",
            "method",
            "path",
            "view",
            "view_method",
            "remote_addr",
            "host",
            # "query_params",
            "data",
            "response",
            "errors",
            "status_code",
        )

    def changelist_view(self, request, extra_context=None):
        # Aggregate api logs per day
        chart_data = self.chart_data_default()

        extra_context = extra_context or {"chart_data": list(chart_data)}

        # Call the superclass changelist_view to render the page
        return super().changelist_view(request, extra_context=extra_context)

    def get_username(self, obj):
        """Human readable username field for list display."""
        return obj.username_persistent or obj.user

    get_username.short_description = "User"

    def get_urls(self):
        urls = super().get_urls()
        extra_urls = [path("chart_data/", self.admin_site.admin_view(self.chart_data_endpoint))]
        return extra_urls + urls

    # JSON endpoint for generating chart data that is used for dynamic loading
    # via JS.
    def chart_data_endpoint(self, request):
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")

        if not start_date or not end_date:
            return JsonResponse({"error": "start_date and end_date are required"}, status=400)

        try:
            start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            return JsonResponse({"error": "Invalid date format, use YYYY-MM-DD"}, status=400)

        chart_data = self.chart_data(start_date, end_date)
        return JsonResponse(list(chart_data), safe=False)

    def chart_data_default(self):
        return (
            APIRequestLog.objects.annotate(date=TruncDay("requested_at"))
            .values("date")
            .annotate(
                y=Count("id"),
                y2xx=Count("id", filter=Q(status_code__gte=200, status_code__lt=300)),
                y4xx=Count("id", filter=Q(status_code__gte=400, status_code__lt=500)),
                y5xx=Count("id", filter=Q(status_code__gte=500)),
            )
            .order_by("-date")
        )

    def chart_data(self, start_date, end_date):
        return (
            APIRequestLog.objects.filter(
                requested_at__date__gte=start_date, requested_at__date__lte=end_date
            )
            .annotate(date=TruncDay("requested_at"))
            .values("date")
            .annotate(
                y=Count("id"),
                y2xx=Count("id", filter=Q(status_code__gte=200, status_code__lt=300)),
                y4xx=Count("id", filter=Q(status_code__gte=400, status_code__lt=500)),
                y5xx=Count("id", filter=Q(status_code__gte=500)),
            )
            .order_by("-date")
        )


admin.site.register(APIRequestLog, APIRequestLogAdmin)


@admin.register(APILoggingRule)
class APILoggingRuleAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "enabled", "active", "dtm_updated")
    list_filter = ("enabled", "active")
    search_fields = ("user__username", "user__email", "notes")

    actions = ("enable_selected", "disable_selected")

    def enable_selected(self, request, queryset):  # type: ignore[no-untyped-def]
        queryset.update(enabled=True, active=True)

    enable_selected.short_description = "Enable logging for selected users"

    def disable_selected(self, request, queryset):  # type: ignore[no-untyped-def]
        queryset.update(enabled=False, active=True)

    disable_selected.short_description = "Disable logging for selected users"
