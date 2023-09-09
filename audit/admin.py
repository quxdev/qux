from django.contrib import admin

from .models import (
    ModelAuditSummary,
    ModelAuditDetails,
)
from ..admin import (
    AuditSummaryAdmin,
    AuditDetailsAdmin,
)


@admin.register(ModelAuditSummary)
class ModelAuditSummaryAdmin(AuditSummaryAdmin):
    pass


@admin.register(ModelAuditDetails)
class ModelAuditDetailsAdmin(AuditDetailsAdmin):
    pass
