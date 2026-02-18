from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from qux.models.audit import CoreModelAuditSummary, CoreModelAuditDetails

from ..models import TestAuditSummary, TestAuditDetails, AuditedItem, BareAuditSummary

User = get_user_model()


class TestAuditSummaryModel(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("auditor", password="pass")
        self.item = AuditedItem.objects.create(name="item", user=self.user)

    def test_create_summary(self):
        ct = ContentType.objects.get_for_model(AuditedItem)
        summary = TestAuditSummary.objects.create(
            user=self.user,
            content_type=ct,
            object_id=self.item.pk,
        )
        assert summary.pk is not None
        assert summary.slug is not None
        assert summary.user == self.user
        assert summary.content_object == self.item

    def test_slug_auto_generated(self):
        ct = ContentType.objects.get_for_model(AuditedItem)
        summary = TestAuditSummary.objects.create(
            user=self.user,
            content_type=ct,
            object_id=self.item.pk,
        )
        assert summary.slug != ""
        assert summary.slug is not None

    def test_user_nullable(self):
        ct = ContentType.objects.get_for_model(AuditedItem)
        summary = TestAuditSummary.objects.create(
            user=None,
            content_type=ct,
            object_id=self.item.pk,
        )
        assert summary.user is None


class TestAuditSummaryGetDetails(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("detailuser", password="pass")
        self.item = AuditedItem.objects.create(name="item", user=self.user)
        ct = ContentType.objects.get_for_model(AuditedItem)
        self.summary = TestAuditSummary.objects.create(
            user=self.user,
            content_type=ct,
            object_id=self.item.pk,
        )

    def test_get_details_returns_related(self):
        TestAuditDetails.objects.create(
            audit_summary=self.summary,
            field_name="name",
            old_value="old",
            new_value="new",
        )
        details = self.summary.get_details()
        assert details.count() == 1
        assert details.first().field_name == "name"

    def test_get_details_empty(self):
        details = self.summary.get_details()
        assert details.count() == 0


class TestAuditDetailsModel(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("detailcreator", password="pass")
        self.item = AuditedItem.objects.create(name="item", user=self.user)
        ct = ContentType.objects.get_for_model(AuditedItem)
        self.summary = TestAuditSummary.objects.create(
            user=self.user,
            content_type=ct,
            object_id=self.item.pk,
        )

    def test_create_detail(self):
        detail = TestAuditDetails.objects.create(
            audit_summary=self.summary,
            field_name="name",
            old_value="old",
            new_value="new",
        )
        assert detail.pk is not None
        assert detail.field_name == "name"
        assert detail.old_value == "old"
        assert detail.new_value == "new"

    def test_null_values(self):
        detail = TestAuditDetails.objects.create(
            audit_summary=self.summary,
            field_name="name",
            old_value=None,
            new_value=None,
        )
        assert detail.old_value is None
        assert detail.new_value is None

    def test_json_values(self):
        detail = TestAuditDetails.objects.create(
            audit_summary=self.summary,
            field_name="config",
            old_value={"key": "old"},
            new_value={"key": "new"},
        )
        assert detail.old_value == {"key": "old"}
        assert detail.new_value == {"key": "new"}


class TestAuditAbstractMeta(TestCase):
    def test_summary_is_abstract(self):
        assert CoreModelAuditSummary._meta.abstract is True

    def test_details_is_abstract(self):
        assert CoreModelAuditDetails._meta.abstract is True


class TestAuditIntegration(TestCase):
    """Tests the full audit trail via post_save signal."""

    def test_change_creates_audit_trail(self):
        user = User.objects.create_user("integration", password="pass")
        obj = AuditedItem.objects.create(name="v1", user=user)
        obj = AuditedItem.objects.get(pk=obj.pk)
        obj.name = "v2"
        obj.save()

        summaries = TestAuditSummary.objects.all()
        assert summaries.exists()

        detail = TestAuditDetails.objects.filter(field_name="name").last()
        assert detail.old_value == "v1"
        assert detail.new_value == "v2"

    def test_multiple_changes_create_multiple_details(self):
        user = User.objects.create_user("multi", password="pass")
        obj = AuditedItem.objects.create(name="original", user=user)
        obj = AuditedItem.objects.get(pk=obj.pk)
        obj.name = "changed"
        obj.save()

        obj = AuditedItem.objects.get(pk=obj.pk)
        obj.name = "changed_again"
        obj.save()

        ct = ContentType.objects.get_for_model(AuditedItem)
        summaries = TestAuditSummary.objects.filter(content_type=ct, object_id=obj.pk)
        assert summaries.count() == 2


class TestGetDetailsNotImplemented(TestCase):
    def test_raises_not_implemented_without_details_relation(self):
        user = User.objects.create_user("bare", password="pass")
        item = AuditedItem.objects.create(name="item", user=user)
        ct = ContentType.objects.get_for_model(AuditedItem)
        summary = BareAuditSummary.objects.create(
            user=user,
            content_type=ct,
            object_id=item.pk,
        )
        with self.assertRaises(NotImplementedError):
            summary.get_details()


class TestMultipleFieldChanges(TestCase):
    def test_multiple_fields_changed_creates_multiple_details(self):
        user = User.objects.create_user("multifield", password="pass")
        user2 = User.objects.create_user("multifield2", password="pass")
        obj = AuditedItem.objects.create(name="orig", user=user)
        obj = AuditedItem.objects.get(pk=obj.pk)
        obj.name = "changed"
        obj.user = user2
        obj.save()

        summary = TestAuditSummary.objects.filter(object_id=obj.pk).last()
        details = TestAuditDetails.objects.filter(audit_summary=summary)
        field_names = set(details.values_list("field_name", flat=True))
        assert "name" in field_names
        assert "user" in field_names
        assert details.count() >= 2


class TestContentObjectGenericFK(TestCase):
    def test_content_object_resolves(self):
        user = User.objects.create_user("gfk", password="pass")
        item = AuditedItem.objects.create(name="gfkitem", user=user)
        ct = ContentType.objects.get_for_model(AuditedItem)
        summary = TestAuditSummary.objects.create(
            user=user,
            content_type=ct,
            object_id=item.pk,
        )
        assert summary.content_object == item
        assert summary.content_object.name == "gfkitem"
