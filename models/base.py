import datetime
import random
from itertools import chain

from django.conf import settings
from django.contrib import admin
from django.core.exceptions import FieldError
from django.core.exceptions import ObjectDoesNotExist, FieldDoesNotExist
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.fields import DateField, DateTimeField
from django.db.models.fields.files import FileField
from django.db.models.fields.related import ManyToManyField
from django.db.models.signals import pre_save, post_init, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.crypto import get_random_string

from qux.lorem import Lorem

# Commonly used definitions
default_null_blank = dict(default=None, null=True, blank=True)

# https://en.wikipedia.org/wiki/E.164
regexp_phone = RegexValidator(
    regex=r"^\+?[1-9]\d{4,14}$",
    message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
)


def qux_model_to_dict(
    instance,
    fields=None,
    exclude=None,
    exclude_none=False,
    verbose_name=False,
):
    if exclude is None:
        exclude = ["id", "dtm_created", "dtm_updated"]
    opts = instance._meta
    data = {}
    if exclude_none:
        exclude = []

    for f in chain(opts.concrete_fields, opts.many_to_many):
        if fields is not None and f.name not in fields:
            continue
        if exclude and f.name in exclude:
            continue
        field_name = f.verbose_name if verbose_name else f.name
        if isinstance(f, ManyToManyField):
            if instance.pk is None:
                data[field_name] = []
            else:
                try:
                    data[field_name] = list(
                        f.value_from_object(instance).values_list("pk", flat=True)
                    )
                except AttributeError:
                    data[field_name] = list(f.value_from_object(instance))
                except FieldDoesNotExist:
                    data[field_name] = []
        else:
            data[field_name] = f.value_from_object(instance)
    return data


class CoreManager(models.Manager):
    def get_or_none(self, **kwargs):
        try:
            return self.get(**kwargs)
        except ObjectDoesNotExist:
            return None


class CoreModel(models.Model):
    objects = CoreManager()
    all_objects = models.Manager()

    dtm_created = models.DateTimeField(verbose_name="DTM Created", auto_now_add=True)
    dtm_updated = models.DateTimeField(verbose_name="DTM Updated", auto_now=True)

    class Meta:
        abstract = True

    # def save(self, *args, **kwargs):
    #     self.full_clean()
    #     super().save(*args, **kwargs)

    def get_slug(self, slug_length: int = 8):
        allowed_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        allowed_chars = getattr(self.__class__, "SLUG_ALLOWED_CHARS", allowed_chars)

        # First char should be alpha only
        first_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        first_chars = [x for x in allowed_chars if x in first_chars]

        slug = random.choice(first_chars)
        slug = slug + get_random_string(slug_length - 1, allowed_chars)
        return slug

    @classmethod
    def initdata(cls):
        print("{}.initdata()".format(cls.__name__))

    def to_dict(
        self,
        fields=None,
        exclude=None,
        exclude_none=False,
        verbose_name=False,
    ):
        if exclude is None:
            exclude = ["id", "dtm_created", "dtm_updated"]
        return qux_model_to_dict(
            self,
            fields=fields,
            exclude=exclude,
            exclude_none=exclude_none,
            verbose_name=verbose_name,
        )

    @classmethod
    def get_dict(cls, pk):
        result = cls.objects.get(id=pk)
        return result.to_dict()

    def randomize(self):
        if settings.DEBUG:
            print(f"{self.__class__.__name__}.randomize()")

        for field in self._meta.get_fields():
            if field.auto_created or not field.editable or field.null:
                continue

            internal_type = field.get_internal_type()
            if internal_type == "CharField":
                value = get_random_string(field.max_length)
            elif internal_type == "TextField":
                value = Lorem.words(random.randint(5, 20))
            elif internal_type == "IntegerField":
                value = random.randint(0, 100)
            elif internal_type == "DecimalField":
                value = random.randint(0, 10000) / 100
            elif internal_type == "DateField":
                value = datetime.date.today()
            elif internal_type == "DateTimeField":
                value = datetime.datetime.now()
            elif internal_type == "BooleanField":
                value = random.choice([True, False])
            elif internal_type == "EmailField":
                value = get_random_string(10) + "@" + get_random_string(10) + ".com"
            elif internal_type == "URLField":
                value = "https://" + get_random_string(10) + ".com"
            elif internal_type == "ForeignKey":
                queryset = field.related_model.objects.all()
                if not queryset.exists():
                    raise Exception(f"{field.related_model.__name__} has no objects")
                value = random.choice(field.related_model.objects.all())
            else:
                print(f"randomize: {field.name} {internal_type}")
                value = None

            setattr(self, field.name, value)

        print(self.__dict__)

    def settag(self, tag: str):
        if not hasattr(self, "tags"):
            return

        tags = []
        if self.tags and hasattr("strip", self.tags):
            tags = [x.strip() for x in self.tags.split(",")]
        tags.append(tag)
        tags.sort()
        self.tags = ",".join(tags)
        self.save()

    def deltag(self, tag: str):
        if not hasattr(self, "tags"):
            return

        tags = []
        if self.tags:
            tags = [x.strip() for x in self.tags.split(",")]
        if tag in tags:
            tags.remove(tag)
        tags.sort()
        self.tags = ",".join(tags)
        self.save()

    def hastag(self, tag: str):
        if not hasattr(self, "tags"):
            return

        tags = []
        if self.tags and self.tags != "":
            tags = [x.strip() for x in self.tags.split(",")]
        if tag in tags:
            return True
        return False

    def gettags(self):
        if not hasattr(self, "tags"):
            return

        tags = []
        if self.tags and self.tags != "":
            tags = [x.strip() for x in self.tags.split(",")]
        if "" in tags:
            tags.remove("")
        return tags

    @classmethod
    def gettaglist(cls):
        try:
            tags = (
                cls.objects.all()
                .exclude(models.Q(tags__isnull=True) | models.Q(tags=""))
                .values_list("tags", flat=True)
                .distinct()
            )
        except FieldError:
            return

        tags = ",".join(tags)
        tags = [x.strip() for x in tags.split(",")]
        tags = list(set(tags))
        if "" in tags:
            tags.remove("")
        return tags


@receiver(pre_save)
def pre_save_coremodel(sender, instance, **kwargs):
    if not isinstance(instance, CoreModel):
        return

    if getattr(settings, "DEBUG_VERBOSE", False):
        print(f"pre_save_coremodel({sender.__name__}, {instance})")

    if getattr(instance, "slug", None):
        return

    # Slug must be None because otherwise it would have returned
    if hasattr(instance, "slug"):
        prefix = getattr(instance.__class__, "SLUG_PREFIX", None)
        prefix = prefix + "_" if prefix else ""

        slug_length = instance._meta.get_field("slug").max_length - len(prefix)
        instance.slug = prefix + instance.get_slug(slug_length)
        while instance.__class__.objects.filter(slug=instance.slug).exists():
            instance.slug = prefix + instance.get_slug()


@receiver(post_init)
def post_init_coremodel(sender, instance, **kwargs):
    if not isinstance(instance, CoreModel):
        return

    if getattr(settings, "DEBUG_VERBOSE", False):
        print(f"post_init_coremodel({sender.__name__}, {instance})")

    if getattr(sender, "AUDIT_MODE", False):
        instance.__old = qux_model_to_dict(instance)


@receiver(post_save)
def post_save_coremodel(sender, instance, created, **kwargs):
    if not isinstance(instance, CoreModel):
        return

    if getattr(settings, "DEBUG_VERBOSE", False):
        print(f"post_core_coremodel({sender.__name__}, {instance})")

    if not getattr(sender, "AUDIT_MODE", False):
        return

    if hasattr(instance, "__old"):
        old_data = instance.__old
        new_data = qux_model_to_dict(instance)
        diff = {k: (old_data[k], v) for k, v in new_data.items() if v != old_data[k]}
        if not diff:
            return

        audit_summary = getattr(sender, "AUDIT_SUMMARY", None)
        audit_details = getattr(sender, "AUDIT_DETAILS", None)

        if audit_summary is None or audit_details is None:
            return

        user = getattr(instance, "user", None)
        if user is None:
            user = getattr(instance, "_user", None)

        if user is None:
            user = User.objects.get(id=1)

        audit_summary_obj = audit_summary.objects.create(
            user=getattr(instance, "user", user),
            content_object=instance,
        )

        for k, (old_value, new_value) in diff.items():
            kfield = instance.__class__._meta.get_field(k)
            if isinstance(kfield, FileField):
                old_value = old_value.name if old_value else None
                new_value = new_value.name if new_value else None

            if isinstance(kfield, DateField) or isinstance(kfield, DateTimeField):
                old_value = old_value.isoformat() if old_value else None
                new_value = new_value.isoformat() if new_value else None

            audit_details.objects.create(
                audit_summary=audit_summary_obj,
                field_name=k,
                old_value=old_value,
                new_value=new_value,
            )


class CoreModelAdmin(admin.ModelAdmin):
    list_per_page = 50
    show_full_result_count = False

    # noinspection PyProtectedMember
    def get_queryset(self, request):
        """
        Returns a QuerySet of all model instances that can be edited by the
        admin site. This is used by changelist_view.
        """

        # Default: qs = self.model._default_manager.get_query_set()
        qs = self.model._default_manager.get_queryset()

        # TODO: this should be handled by some parameter to the ChangeList.
        # () because *None is bad
        ordering = self.ordering or ()
        if ordering:
            qs = qs.order_by(*ordering)
        return qs


class CoreManagerPlus(CoreManager):
    def get(self, *args, **kwargs):
        # print("get is_deleted=False")
        return self.get_queryset().get(*args, **kwargs)

    def filter(self, *args, **kwargs):
        # print("filter is_deleted=False")
        return self.get_queryset().filter(*args, **kwargs)

    def get_queryset(self):
        # print("get_queryset is_deleted=False")
        return super(CoreManagerPlus, self).get_queryset().filter(is_deleted=False)

    def all_with_deleted(self):
        # print("all_with_deleted is_deleted=False")
        return super(CoreManagerPlus, self).get_queryset()


class CoreModelPlus(CoreModel):
    objects = CoreManagerPlus()
    is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.dtm_created:
            self.dtm_created = timezone.now()
        self.dtm_updated = timezone.now()
        return super(CoreModelPlus, self).save(*args, **kwargs)

    def delete(self, **kwargs):
        self.is_deleted = True
        self.save()

    def restore(self):
        self.is_deleted = False
        self.save()


class CoreModelPlusAdmin(admin.ModelAdmin):
    list_display = (
        "is_deleted",
        "dtm_created",
        "dtm_updated",
    )
    list_filter = ("is_deleted",)
    readonly_fields = (
        "dtm_created",
        "dtm_updated",
    )

    list_per_page = 50
    show_full_result_count = False

    # noinspection PyProtectedMember
    def get_queryset(self, request):
        """
        Returns a QuerySet of all model instances that can be edited by the
        admin site. This is used by changelist_view.
        """

        # Default: qs = self.model._default_manager.get_query_set()
        qs = self.model._default_manager.all_with_deleted()

        # TODO: this should be handled by some parameter to the ChangeList.
        # () because *None is bad
        ordering = self.ordering or ()
        if ordering:
            qs = qs.order_by(*ordering)
        return qs


class AbstractLead(CoreModel):
    regexp = RegexValidator(
        regex=r"^\+?[1-9]\d{4,14}$",
        message=(
            "Phone number must be entered in the format: '+999999999'. "
            "Up to 15 digits allowed.",
        ),
    )

    # Lead
    firstname = models.CharField("First Name", max_length=128, **default_null_blank)
    lastname = models.CharField("Last Name", max_length=128, **default_null_blank)
    email = models.EmailField(max_length=240, **default_null_blank)
    phone = models.CharField(max_length=16, **default_null_blank, validators=[regexp])

    # request.META
    http_accept_language = models.CharField(
        "HTTP Language", max_length=256, **default_null_blank
    )
    http_user_agent = models.CharField(
        "HTTP UserAgent", max_length=512, **default_null_blank
    )
    remote_addr = models.CharField(
        "Remote Address", max_length=256, **default_null_blank
    )

    # UTM
    utm_source = models.CharField("UTM Source", max_length=256, **default_null_blank)
    utm_medium = models.CharField("UTM Medium", max_length=256, **default_null_blank)
    utm_campaign = models.CharField(
        "UTM Campaign", max_length=256, **default_null_blank
    )
    utm_term = models.CharField("UTM Term", max_length=256, **default_null_blank)
    utm_content = models.CharField("UTM Content", max_length=256, **default_null_blank)

    get_params = models.JSONField(default=dict, blank=True)

    class Meta:
        abstract = True

    @classmethod
    def update_or_create_from_request(cls, request, additional_fields=None):
        """
        Create or update lead from request
        additional_fields in facebook context might include:
        [
            'fbclid', 'ad_id', 'adset_id', 'campaign_id', 'ad_name',
            'adset_name', 'campaign_name', 'placement', 'site_source_name', 'ref'
        ]

        """
        reqdata = request.GET.dict()
        clsobj = cls()

        metadata = ["HTTP_ACCEPT_LANGUAGE", "HTTP_USER_AGENT", "REMOTE_ADDR"]
        [setattr(clsobj, f.lower(), request.META.get(f, None)) for f in metadata]

        urlfields = [
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_term",
            "utm_content",
        ]

        if additional_fields and isinstance(additional_fields, list):
            urlfields += additional_fields

        datadict = {k.lower().replace(" ", "_"): v for k, v in reqdata.items()}

        if "ad_set" in datadict and datadict["ad_set"]:
            datadict["adset_name"] = datadict["ad_set"]

        islink = any([f for f in urlfields if f in datadict.keys()])
        if islink:
            fields = [f for f in urlfields if f in datadict]
            [setattr(clsobj, f, datadict[f]) for f in fields]

        clsobj.get_params = datadict
        clsobj.save()

        return clsobj
