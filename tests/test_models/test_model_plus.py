from django.test import TestCase

from qux.models.plus import CoreModelPlus

from ..models import SoftDeleteItem


class TestCoreManagerPlusQueryset(TestCase):
    def setUp(self):
        self.alive = SoftDeleteItem.objects.create(name="alive")
        self.deleted = SoftDeleteItem(name="deleted", is_deleted=True)
        self.deleted.save()

    def test_default_queryset_excludes_deleted(self):
        qs = SoftDeleteItem.objects.all()
        assert self.alive in qs
        assert self.deleted not in qs

    def test_filter_excludes_deleted(self):
        qs = SoftDeleteItem.objects.filter(name="deleted")
        assert qs.count() == 0

    def test_get_raises_for_deleted(self):
        with self.assertRaises(SoftDeleteItem.DoesNotExist):
            SoftDeleteItem.objects.get(pk=self.deleted.pk)

    def test_all_with_deleted(self):
        qs = SoftDeleteItem.objects.all_with_deleted()
        assert self.alive in qs
        assert self.deleted in qs

    def test_get_or_none_excludes_deleted(self):
        result = SoftDeleteItem.objects.get_or_none(pk=self.deleted.pk)
        assert result is None

    def test_get_or_none_returns_alive(self):
        result = SoftDeleteItem.objects.get_or_none(pk=self.alive.pk)
        assert result == self.alive


class TestCoreModelPlusSoftDelete(TestCase):
    def test_delete_sets_is_deleted(self):
        obj = SoftDeleteItem.objects.create(name="todelete")
        obj.delete()
        obj.refresh_from_db()
        assert obj.is_deleted is True

    def test_delete_does_not_remove_from_db(self):
        obj = SoftDeleteItem.objects.create(name="todelete")
        pk = obj.pk
        obj.delete()
        assert SoftDeleteItem.objects.all_with_deleted().filter(pk=pk).exists()

    def test_deleted_hidden_from_default_queryset(self):
        obj = SoftDeleteItem.objects.create(name="todelete")
        obj.delete()
        assert not SoftDeleteItem.objects.filter(pk=obj.pk).exists()


class TestCoreModelPlusRestore(TestCase):
    def test_restore_clears_is_deleted(self):
        obj = SoftDeleteItem.objects.create(name="restoreable")
        obj.delete()
        obj.restore()
        obj.refresh_from_db()
        assert obj.is_deleted is False

    def test_restored_visible_in_default_queryset(self):
        obj = SoftDeleteItem.objects.create(name="restoreable")
        obj.delete()
        obj.restore()
        assert SoftDeleteItem.objects.filter(pk=obj.pk).exists()


class TestCoreManagerPlusGet(TestCase):
    def test_get_returns_alive_item(self):
        obj = SoftDeleteItem.objects.create(name="findme")
        found = SoftDeleteItem.objects.get(pk=obj.pk)
        assert found == obj


class TestSoftDeleteRestoreDeleteCycle(TestCase):
    def test_delete_restore_delete_again(self):
        obj = SoftDeleteItem.objects.create(name="cycle")
        obj.delete()
        obj.refresh_from_db()
        assert obj.is_deleted is True

        obj.restore()
        obj.refresh_from_db()
        assert obj.is_deleted is False
        assert SoftDeleteItem.objects.filter(pk=obj.pk).exists()

        obj.delete()
        obj.refresh_from_db()
        assert obj.is_deleted is True
        assert not SoftDeleteItem.objects.filter(pk=obj.pk).exists()
        assert SoftDeleteItem.objects.all_with_deleted().filter(pk=obj.pk).exists()


class TestCoreModelPlusTimestamps(TestCase):
    def test_dtm_fields_set(self):
        obj = SoftDeleteItem.objects.create(name="timestamps")
        assert obj.dtm_created is not None
        assert obj.dtm_updated is not None


class TestCoreModelPlusMeta(TestCase):
    def test_is_abstract(self):
        assert CoreModelPlus._meta.abstract is True

    def test_has_is_deleted_field(self):
        field_names = [f.name for f in CoreModelPlus._meta.get_fields()]
        assert "is_deleted" in field_names
