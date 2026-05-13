import datetime
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
from django.test import TestCase, override_settings

from qux.models.base import CoreModel, QuxModel, default_null_blank, qux_model_to_dict

from ..models import (
    AuditedFileItem,
    AuditedItem,
    AuditedNoDetailsItem,
    AuditedNoUserItem,
    FKSource,
    FKTarget,
    M2MItem,
    M2MRelated,
    RandomItem,
    SimpleItem,
    SlugItem,
    TagItem,
    TestAuditDetails,
    TestAuditSummary,
    UnknownFieldItem,
)

User = get_user_model()


class TestDefaultNullBlank(TestCase):
    def test_values(self):
        assert default_null_blank == {"default": None, "null": True, "blank": True}


class TestCoreManager(TestCase):
    def test_get_or_none_exists(self):
        obj = SimpleItem.objects.create(name="exists")
        result = SimpleItem.objects.get_or_none(pk=obj.pk)
        assert result == obj

    def test_get_or_none_missing(self):
        result = SimpleItem.objects.get_or_none(pk=99999)
        assert result is None


class TestCoreModelTimestamps(TestCase):
    def test_dtm_created_set_on_create(self):
        obj = SimpleItem.objects.create(name="ts")
        assert obj.dtm_created is not None

    def test_dtm_updated_set_on_create(self):
        obj = SimpleItem.objects.create(name="ts")
        assert obj.dtm_updated is not None

    def test_dtm_updated_changes_on_save(self):
        obj = SimpleItem.objects.create(name="ts")
        old_updated = obj.dtm_updated
        obj.name = "ts2"
        obj.save()
        obj.refresh_from_db()
        assert obj.dtm_updated >= old_updated


class TestGetSlug(TestCase):
    def test_default_length(self):
        obj = SimpleItem(name="test")
        slug = obj.get_slug()
        assert len(slug) == 8

    def test_custom_length(self):
        obj = SimpleItem(name="test")
        slug = obj.get_slug(slug_length=12)
        assert len(slug) == 12

    def test_first_char_is_alpha(self):
        obj = SimpleItem(name="test")
        for _ in range(20):
            slug = obj.get_slug()
            assert slug[0].isalpha()

    def test_respects_allowed_chars(self):
        obj = SlugItem(name="test")
        for _ in range(20):
            slug = obj.get_slug()
            assert all(c in "abcdefghijklmnopqrstuvwxyz" for c in slug)


class TestSlugAutoGeneration(TestCase):
    def test_slug_generated_on_save(self):
        obj = SlugItem.objects.create(name="test")
        assert obj.slug is not None
        assert obj.slug.startswith("item_")

    def test_slug_unique_across_saves(self):
        obj1 = SlugItem.objects.create(name="a")
        obj2 = SlugItem.objects.create(name="b")
        assert obj1.slug != obj2.slug

    def test_existing_slug_preserved(self):
        obj = SlugItem(name="test", slug="item_custom")
        obj.save()
        assert obj.slug == "item_custom"


class TestInitdata(TestCase):
    def test_initdata_runs_without_error(self):
        SimpleItem.initdata()


class TestToDict(TestCase):
    def test_default_excludes(self):
        obj = SimpleItem.objects.create(name="dicttest")
        d = obj.to_dict()
        assert "name" in d
        assert "id" not in d
        assert "dtm_created" not in d
        assert "dtm_updated" not in d

    def test_custom_fields(self):
        obj = SimpleItem.objects.create(name="dicttest")
        d = obj.to_dict(fields=["name"])
        assert list(d.keys()) == ["name"]

    def test_custom_exclude(self):
        obj = SimpleItem.objects.create(name="dicttest")
        d = obj.to_dict(exclude=["name"])
        assert "name" not in d
        assert "id" in d

    def test_exclude_none(self):
        obj = SimpleItem.objects.create(name="dicttest")
        d = obj.to_dict(exclude_none=True)
        assert "id" in d
        assert "dtm_created" in d

    def test_verbose_name(self):
        obj = SimpleItem.objects.create(name="dicttest")
        d = obj.to_dict(verbose_name=True)
        assert "DTM Created" not in d  # excluded by default
        assert "name" in d


class TestGetDict(TestCase):
    def test_returns_dict(self):
        obj = SimpleItem.objects.create(name="getdict")
        d = SimpleItem.get_dict(obj.pk)
        assert d["name"] == "getdict"

    def test_raises_on_missing(self):
        with self.assertRaises(SimpleItem.DoesNotExist):
            SimpleItem.get_dict(99999)


class TestQuxModelToDict(TestCase):
    def test_m2m_field_unsaved(self):
        obj = M2MItem(name="unsaved")
        d = qux_model_to_dict(obj, exclude=[])
        assert d["related"] == []

    def test_m2m_field_saved(self):
        rel1 = M2MRelated.objects.create(name="r1")
        rel2 = M2MRelated.objects.create(name="r2")
        obj = M2MItem.objects.create(name="m2m")
        obj.related.set([rel1, rel2])
        d = qux_model_to_dict(obj, exclude=[])
        assert set(d["related"]) == {rel1, rel2}


class TestRandomize(TestCase):
    def test_randomize_sets_char_field(self):
        obj = RandomItem()
        obj.randomize()
        assert obj.char_field is not None
        assert len(obj.char_field) == 32

    def test_randomize_sets_bool_field(self):
        obj = RandomItem()
        obj.randomize()
        assert isinstance(obj.bool_field, bool)


class TestTagMethods(TestCase):
    def test_settag(self):
        obj = TagItem.objects.create(name="tagged", tags="")
        result = obj.settag("foo")
        assert "foo" in result
        obj.refresh_from_db()
        assert "foo" in obj.tags

    def test_settag_no_tags_field(self):
        obj = SimpleItem.objects.create(name="notags")
        result = obj.settag("foo")
        assert result is None

    def test_deltag(self):
        obj = TagItem.objects.create(name="tagged", tags="bar,foo")
        result = obj.deltag("foo")
        assert result is True
        obj.refresh_from_db()
        assert "foo" not in obj.tags

    def test_deltag_missing(self):
        obj = TagItem.objects.create(name="tagged", tags="bar")
        result = obj.deltag("nonexistent")
        assert result is True

    def test_deltag_no_tags_field(self):
        obj = SimpleItem.objects.create(name="notags")
        result = obj.deltag("foo")
        assert result is False

    def test_hastag_true(self):
        obj = TagItem.objects.create(name="tagged", tags="alpha,beta")
        assert obj.hastag("alpha") is True

    def test_hastag_false(self):
        obj = TagItem.objects.create(name="tagged", tags="alpha,beta")
        assert obj.hastag("gamma") is False

    def test_hastag_no_tags_field(self):
        obj = SimpleItem.objects.create(name="notags")
        assert obj.hastag("foo") is False

    def test_gettags(self):
        obj = TagItem.objects.create(name="tagged", tags="alpha,beta")
        result = obj.gettags()
        assert set(result) == {"alpha", "beta"}

    def test_gettags_empty(self):
        obj = TagItem.objects.create(name="tagged", tags="")
        result = obj.gettags()
        assert result == []

    def test_gettags_no_tags_field(self):
        obj = SimpleItem.objects.create(name="notags")
        result = obj.gettags()
        assert result is None

    def test_gettaglist(self):
        TagItem.objects.create(name="a", tags="foo,bar")
        TagItem.objects.create(name="b", tags="bar,baz")
        result = TagItem.gettaglist()
        assert set(result) == {"foo", "bar", "baz"}

    def test_gettaglist_removes_empty(self):
        """Gettaglist removes empty string after join/split."""
        TagItem.objects.create(name="c", tags=",alpha")
        result = TagItem.gettaglist()
        assert "" not in result

    def test_gettaglist_no_tags_field(self):
        result = SimpleItem.gettaglist()
        assert result is None


class TestAllObjectsManager(TestCase):
    def test_all_objects_returns_all_instances(self):
        obj1 = SimpleItem.objects.create(name="a1")
        obj2 = SimpleItem.objects.create(name="a2")
        qs = SimpleItem.all_objects.all()
        assert obj1 in qs
        assert obj2 in qs


class TestRandomizeAllFields(TestCase):
    def test_randomize_sets_text_field(self):
        obj = RandomItem()
        obj.randomize()
        assert obj.text_field_required is not None
        assert len(obj.text_field_required) > 0

    def test_randomize_sets_int_field(self):
        obj = RandomItem()
        obj.randomize()
        assert isinstance(obj.int_field_required, int)
        assert 0 <= obj.int_field_required <= 100

    def test_randomize_sets_email_field(self):
        # EmailField.get_internal_type() returns "CharField", so randomize()
        # treats it as a CharField and fills it with a random string
        obj = RandomItem()
        obj.randomize()
        assert obj.email_field_required is not None
        assert len(obj.email_field_required) > 0

    def test_randomize_sets_url_field(self):
        # URLField.get_internal_type() returns "CharField", so randomize()
        # treats it as a CharField and fills it with a random string
        obj = RandomItem()
        obj.randomize()
        assert obj.url_field_required is not None
        assert len(obj.url_field_required) > 0


class TestSettagDuplicateAndSorted(TestCase):
    def test_settag_duplicate_not_added_twice(self):
        obj = TagItem.objects.create(name="dup", tags="alpha")
        obj.settag("alpha")
        obj.refresh_from_db()
        tags = [t.strip() for t in obj.tags.split(",") if t.strip()]
        assert tags.count("alpha") == 1  # settag should not add duplicates

    def test_settag_tags_are_sorted(self):
        obj = TagItem.objects.create(name="sorted", tags="")
        obj.settag("cherry")
        obj.settag("apple")
        obj.settag("banana")
        obj.refresh_from_db()
        tags = [t.strip() for t in obj.tags.split(",") if t.strip()]
        assert tags == sorted(tags)


class TestToDictVerboseName(TestCase):
    def test_verbose_name_keys(self):
        obj = SimpleItem.objects.create(name="vn")
        d = obj.to_dict(verbose_name=True, exclude=[])
        # 'name' field has default verbose_name='name'
        assert "name" in d
        # 'dtm_created' has verbose_name='DTM Created'
        assert "DTM Created" in d
        assert "DTM Updated" in d


class TestQuxModelToDictParams(TestCase):
    def test_fields_param(self):
        obj = SimpleItem.objects.create(name="fp")
        d = qux_model_to_dict(obj, fields=["name"])
        assert list(d.keys()) == ["name"]
        assert d["name"] == "fp"

    def test_exclude_none_param(self):
        obj = SimpleItem.objects.create(name="en")
        d = qux_model_to_dict(obj, exclude_none=True)
        # exclude_none=True sets exclude=[], so all fields are included
        assert "id" in d
        assert "name" in d
        assert "dtm_created" in d


class TestSlugAllowedChars(TestCase):
    def test_slug_uses_allowed_chars(self):
        obj = SlugItem.objects.create(name="allowed")
        slug_body = obj.slug.replace("item_", "")
        assert all(c in "abcdefghijklmnopqrstuvwxyz" for c in slug_body)


class TestQuxModel(TestCase):
    def test_is_abstract(self):
        assert QuxModel._meta.abstract is True

    def test_subclasses_coremodel(self):
        assert issubclass(QuxModel, CoreModel)


class TestPreSaveSlugSignal(TestCase):
    def test_no_slug_field_no_error(self):
        obj = SimpleItem.objects.create(name="noslugs")
        assert not hasattr(obj, "slug")

    def test_slug_prefix(self):
        obj = SlugItem.objects.create(name="prefixed")
        assert obj.slug.startswith("item_")

    def test_slug_length_respects_max(self):
        obj = SlugItem.objects.create(name="lentest")
        assert len(obj.slug) <= 16


class TestPostInitAuditMode(TestCase):
    def test_audit_mode_stores_old_state(self):
        user = User.objects.create_user("audituser", password="pass")
        obj = AuditedItem.objects.create(name="original", user=user)
        # After init from DB, __old should be set
        obj_from_db = AuditedItem.objects.get(pk=obj.pk)
        assert hasattr(obj_from_db, "__old")


class TestPostSaveAuditSignal(TestCase):
    def test_audit_trail_created_on_change(self):
        user = User.objects.create_user("auditsave", password="pass")
        obj = AuditedItem.objects.create(name="before", user=user)
        # Re-fetch to populate __old
        obj = AuditedItem.objects.get(pk=obj.pk)
        obj.name = "after"
        obj.save()

        summaries = TestAuditSummary.objects.filter(
            object_id=obj.pk,
        )
        assert summaries.exists()
        details = TestAuditDetails.objects.filter(audit_summary__in=summaries, field_name="name")
        assert details.exists()
        detail = details.first()
        assert detail.old_value == "before"
        assert detail.new_value == "after"

    def test_no_audit_when_no_change(self):
        user = User.objects.create_user("nochange", password="pass")
        obj = AuditedItem.objects.create(name="same", user=user)
        initial_count = TestAuditSummary.objects.count()
        obj = AuditedItem.objects.get(pk=obj.pk)
        obj.save()
        assert TestAuditSummary.objects.count() == initial_count


class TestRandomizeDecimalField(TestCase):
    def test_randomize_sets_decimal_field(self):
        obj = RandomItem()
        obj.randomize()
        assert obj.decimal_field_required is not None
        assert isinstance(obj.decimal_field_required, (int, float))
        assert 0 <= obj.decimal_field_required <= 100


class TestRandomizeDateField(TestCase):
    def test_randomize_sets_date_field(self):
        obj = RandomItem()
        obj.randomize()
        assert obj.date_field_required is not None
        assert isinstance(obj.date_field_required, datetime.date)


class TestRandomizeDateTimeField(TestCase):
    def test_randomize_sets_datetime_field(self):
        obj = RandomItem()
        obj.randomize()
        assert obj.datetime_field_required is not None
        assert isinstance(obj.datetime_field_required, datetime.datetime)


class TestRandomizeForeignKey(TestCase):
    def test_randomize_sets_fk_field(self):
        target = FKTarget.objects.create(name="target1")
        obj = FKSource()
        obj.randomize()
        assert obj.target is not None
        assert obj.target == target

    def test_randomize_fk_raises_when_no_related_objects(self):
        obj = FKSource()
        with self.assertRaises(ValueError):
            obj.randomize()

    def test_randomize_fk_picks_from_available(self):
        t1 = FKTarget.objects.create(name="t1")
        t2 = FKTarget.objects.create(name="t2")
        obj = FKSource()
        obj.randomize()
        assert obj.target in [t1, t2]


class TestQuxModelToDictM2MAttributeError(TestCase):
    """M2M AttributeError branch when values_list is not available."""

    def test_m2m_attribute_error_falls_back_to_list(self):
        rel1 = M2MRelated.objects.create(name="r1")
        rel2 = M2MRelated.objects.create(name="r2")
        obj = M2MItem.objects.create(name="m2m_attr")
        obj.related.set([rel1, rel2])

        # Mock value_from_object to return an iterable without values_list
        m2m_field = obj._meta.get_field("related")
        pks = list(obj.related.values_list("pk", flat=True))

        def mock_vfo(_self_field, _instance):
            # Return a plain list (no values_list method), triggering AttributeError
            return pks

        with patch.object(type(m2m_field), "value_from_object", mock_vfo):
            d = qux_model_to_dict(obj, fields=["related"])
            assert "related" in d
            assert set(d["related"]) == set(pks)


class TestQuxModelToDictExcludeNone(TestCase):
    """Exclude_none=True skips None values."""

    def test_exclude_none_skips_none_values(self):
        obj = TagItem.objects.create(name="excl_none", tags=None)
        d = qux_model_to_dict(obj, exclude_none=True, exclude=[])
        assert "name" in d
        assert d["name"] == "excl_none"
        # tags is None, so with exclude_none=True it should be skipped
        assert "tags" not in d


class TestRandomizeEmailAndURLField(TestCase):
    """EmailField/URLField randomize branches.

    Django's EmailField.get_internal_type() returns 'CharField', so
    the 'EmailField' branch in randomize() is only reachable if a custom
    field returns 'EmailField'. We mock get_internal_type to test this.
    """

    def test_randomize_email_field_branch(self):
        obj = RandomItem()
        # Patch the email_field_required's get_internal_type to return "EmailField"
        field = obj._meta.get_field("email_field_required")
        original_git = field.get_internal_type
        field.get_internal_type = lambda: "EmailField"
        try:
            obj.randomize()
            assert "@" in obj.email_field_required
            assert obj.email_field_required.endswith(".com")
        finally:
            field.get_internal_type = original_git

    def test_randomize_url_field_branch(self):
        obj = RandomItem()
        field = obj._meta.get_field("url_field_required")
        original_git = field.get_internal_type
        field.get_internal_type = lambda: "URLField"
        try:
            obj.randomize()
            assert obj.url_field_required.startswith("https://")
            assert obj.url_field_required.endswith(".com")
        finally:
            field.get_internal_type = original_git


class TestRandomizeUnknownFieldType(TestCase):
    """Else branch in randomize for unknown field types."""

    def test_randomize_unknown_field_sets_none(self):
        obj = UnknownFieldItem()
        obj.randomize()
        # GenericIPAddressField get_internal_type() returns 'GenericIPAddressField'
        # which is not handled, so it should be set to None
        assert obj.ip_address is None


class TestGettagsRemovesEmpty(TestCase):
    """Gettags removes empty string from tags list."""

    def test_gettags_removes_empty_from_trailing_comma(self):
        obj = TagItem.objects.create(name="trail", tags="alpha,,beta")
        result = obj.gettags()
        assert "" not in result
        assert set(result) == {"alpha", "beta"}

    def test_gettags_removes_empty_from_leading_comma(self):
        obj = TagItem.objects.create(name="lead", tags=",alpha,beta")
        result = obj.gettags()
        assert "" not in result


class TestPreSaveSlugAlreadySet(TestCase):
    """Pre_save_coremodel returns early when slug is already set."""

    def test_existing_slug_not_overwritten(self):
        obj = SlugItem(name="presave", slug="item_mycustomslug")
        obj.save()
        assert obj.slug == "item_mycustomslug"


class TestPostInitAuditModeStoresOld(TestCase):
    """Post_init_coremodel stores __old when AUDIT_MODE=True."""

    def test_old_state_stored_after_fetch(self):
        user = User.objects.create_user("postinit_user", password="pass")
        obj = AuditedItem.objects.create(name="original", user=user)
        obj_from_db = AuditedItem.objects.get(pk=obj.pk)
        old = getattr(obj_from_db, "__old", None)
        assert old is not None
        assert old["name"] == "original"


class TestPostSaveAuditModeDisabled(TestCase):
    """Post_save_coremodel returns early when AUDIT_MODE=False."""

    def test_no_audit_for_non_audited_model(self):
        initial_count = TestAuditSummary.objects.count()
        SimpleItem.objects.create(name="noaudit")
        assert TestAuditSummary.objects.count() == initial_count


class TestPostSaveAuditSummaryNone(TestCase):
    """Audit_summary or audit_details is None."""

    def test_no_audit_when_summary_is_none(self):
        initial_count = TestAuditSummary.objects.count()
        obj = AuditedNoDetailsItem.objects.create(name="before")
        obj = AuditedNoDetailsItem.objects.get(pk=obj.pk)
        obj.name = "after"
        obj.save()
        assert TestAuditSummary.objects.count() == initial_count


class TestPostSaveAuditUserNone(TestCase):
    """User is None, tries _user, still None, skips audit."""

    def test_no_audit_when_no_user(self):
        initial_count = TestAuditSummary.objects.count()
        obj = AuditedNoUserItem.objects.create(name="before")
        obj = AuditedNoUserItem.objects.get(pk=obj.pk)
        obj.name = "after"
        obj.save()
        # No user on model, no _user attribute, so audit is skipped
        assert TestAuditSummary.objects.count() == initial_count


class TestPostSaveAuditFileField(TestCase):
    """FileField handling in audit diff."""

    def test_audit_file_field_change(self):
        user = User.objects.create_user("filefld_user", password="pass")
        obj = AuditedFileItem.objects.create(name="filetest", user=user)
        obj = AuditedFileItem.objects.get(pk=obj.pk)
        # Set the doc field's underlying attribute to simulate a file change
        obj.doc = "test_uploads/test.txt"
        obj.save()

        details = TestAuditDetails.objects.filter(field_name="doc")
        assert details.exists()


class TestPostSaveAuditDateField(TestCase):
    """DateField/DateTimeField handling in audit diff."""

    def test_audit_date_field_change(self):
        user = User.objects.create_user("datefld_user", password="pass")
        obj = AuditedFileItem.objects.create(
            name="datetest",
            event_date=datetime.date(2024, 1, 1),
            user=user,
        )
        obj = AuditedFileItem.objects.get(pk=obj.pk)
        obj.event_date = datetime.date(2025, 6, 15)
        obj.save()

        details = TestAuditDetails.objects.filter(field_name="event_date")
        assert details.exists()
        detail = details.first()
        assert "2024-01-01" in str(detail.old_value)
        assert "2025-06-15" in str(detail.new_value)

    def test_audit_datetime_field_change(self):
        user = User.objects.create_user("dtfld_user", password="pass")
        obj = AuditedFileItem.objects.create(
            name="dttest",
            event_datetime=datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
            user=user,
        )
        obj = AuditedFileItem.objects.get(pk=obj.pk)
        obj.event_datetime = datetime.datetime(2025, 6, 15, 14, 30, 0, tzinfo=datetime.timezone.utc)
        obj.save()

        details = TestAuditDetails.objects.filter(field_name="event_datetime")
        assert details.exists()


class TestQuxModelToDictFieldDoesNotExist(TestCase):
    """FieldDoesNotExist branch in M2M handling."""

    def test_m2m_field_does_not_exist_fallback(self):
        rel1 = M2MRelated.objects.create(name="r1")
        obj = M2MItem.objects.create(name="m2m_fdne")
        obj.related.set([rel1])

        m2m_field = obj._meta.get_field("related")

        def mock_vfo(_self_field, _instance):
            mock_qs = MagicMock()
            mock_qs.values_list.side_effect = FieldDoesNotExist("fake")
            return mock_qs

        with patch.object(type(m2m_field), "value_from_object", mock_vfo):
            d = qux_model_to_dict(obj, fields=["related"])
            assert d["related"] == []


class TestSlugCollisionWhileLoop(TestCase):
    """While loop for slug collision in pre_save."""

    def test_slug_regenerated_on_collision(self):
        call_count = [0]
        original_filter = SlugItem.objects.filter

        def mock_filter(**kwargs):
            qs = original_filter(**kwargs)
            if "slug" in kwargs:
                call_count[0] += 1
                if call_count[0] <= 1:
                    # First call returns exists()=True (collision)
                    mock_qs = MagicMock()
                    mock_qs.exists.return_value = True
                    return mock_qs
            return qs

        with patch.object(type(SlugItem.objects), "filter", side_effect=mock_filter):
            obj = SlugItem(name="collision_test")
            obj.save()

        assert obj.slug is not None
        assert obj.slug.startswith("item_")


class TestRandomizeDebugLog(TestCase):
    """Logger.debug in randomize when DEBUG=True."""

    @override_settings(DEBUG=True)
    def test_randomize_logs_when_debug(self):
        obj = RandomItem()
        with patch("qux.models.base.logger") as mock_logger:
            obj.randomize()
            mock_logger.debug.assert_called()


class TestDebugVerbosePreSave(TestCase):
    """Pre_save_coremodel DEBUG_VERBOSE logging."""

    @override_settings(DEBUG_VERBOSE=True)
    def test_pre_save_debug_verbose(self):
        obj = SlugItem(name="verbose_pre", slug="item_verbose1")
        obj.save()
        assert obj.slug == "item_verbose1"


class TestDebugVerbosePostInit(TestCase):
    """Post_init_coremodel DEBUG_VERBOSE logging."""

    @override_settings(DEBUG_VERBOSE=True)
    def test_post_init_debug_verbose(self):
        user = User.objects.create_user("verbose_user", password="pass")
        obj = AuditedItem.objects.create(name="verbose_init", user=user)
        obj_from_db = AuditedItem.objects.get(pk=obj.pk)
        assert hasattr(obj_from_db, "__old")


class TestDebugVerbosePostSave(TestCase):
    """Post_save_coremodel DEBUG_VERBOSE logging."""

    @override_settings(DEBUG_VERBOSE=True)
    def test_post_save_debug_verbose(self):
        user = User.objects.create_user("verbose_save", password="pass")
        obj = AuditedItem.objects.create(name="verbose_save", user=user)
        obj = AuditedItem.objects.get(pk=obj.pk)
        obj.name = "verbose_after"
        obj.save()
