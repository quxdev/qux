import datetime
import logging
import random
from itertools import chain

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist, FieldError, ObjectDoesNotExist
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.fields import DateField, DateTimeField
from django.db.models.fields.files import FileField
from django.db.models.fields.related import ManyToManyField
from django.db.models.signals import post_init, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone as django_timezone
from django.utils.crypto import get_random_string

logger = logging.getLogger("qux")

# Lorem ipsum filler used by ``randomize()`` for TextField defaults during
# model fuzzing. Inlined here (was qux.lorem) — too small to justify its own module.
_LOREM_WORDS = [
    "Lorem",
    "ipsum",
    "dolor",
    "sit",
    "amet,",
    "consectetur",
    "adipiscing",
    "elit,",
    "sed",
    "do",
    "eiusmod",
    "tempor",
    "incididunt",
    "ut",
    "labore",
    "et",
    "dolore",
    "magna",
    "aliqua.",
    "Ut",
    "enim",
    "ad",
    "minim",
    "veniam,",
    "quis",
    "nostrud",
    "exercitation",
    "ullamco",
    "laboris",
    "nisi",
    "ut",
    "aliquip",
    "ex",
    "ea",
    "commodo",
    "consequat.",
    "Duis",
    "aute",
    "irure",
    "dolor",
    "in",
    "reprehenderit",
    "in",
    "voluptate",
    "velit",
    "esse",
    "cillum",
    "dolore",
    "eu",
    "fugiat",
    "nulla",
    "pariatur.",
    "Excepteur",
    "sint",
    "occaecat",
    "cupidatat",
    "non",
    "proident,",
    "sunt",
    "in",
    "culpa",
    "qui",
    "officia",
    "deserunt",
    "mollit",
    "anim",
    "id",
    "est",
    "laborum.",
]


def _lorem(n: int = 5) -> str:
    """Return the first ``n`` words of lorem ipsum (replaces qux.lorem.Lorem.words)."""
    return " ".join(_LOREM_WORDS[:n])


# Commonly used definitions
default_null_blank = {"default": None, "null": True, "blank": True}

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

    for f in chain(opts.concrete_fields, opts.many_to_many):
        if fields is not None and f.name not in fields:
            continue
        if not exclude_none and exclude and f.name in exclude:
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
            value = f.value_from_object(instance)
            if exclude_none and value is None:
                continue
            data[field_name] = value
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

    def get_slug(self, slug_length: int = 8):
        allowed_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        allowed_chars = getattr(self.__class__, "SLUG_ALLOWED_CHARS", allowed_chars)

        # First char should be alpha only
        first_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        first_chars = [x for x in allowed_chars if x in first_chars]

        slug = random.choice(first_chars)
        return slug + get_random_string(slug_length - 1, allowed_chars)

    @classmethod
    def initdata(cls):
        logger.debug("%s.initdata()", cls.__name__)

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
            logger.debug("%s.randomize()", self.__class__.__name__)

        for field in self._meta.get_fields():
            if field.auto_created or not field.editable or field.null:
                continue

            internal_type = field.get_internal_type()
            if internal_type == "CharField":
                value = get_random_string(field.max_length)
            elif internal_type == "TextField":
                value = _lorem(random.randint(5, 20))
            elif internal_type == "IntegerField":
                value = random.randint(0, 100)
            elif internal_type == "DecimalField":
                value = random.randint(0, 10000) / 100
            elif internal_type == "DateField":
                value = datetime.date.today()
            elif internal_type == "DateTimeField":
                value = django_timezone.now()
            elif internal_type == "BooleanField":
                value = random.choice([True, False])
            elif internal_type == "EmailField":
                value = get_random_string(10) + "@" + get_random_string(10) + ".com"
            elif internal_type == "URLField":
                value = "https://" + get_random_string(10) + ".com"
            elif internal_type == "ForeignKey":
                all_objects = list(field.related_model.objects.all())
                if not all_objects:
                    raise ValueError(f"{field.related_model.__name__} has no objects")
                value = random.choice(all_objects)
            else:
                logger.debug("randomize: %s %s", field.name, internal_type)
                value = None

            setattr(self, field.name, value)

        logger.debug(self.__dict__)

    def settag(self, tag: str):
        if not hasattr(self, "tags"):
            return None

        tags = [x.strip() for x in getattr(self, "tags", "").split(",")]
        if tag not in tags:
            tags.append(tag)
        tags.sort()
        self.tags = ",".join(tags)
        self.save()

        return tags

    def deltag(self, tag: str):
        if not hasattr(self, "tags"):
            return False

        tags = [x.strip() for x in getattr(self, "tags", "").split(",")]
        if tag in tags:
            tags.remove(tag)
        tags.sort()
        self.tags = ",".join(tags)
        self.save()

        return True

    def hastag(self, tag: str):
        if not hasattr(self, "tags"):
            return False

        tags = [x.strip() for x in getattr(self, "tags", "").split(",")]
        return tag in tags

    def gettags(self):
        if not hasattr(self, "tags"):
            return None

        tags = [x.strip() for x in getattr(self, "tags", "").split(",")]
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
            return None

        tags = ",".join(tags)
        tags = [x.strip() for x in tags.split(",")]
        tags = list(set(tags))
        if "" in tags:
            tags.remove("")
        return tags


class QuxModel(CoreModel):
    class Meta:
        abstract = True


@receiver(pre_save)
def pre_save_coremodel(sender, instance, **kwargs):
    if not issubclass(sender, CoreModel):
        return

    if getattr(settings, "DEBUG_VERBOSE", False):
        logger.debug("pre_save_coremodel(%s, %s)", sender.__name__, instance)

    if getattr(instance, "slug", None):
        return

    # Slug must be None because otherwise it would have returned
    if hasattr(instance, "slug"):
        prefix = getattr(instance.__class__, "SLUG_PREFIX", None)
        prefix = prefix + "_" if prefix else ""

        slug_length = instance._meta.get_field("slug").max_length - len(prefix)
        instance.slug = prefix + instance.get_slug(slug_length)
        while instance.__class__.objects.filter(slug=instance.slug).exists():
            instance.slug = prefix + instance.get_slug(slug_length)


@receiver(post_init)
def post_init_coremodel(sender, instance, **kwargs):
    if not issubclass(sender, CoreModel):
        return

    if getattr(settings, "DEBUG_VERBOSE", False):
        logger.debug("post_init_coremodel(%s, %s)", sender.__name__, instance)

    if getattr(sender, "AUDIT_MODE", False):
        instance.__old = qux_model_to_dict(instance)


@receiver(post_save)
def post_save_coremodel(sender, instance, created, **kwargs):
    if not issubclass(sender, CoreModel):
        return

    if getattr(settings, "DEBUG_VERBOSE", False):
        logger.debug("post_save_coremodel(%s, %s)", sender.__name__, instance)

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
            logger.warning(
                "Audit: no user found for %s (pk=%s), skipping audit.",
                sender.__name__,
                instance.pk,
            )
            return

        audit_summary_obj = audit_summary.objects.create(
            user=getattr(instance, "user", user),
            content_object=instance,
        )

        for k, (old_value, new_value) in diff.items():
            kfield = instance.__class__._meta.get_field(k)
            if isinstance(kfield, FileField):
                old_value = old_value.name if hasattr(old_value, "name") else None
                new_value = new_value.name if hasattr(new_value, "name") else None

            if isinstance(kfield, (DateField, DateTimeField)):
                old_value = old_value.isoformat() if hasattr(old_value, "isoformat") else None
                new_value = new_value.isoformat() if hasattr(new_value, "isoformat") else None

            audit_details.objects.create(
                audit_summary=audit_summary_obj,
                field_name=k,
                old_value=old_value,
                new_value=new_value,
            )


class AbstractLead(CoreModel):
    regexp = RegexValidator(
        regex=r"^\+?[1-9]\d{4,14}$",
        message=(
            "Phone number must be entered in the format: '+999999999'. " "Up to 15 digits allowed."
        ),
    )

    # Lead
    firstname = models.CharField("First Name", max_length=128, **default_null_blank)
    lastname = models.CharField("Last Name", max_length=128, **default_null_blank)
    email = models.EmailField(max_length=240, **default_null_blank)
    phone = models.CharField(max_length=16, **default_null_blank, validators=[regexp])

    # request.META
    http_accept_language = models.CharField("HTTP Language", max_length=256, **default_null_blank)
    http_user_agent = models.CharField("HTTP UserAgent", max_length=512, **default_null_blank)
    remote_addr = models.CharField("Remote Address", max_length=256, **default_null_blank)

    # UTM
    utm_source = models.CharField("UTM Source", max_length=256, **default_null_blank)
    utm_medium = models.CharField("UTM Medium", max_length=256, **default_null_blank)
    utm_campaign = models.CharField("UTM Campaign", max_length=256, **default_null_blank)
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
        for f in metadata:
            setattr(clsobj, f.lower(), request.META.get(f, None))

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

        islink = any(f for f in urlfields if f in datadict)
        if islink:
            fields = [f for f in urlfields if f in datadict]
            for f in fields:
                setattr(clsobj, f, datadict[f])

        clsobj.get_params = datadict
        clsobj.save()

        return clsobj
