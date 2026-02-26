import json
import os
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from qux.auth.models.models import Preference, Service

User = get_user_model()


class TestServiceStr(TestCase):
    def test_str(self):
        service = Service(name="TestService", slug="service-001")
        assert str(service) == "TestService"


class TestServiceGetPreferences(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass1234")
        self.service = Service.objects.create(name="MySvc", slug="service-001")
        Preference.objects.create(
            user=self.user,
            service=self.service,
            name="page_size",
            value="25",
            type="int",
            slug="pref-000001",
        )
        Preference.objects.create(
            user=self.user,
            service=self.service,
            name="debug",
            value="true",
            type="bool",
            slug="pref-000002",
        )
        Preference.objects.create(
            user=self.user,
            service=self.service,
            name="label",
            value="hello",
            type="str",
            slug="pref-000003",
        )

    def test_returns_list(self):
        prefs = self.service.get_preferences()
        assert isinstance(prefs, list)
        assert len(prefs) == 3
        for p in prefs:
            assert isinstance(p, dict)
            assert "name" in p
            assert "value" in p

    def test_casts_values(self):
        prefs = self.service.get_preferences()
        by_name = {p["name"]: p for p in prefs}
        assert by_name["page_size"]["value"] == 25
        assert by_name["debug"]["value"] is True
        assert by_name["label"]["value"] == "hello"

    def test_include_filter(self):
        prefs = self.service.get_preferences(include=["page_size"])
        assert len(prefs) == 1
        assert prefs[0]["name"] == "page_size"

    def test_exclude_filter(self):
        prefs = self.service.get_preferences(exclude=["label"])
        names = [p["name"] for p in prefs]
        assert "label" not in names
        assert len(prefs) == 2


class TestPreferenceStr(TestCase):
    def test_str(self):
        service = Service(name="MySvc", slug="service-001")
        pref = Preference(service=service, name="theme", slug="pref-000001")
        assert str(pref) == "MySvc.theme"


class TestPreferenceGetPreferences(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass1234")
        self.service = Service.objects.create(name="MySvc", slug="service-001")
        Preference.objects.create(
            user=self.user,
            service=self.service,
            name="pref1",
            value="val1",
            slug="pref-000001",
        )

    def test_returns_queryset(self):
        qs = Preference.get_preferences(self.user, self.service)
        assert qs.count() == 1
        assert qs.first().name == "pref1"


class TestPreferenceLoaddata(TestCase):
    def test_nonexistent_file(self):
        with patch.dict(os.environ, {"QUX_FIXTURES_PREFERENCE": "/nonexistent.json"}):
            # Should return without error
            result = Preference.loaddata()
            assert result is None
        assert Preference.objects.count() == 0

    def test_valid_fixture(self):
        user = User.objects.create_user(username="fixtureuser", password="pass1234")
        service = Service.objects.create(name="FixSvc", slug="service-002")

        fixture_data = [
            {
                "user": user.id,
                "service": service.id,
                "name": "loaded_pref",
                "value": "loaded_val",
                "type": "str",
                "slug": "pref-100001",
            }
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(fixture_data, f)
            fixture_path = f.name

        try:
            with patch.dict(os.environ, {"QUX_FIXTURES_PREFERENCE": fixture_path}):
                Preference.loaddata()
            pref = Preference.objects.filter(name="loaded_pref").first()
            assert pref is not None
            # Verify line 98-99: item["service"] was resolved to a Service instance
            assert pref.service == service
        finally:
            os.unlink(fixture_path)

    def test_fixture_with_nonexistent_user(self):
        """Cover lines 93-94: User.DoesNotExist triggers continue."""
        service = Service.objects.create(name="FixSvc2", slug="service-003")

        fixture_data = [
            {
                "user": 999999,
                "service": service.id,
                "name": "orphan_pref",
                "value": "val",
                "type": "str",
                "slug": "pref-200001",
            }
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(fixture_data, f)
            fixture_path = f.name

        try:
            with patch.dict(os.environ, {"QUX_FIXTURES_PREFERENCE": fixture_path}):
                Preference.loaddata()
            assert not Preference.objects.filter(name="orphan_pref").exists()
        finally:
            os.unlink(fixture_path)

    def test_fixture_with_nonexistent_service(self):
        """Cover line 97-98: service is None triggers continue."""
        user = User.objects.create_user(username="fixtureuser2", password="pass1234")

        fixture_data = [
            {
                "user": user.id,
                "service": 999999,
                "name": "no_svc_pref",
                "value": "val",
                "type": "str",
                "slug": "pref-300001",
            }
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(fixture_data, f)
            fixture_path = f.name

        try:
            with patch.dict(os.environ, {"QUX_FIXTURES_PREFERENCE": fixture_path}):
                Preference.loaddata()
            assert not Preference.objects.filter(name="no_svc_pref").exists()
        finally:
            os.unlink(fixture_path)
