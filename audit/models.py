from django.db import models

from ..models import CoreModelAuditSummary, CoreModelAuditDetails


class ModelAuditSummary(CoreModelAuditSummary):
    db_table = "qux_audit_summary"
    verbose_name = "Model Audit Summary"
    verbose_name_plural = "Model Audit Summaries"


class ModelAuditDetails(CoreModelAuditDetails):
    audit_summary = models.ForeignKey(
        ModelAuditSummary, on_delete=models.CASCADE, related_name="details"
    )

    class Meta:
        db_table = "qux_audit_details"
        verbose_name = "Model Audit Detail"
        verbose_name_plural = "Model Audit Details"
