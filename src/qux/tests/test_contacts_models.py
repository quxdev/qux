"""Tests for ``qux.contacts.models`` — Company + Contact + the pre_save signal.

Limitation: ``Contact.phones`` and ``.emails`` are reverse relations to
``AbstractContactPhone`` / ``AbstractContactEmail`` subclasses. Those abstract
bases don't create reverse accessors on Contact — only concrete subclasses
defined in downstream apps do. So ``asdict``, ``primaryphone``, ``primaryemail``,
and ``hasphone`` aren't testable from inside qux without forcing a concrete
subclass into the library. The tests here cover everything that does work
without that downstream concrete subclass.
"""

from __future__ import annotations

from django.test import TestCase

from qux.contacts.models import Company, Contact


class TestCompany(TestCase):
    def test_creation_persists(self):
        c = Company.objects.create(name="Acme Co")
        self.assertIsNotNone(c.pk)
        self.assertEqual(c.name, "Acme Co")

    def test_db_table_name(self):
        self.assertEqual(Company._meta.db_table, "qux_contacts_company")


class TestContactDisplayname(TestCase):
    def test_uses_display_name_when_set(self):
        c = Contact.objects.create(
            first_name="Ada",
            last_name="Lovelace",
            display_name="Countess Lovelace",
        )
        self.assertEqual(c.displayname(), "Countess Lovelace")

    def test_falls_back_to_first_plus_last(self):
        c = Contact.objects.create(first_name="Ada", last_name="Lovelace")
        self.assertEqual(c.displayname(), "Ada Lovelace")

    def test_first_only(self):
        c = Contact.objects.create(first_name="Ada")
        self.assertEqual(c.displayname(), "Ada")

    def test_returns_id_when_no_name_fields(self):
        c = Contact.objects.create()
        # Returns the id (an int) when nothing else is set.
        self.assertEqual(c.displayname(), c.id)


class TestContactPreSaveSignal(TestCase):
    """``contact_pre_save`` normalizes ``phone`` to E.164 via ``qux.utils.phone.phone_number``."""

    def test_phone_normalized_on_save(self):
        # Indian mobile in national form -> normalized to +91… E.164 by phone_number().
        c = Contact.objects.create(first_name="A", phone="9876543210")
        c.refresh_from_db()
        self.assertEqual(c.phone, "+919876543210")

    def test_already_normalized_phone_unchanged(self):
        c = Contact.objects.create(first_name="B", phone="+919876543210")
        c.refresh_from_db()
        self.assertEqual(c.phone, "+919876543210")

    def test_empty_phone_left_alone(self):
        c = Contact.objects.create(first_name="C")
        c.refresh_from_db()
        # Phone field is null/blank-allowed; signal short-circuits when falsy.
        self.assertIn(c.phone, ("", None))


class TestContactFields(TestCase):
    def test_db_table_name(self):
        self.assertEqual(Contact._meta.db_table, "qux_contacts_contact")

    def test_company_relation_optional(self):
        # company is nullable; Contact creates without one.
        c = Contact.objects.create(first_name="Solo")
        self.assertIsNone(c.company)

    def test_company_fk_assignment(self):
        company = Company.objects.create(name="WidgetCorp")
        c = Contact.objects.create(first_name="Emp", company=company)
        c.refresh_from_db()
        self.assertEqual(c.company, company)

    def test_email_assignment(self):
        c = Contact.objects.create(first_name="A", email="a@example.com")
        c.refresh_from_db()
        self.assertEqual(c.email, "a@example.com")
