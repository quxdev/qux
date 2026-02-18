from django.contrib.auth import get_user_model
from django.db import models

from qux.models.base import CoreModel, default_null_blank
from qux.models.plus import CoreModelPlus
from qux.models.audit import CoreModelAuditSummary, CoreModelAuditDetails
from qux.models.base import AbstractLead
from qux.models.contacts import AbstractCompany, AbstractProfile
from qux.contacts.models import AbstractContactPhone, AbstractContactEmail
from qux.modelfields import FloatListField


class SimpleItem(CoreModel):
    name = models.CharField(max_length=64)

    class Meta:
        app_label = "tests"

    def __str__(self):
        return self.name


class SlugItem(CoreModel):
    SLUG_PREFIX = "item"
    SLUG_ALLOWED_CHARS = "abcdefghijklmnopqrstuvwxyz"

    slug = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=64)

    class Meta:
        app_label = "tests"

    def __str__(self):
        return self.name


class TagItem(CoreModel):
    name = models.CharField(max_length=64)
    tags = models.CharField(max_length=256, **default_null_blank)

    class Meta:
        app_label = "tests"


class RandomItem(CoreModel):
    char_field = models.CharField(max_length=32)
    text_field = models.TextField(**default_null_blank)
    int_field = models.IntegerField(**default_null_blank)
    bool_field = models.BooleanField(default=False)
    email_field = models.EmailField(**default_null_blank)
    url_field = models.URLField(**default_null_blank)
    # Non-nullable versions for randomize() testing (randomize skips null fields)
    text_field_required = models.TextField(default="")
    int_field_required = models.IntegerField(default=0)
    email_field_required = models.EmailField(max_length=254, default="")
    url_field_required = models.URLField(default="")
    # Additional field types for randomize() coverage
    decimal_field_required = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    date_field_required = models.DateField(default="2000-01-01")
    datetime_field_required = models.DateTimeField(
        auto_now=False, default="2000-01-01T00:00:00Z"
    )

    class Meta:
        app_label = "tests"


class M2MRelated(CoreModel):
    name = models.CharField(max_length=64)

    class Meta:
        app_label = "tests"


class M2MItem(CoreModel):
    name = models.CharField(max_length=64)
    related = models.ManyToManyField(M2MRelated, blank=True)

    class Meta:
        app_label = "tests"


class SoftDeleteItem(CoreModelPlus):
    name = models.CharField(max_length=64)

    class Meta:
        app_label = "tests"

    def __str__(self):
        return self.name


class TestAuditSummary(CoreModelAuditSummary):
    class Meta:
        app_label = "tests"


class TestAuditDetails(CoreModelAuditDetails):
    audit_summary = models.ForeignKey(
        TestAuditSummary, on_delete=models.CASCADE, related_name="details"
    )

    class Meta:
        app_label = "tests"


class BareAuditSummary(CoreModelAuditSummary):
    """Audit summary with no details FK pointing to it — for testing NotImplementedError."""

    class Meta:
        app_label = "tests"


class AuditedItem(CoreModel):
    AUDIT_MODE = True
    AUDIT_SUMMARY = TestAuditSummary
    AUDIT_DETAILS = TestAuditDetails

    name = models.CharField(max_length=64)
    user = models.ForeignKey(
        get_user_model(), on_delete=models.SET_NULL, **default_null_blank
    )

    class Meta:
        app_label = "tests"


class TestCompany(AbstractCompany):
    class Meta(AbstractCompany.Meta):
        app_label = "tests"


class TestProfile(AbstractProfile):
    class Meta(AbstractProfile.Meta):
        app_label = "tests"


class TestLead(AbstractLead):
    class Meta:
        app_label = "tests"


class TestContactPhone(AbstractContactPhone):
    class Meta:
        app_label = "tests"


class TestContactEmail(AbstractContactEmail):
    class Meta:
        app_label = "tests"


class FloatListItem(CoreModel):
    values = FloatListField(**default_null_blank)

    class Meta:
        app_label = "tests"


class FKTarget(CoreModel):
    """Target model for ForeignKey randomize() testing."""

    name = models.CharField(max_length=64)

    class Meta:
        app_label = "tests"


class FKSource(CoreModel):
    """Source model with a required FK for randomize() testing."""

    name = models.CharField(max_length=64, default="")
    target = models.ForeignKey(FKTarget, on_delete=models.CASCADE)

    class Meta:
        app_label = "tests"


class UnknownFieldItem(CoreModel):
    """Model with a field type not handled by randomize() — triggers else branch."""

    name = models.CharField(max_length=64, default="")
    ip_address = models.GenericIPAddressField(default="127.0.0.1")

    class Meta:
        app_label = "tests"


class AuditedFileItem(CoreModel):
    """Model with FileField and DateField for audit diff coverage."""

    AUDIT_MODE = True
    AUDIT_SUMMARY = TestAuditSummary
    AUDIT_DETAILS = TestAuditDetails

    name = models.CharField(max_length=64)
    doc = models.FileField(upload_to="test_uploads/", **default_null_blank)
    event_date = models.DateField(**default_null_blank)
    event_datetime = models.DateTimeField(**default_null_blank)
    user = models.ForeignKey(
        get_user_model(), on_delete=models.SET_NULL, **default_null_blank
    )

    class Meta:
        app_label = "tests"


class AuditedNoUserItem(CoreModel):
    """Audited model without a user field — triggers user=None branch."""

    AUDIT_MODE = True
    AUDIT_SUMMARY = TestAuditSummary
    AUDIT_DETAILS = TestAuditDetails

    name = models.CharField(max_length=64)

    class Meta:
        app_label = "tests"


class AuditedNoDetailsItem(CoreModel):
    """Audited model with AUDIT_SUMMARY/DETAILS set to None — triggers early return."""

    AUDIT_MODE = True
    AUDIT_SUMMARY = None
    AUDIT_DETAILS = None

    name = models.CharField(max_length=64)
    user = models.ForeignKey(
        get_user_model(), on_delete=models.SET_NULL, **default_null_blank
    )

    class Meta:
        app_label = "tests"
