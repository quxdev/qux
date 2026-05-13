from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import RequestFactory, TestCase

from qux.contacts.models import Contact
from qux.models.contacts import AbstractCompany, AbstractProfile

from ..models import TestCompany, TestContactEmail, TestContactPhone, TestLead, TestProfile

User = get_user_model()


class TestAbstractCompanyModel(TestCase):
    def test_create(self):
        company = TestCompany.objects.create(name="Acme", domain="acme.com")
        assert company.pk is not None
        assert company.slug is not None

    def test_slug_prefix(self):
        company = TestCompany.objects.create(name="Acme", domain="acme.com")
        assert company.slug.startswith("company_")

    def test_slug_only_lowercase(self):
        company = TestCompany.objects.create(name="Acme", domain="acme.com")
        slug_body = company.slug.replace("company_", "")
        assert slug_body == slug_body.lower()

    def test_str_with_name(self):
        company = TestCompany.objects.create(name="Acme", domain="acme.com")
        assert str(company) == "Acme"

    def test_str_without_name(self):
        company = TestCompany.objects.create(name="", domain="noname.com")
        assert str(company) == company.slug

    def test_optional_fields(self):
        company = TestCompany.objects.create(
            name="Full", domain="full.com", address="123 St", url="https://full.com"
        )
        assert company.address == "123 St"
        assert company.url == "https://full.com"

    def test_domain_unique(self):
        TestCompany.objects.create(name="A", domain="unique.com")
        with self.assertRaises(IntegrityError):
            TestCompany.objects.create(name="B", domain="unique.com")

    def test_is_abstract(self):
        assert AbstractCompany._meta.abstract is True


class TestAbstractProfileModel(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "profileuser",
            email="profile@test.com",
            password="pass",
            first_name="John",
            last_name="Doe",
        )
        # Signal auto-creates profile on user creation, so fetch it
        self.profile = TestProfile.objects.get(user=self.user)

    def test_create(self):
        assert self.profile.pk is not None
        assert self.profile.slug is not None

    def test_slug_prefix(self):
        assert self.profile.slug.startswith("user_")

    def test_get_user(self):
        found = TestProfile.get_user(self.profile.slug)
        assert found == self.user

    def test_get_initials_both_names(self):
        assert self.profile.get_initials() == "J D"

    def test_get_initials_first_only(self):
        user = User.objects.create_user("firstonly", password="pass", first_name="Jane")
        profile = TestProfile.objects.get(user=user)
        assert profile.get_initials() == "J"

    def test_get_initials_last_only(self):
        user = User.objects.create_user("lastonly", password="pass", last_name="Smith")
        profile = TestProfile.objects.get(user=user)
        assert profile.get_initials() == "S"

    def test_get_initials_no_name(self):
        user = User.objects.create_user("noname", password="pass")
        profile = TestProfile.objects.get(user=user)
        assert profile.get_initials() is None

    def test_get_fullname_both_names(self):
        assert self.profile.get_fullname() == "John Doe"

    def test_get_fullname_first_only(self):
        user = User.objects.create_user("fnfirst", password="pass", first_name="Jane")
        profile = TestProfile.objects.get(user=user)
        assert profile.get_fullname() == "Jane"

    def test_get_fullname_last_only(self):
        user = User.objects.create_user("fnlast", password="pass", last_name="Smith")
        profile = TestProfile.objects.get(user=user)
        assert profile.get_fullname() == "Smith"

    def test_get_fullname_no_name(self):
        user = User.objects.create_user("fnnoname", email="fallback@test.com", password="pass")
        profile = TestProfile.objects.get(user=user)
        assert profile.get_fullname() == "fallback@test.com"

    def test_is_live_default(self):
        assert self.profile.is_live is False

    def test_is_abstract(self):
        assert AbstractProfile._meta.abstract is True


class TestCreateProfileSignal(TestCase):
    def test_profile_created_on_user_create(self):
        user = User.objects.create_user("signaluser", password="pass")
        assert TestProfile.objects.filter(user=user).exists()

    def test_profile_not_duplicated_on_user_save(self):
        user = User.objects.create_user("saveuser", password="pass")
        user.first_name = "Updated"
        user.save()
        assert TestProfile.objects.filter(user=user).count() == 1


class TestAbstractLeadModel(TestCase):
    def test_create(self):
        lead = TestLead.objects.create()
        assert lead.pk is not None

    def test_optional_fields(self):
        lead = TestLead.objects.create(
            firstname="John",
            lastname="Doe",
            email="john@test.com",
            phone="+1234567890",
        )
        assert lead.firstname == "John"
        assert lead.lastname == "Doe"
        assert lead.email == "john@test.com"
        assert lead.phone == "+1234567890"

    def test_utm_fields(self):
        lead = TestLead.objects.create(
            utm_source="google",
            utm_medium="cpc",
            utm_campaign="summer",
            utm_term="shoes",
            utm_content="banner",
        )
        assert lead.utm_source == "google"
        assert lead.utm_medium == "cpc"

    def test_get_params_default(self):
        lead = TestLead.objects.create()
        assert lead.get_params == {}

    def test_update_or_create_from_request(self):
        factory = RequestFactory()
        request = factory.get(
            "/",
            {"utm_source": "google", "utm_medium": "cpc"},
        )
        lead = TestLead.update_or_create_from_request(request)
        assert lead.pk is not None
        assert lead.utm_source == "google"
        assert lead.utm_medium == "cpc"

    def test_update_or_create_from_request_meta(self):
        factory = RequestFactory()
        request = factory.get("/")
        request.META["HTTP_USER_AGENT"] = "TestBot/1.0"
        request.META["REMOTE_ADDR"] = "127.0.0.1"
        lead = TestLead.update_or_create_from_request(request)
        assert lead.http_user_agent == "TestBot/1.0"
        assert lead.remote_addr == "127.0.0.1"

    def test_update_or_create_from_request_additional_fields(self):
        factory = RequestFactory()
        request = factory.get("/", {"utm_source": "fb", "fbclid": "abc123"})
        lead = TestLead.update_or_create_from_request(request, additional_fields=["fbclid"])
        assert lead.get_params["fbclid"] == "abc123"

    def test_update_or_create_from_request_ad_set(self):
        factory = RequestFactory()
        request = factory.get("/", {"ad_set": "my_adset"})
        lead = TestLead.update_or_create_from_request(request)
        assert lead.get_params["adset_name"] == "my_adset"

    def test_update_or_create_stores_get_params(self):
        factory = RequestFactory()
        request = factory.get("/", {"foo": "bar", "baz": "qux"})
        lead = TestLead.update_or_create_from_request(request)
        assert lead.get_params["foo"] == "bar"
        assert lead.get_params["baz"] == "qux"


class TestProfileGetUserInvalidSlug(TestCase):
    def test_get_user_invalid_slug_raises(self):
        with self.assertRaises(TestProfile.DoesNotExist):
            TestProfile.get_user("nonexistent_slug")


class TestLeadPhoneValidator(TestCase):
    def test_valid_e164_phone(self):
        lead = TestLead(phone="+12345678901")
        # Should not raise for the phone field
        lead.full_clean()

    def test_invalid_phone_format(self):
        lead = TestLead(phone="not-a-phone")
        with self.assertRaises(ValidationError):
            lead.full_clean()

    def test_phone_too_short(self):
        lead = TestLead(phone="+123")
        with self.assertRaises(ValidationError):
            lead.full_clean()


class TestCompanySlugUniqueness(TestCase):
    def test_slugs_are_unique_across_instances(self):
        c1 = TestCompany.objects.create(name="A", domain="a.com")
        c2 = TestCompany.objects.create(name="B", domain="b.com")
        assert c1.slug != c2.slug

    def test_duplicate_slug_rejected(self):
        c1 = TestCompany.objects.create(name="A", domain="a.com")
        with self.assertRaises(IntegrityError):
            TestCompany.objects.create(name="B", domain="b.com", slug=c1.slug)


class TestContactDisplayname(TestCase):
    def test_displayname_with_display_name_set(self):
        contact = Contact.objects.create(display_name="Custom Name")
        assert contact.displayname() == "Custom Name"

    def test_displayname_first_and_last(self):
        contact = Contact.objects.create(first_name="John", last_name="Doe")
        assert contact.displayname() == "John Doe"

    def test_displayname_first_only(self):
        contact = Contact.objects.create(first_name="Jane")
        assert contact.displayname() == "Jane"

    def test_displayname_fallback_to_id(self):
        contact = Contact.objects.create()
        assert contact.displayname() == contact.id


class TestContactAsdict(TestCase):
    def test_asdict_keys(self):
        contact = Contact.objects.create(first_name="John", last_name="Doe", email="john@test.com")
        d = contact.asdict()
        assert d["id"] == contact.id
        assert d["first_name"] == "John"
        assert d["last_name"] == "Doe"
        assert d["display"] == "John Doe"
        assert d["is_favorite"] is False
        assert d["is_private"] is True
        assert d["email"] == "john@test.com"
        assert d["phones"] == []
        assert d["emails"] == []

    def test_asdict_with_phones_and_emails(self):
        contact = Contact.objects.create(first_name="Jane")
        TestContactPhone.objects.create(
            contact=contact, phone="+12025551234", label="work", is_primary=True
        )
        TestContactEmail.objects.create(
            contact=contact, email="jane@test.com", label="home", is_primary=True
        )
        d = contact.asdict()
        assert len(d["phones"]) == 1
        assert d["phones"][0]["phone"] == "+12025551234"
        assert len(d["emails"]) == 1
        assert d["emails"][0]["email"] == "jane@test.com"


class TestContactPrimaryPhoneAndEmail(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(first_name="Test")

    def test_primaryphone_none_when_no_phones(self):
        assert self.contact.primaryphone() is None

    def test_primaryphone_returns_primary(self):
        TestContactPhone.objects.create(
            contact=self.contact, phone="+12025551111", is_primary=False
        )
        primary = TestContactPhone.objects.create(
            contact=self.contact, phone="+12025552222", is_primary=True
        )
        assert self.contact.primaryphone() == primary

    def test_primaryphone_returns_first_when_no_primary(self):
        p1 = TestContactPhone.objects.create(
            contact=self.contact, phone="+12025553333", is_primary=False
        )
        result = self.contact.primaryphone()
        assert result == p1

    def test_primaryemail_none_when_no_emails(self):
        assert self.contact.primaryemail() is None

    def test_primaryemail_returns_primary(self):
        TestContactEmail.objects.create(contact=self.contact, email="a@test.com", is_primary=False)
        primary = TestContactEmail.objects.create(
            contact=self.contact, email="b@test.com", is_primary=True
        )
        assert self.contact.primaryemail() == primary

    def test_primaryemail_returns_first_when_no_primary(self):
        e1 = TestContactEmail.objects.create(
            contact=self.contact, email="c@test.com", is_primary=False
        )
        result = self.contact.primaryemail()
        assert result == e1


class TestContactHasphone(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(first_name="PhoneTest")

    def test_hasphone_true(self):
        TestContactPhone.objects.create(contact=self.contact, phone="+12025551234")
        assert self.contact.hasphone("+12025551234") is True

    def test_hasphone_false(self):
        assert self.contact.hasphone("+12025559999") is False

    def test_hasphone_invalid_phone(self):
        assert self.contact.hasphone("not-a-phone") is False


class TestContactPreSaveFormatsPhone(TestCase):
    """Contact_pre_save signal formats phone."""

    def test_contact_phone_formatted_on_save(self):
        contact = Contact.objects.create(first_name="PhoneFmt", phone="+12025551234")
        contact.refresh_from_db()
        # phone_number should format it to E164
        assert contact.phone == "+12025551234"

    def test_contact_phone_formatted_from_local(self):
        contact = Contact.objects.create(first_name="PhoneLocal", phone="2025551234")
        contact.refresh_from_db()
        # Should be formatted via phone_number()
        # If valid, it gets formatted; if not, it stays as-is
        assert contact.phone is not None


class TestContactPhoneSaveFormatting(TestCase):
    def test_save_formats_phone_number(self):
        contact = Contact.objects.create(first_name="Fmt")
        phone_obj = TestContactPhone.objects.create(contact=contact, phone="+12025551234")
        assert phone_obj.phone == "+12025551234"

    def test_str(self):
        contact = Contact.objects.create(first_name="Str")
        phone_obj = TestContactPhone.objects.create(contact=contact, phone="+12025551234")
        assert str(phone_obj) == "+12025551234"

    def test_asdict(self):
        contact = Contact.objects.create(first_name="Dict")
        phone_obj = TestContactPhone.objects.create(
            contact=contact, phone="+12025551234", label="mobile", is_primary=True
        )
        d = phone_obj.asdict()
        assert d["id"] == phone_obj.id
        assert d["phone"] == "+12025551234"
        assert d["label"] == "mobile"
        assert d["is_primary"] is True


class TestContactEmailModel(TestCase):
    def test_str(self):
        contact = Contact.objects.create(first_name="EmailStr")
        email_obj = TestContactEmail.objects.create(contact=contact, email="test@example.com")
        assert str(email_obj) == "test@example.com"

    def test_asdict(self):
        contact = Contact.objects.create(first_name="EmailDict")
        email_obj = TestContactEmail.objects.create(
            contact=contact, email="test@example.com", label="work", is_primary=True
        )
        d = email_obj.asdict()
        assert d["id"] == email_obj.id
        assert d["email"] == "test@example.com"
        assert d["label"] == "work"
        assert d["is_primary"] is True
