import inspect
from unittest.mock import MagicMock, patch

from django.contrib import admin
from django.test import SimpleTestCase

from qux.admin.base import QuxModelAdmin
from qux.admin.plus import QuxPlusModelAdmin

from .models import SlugItem, SoftDeleteItem


class SlugItemAdmin(QuxModelAdmin):
    pass


class SoftDeleteItemAdmin(QuxPlusModelAdmin):
    pass


# Register on a separate AdminSite to avoid conflicts
test_site = admin.AdminSite(name="test_admin")
test_site.register(SlugItem, SlugItemAdmin)
test_site.register(SoftDeleteItem, SoftDeleteItemAdmin)


def _mock_request():
    return MagicMock()


class TestQuxModelAdminGetFields(SimpleTestCase):
    def setUp(self):
        self.request = _mock_request()
        self.ma = SlugItemAdmin(SlugItem, test_site)

    def test_get_fields_excludes_dtm_created_and_dtm_updated(self):
        fields = self.ma.get_fields(self.request)
        assert "dtm_created" not in fields
        assert "dtm_updated" not in fields

    def test_get_fields_includes_model_fields(self):
        fields = self.ma.get_fields(self.request)
        assert "name" in fields
        assert "slug" in fields


class TestQuxModelAdminGetReadonlyFields(SimpleTestCase):
    def setUp(self):
        self.request = _mock_request()
        self.ma = SlugItemAdmin(SlugItem, test_site)

    def test_get_readonly_fields_returns_id_and_slug(self):
        fields = self.ma.get_readonly_fields(self.request)
        assert "id" in fields
        assert "slug" in fields

    def test_get_readonly_fields_excludes_non_readonly(self):
        fields = self.ma.get_readonly_fields(self.request)
        assert "name" not in fields


class TestQuxModelAdminGetListDisplay(SimpleTestCase):
    def setUp(self):
        self.request = _mock_request()
        self.ma = SlugItemAdmin(SlugItem, test_site)

    def test_get_list_display_excludes_dtm_fields(self):
        fields = self.ma.get_list_display(self.request)
        assert "dtm_created" not in fields
        assert "dtm_updated" not in fields

    def test_get_list_display_includes_regular_fields(self):
        fields = self.ma.get_list_display(self.request)
        assert "name" in fields


class TestQuxPlusModelAdminGetQueryset(SimpleTestCase):
    def test_has_is_deleted_in_list_filter(self):
        ma = SoftDeleteItemAdmin(SoftDeleteItem, test_site)
        assert "is_deleted" in ma.list_filter

    def test_get_queryset_source_uses_all_with_deleted(self):
        """Verify get_queryset is overridden to call all_with_deleted."""
        source = inspect.getsource(QuxPlusModelAdmin.get_queryset)
        assert "all_with_deleted" in source

    def test_get_queryset_calls_all_with_deleted(self):
        """Actually call get_queryset to cover lines 14-19 in plus.py."""
        ma = SoftDeleteItemAdmin(SoftDeleteItem, test_site)
        request = _mock_request()

        mock_qs = MagicMock()
        mock_manager = MagicMock()
        mock_manager.all_with_deleted.return_value = mock_qs
        mock_qs.order_by.return_value = mock_qs

        # _default_manager is a metaclass property, so patch on the model's class
        with patch.object(type(SoftDeleteItem), "_default_manager", new=mock_manager):
            _result = ma.get_queryset(request)
            mock_manager.all_with_deleted.assert_called_once()

    def test_get_queryset_with_ordering(self):
        """Cover the ordering branch (lines 16-18) when ordering is set."""
        ma = SoftDeleteItemAdmin(SoftDeleteItem, test_site)
        ma.ordering = ("-name",)
        request = _mock_request()

        mock_qs = MagicMock()
        mock_manager = MagicMock()
        mock_manager.all_with_deleted.return_value = mock_qs
        mock_qs.order_by.return_value = mock_qs

        with patch.object(type(SoftDeleteItem), "_default_manager", new=mock_manager):
            _result = ma.get_queryset(request)
            mock_qs.order_by.assert_called_once_with("-name")

    def test_get_queryset_without_ordering(self):
        """Cover the branch when ordering is empty/None (lines 16, 19)."""
        ma = SoftDeleteItemAdmin(SoftDeleteItem, test_site)
        ma.ordering = None
        request = _mock_request()

        mock_qs = MagicMock()
        mock_manager = MagicMock()
        mock_manager.all_with_deleted.return_value = mock_qs

        with patch.object(type(SoftDeleteItem), "_default_manager", new=mock_manager):
            _result = ma.get_queryset(request)
            # ordering is () so order_by should NOT be called
            mock_qs.order_by.assert_not_called()
            assert _result == mock_qs
