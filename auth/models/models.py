import json
import os

from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from qux.models import CoreModel, default_null_blank
from qux.utils import cast


class Company(CoreModel):
    SLUG_PREFIX = "company"
    SLUG_ALLOWED_CHARS = "abcdefghijklmnopqrstuvwxyz"

    slug = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=128)
    address = models.TextField(**default_null_blank)
    domain = models.CharField(max_length=255, unique=True)
    url = models.URLField("URL", max_length=1024, **default_null_blank)

    class Meta:
        db_table = "qux_auth_company"
        verbose_name = "Company"
        verbose_name_plural = "Companies"

    def __str__(self):
        return self.name if self.name else self.slug


class Profile(CoreModel):
    SLUG_PREFIX = "user"
    SLUG_ALLOWED_CHARS = "abcdefghijklmnopqrstuvwxyz"

    # https://en.wikipedia.org/wiki/E.164
    regexp = RegexValidator(
        regex=r"^\+?[1-9]\d{4,14}$",
        message="Phone number must be entered in the format: '+999999999'. "
        "Up to 15 digits allowed.",
    )

    slug = models.CharField(max_length=11, unique=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=16, validators=[regexp], **default_null_blank)
    company = models.ForeignKey(
        Company,
        on_delete=models.DO_NOTHING,
        **default_null_blank,
        related_name="profiles",
    )
    title = models.CharField(max_length=255, **default_null_blank)
    is_live = models.BooleanField(default=False)

    class Meta:
        db_table = "qux_auth_profile"
        verbose_name = "User Profile"

    @classmethod
    def get_user(cls, slug):
        return cls.objects.get(slug=slug).user

    def get_initials(self):
        user = self.user
        if user.first_name and user.last_name:
            initials = user.first_name[0] + " " + user.last_name[0]
        elif user.first_name:
            initials = user.first_name[0]
        elif user.last_name:
            initials = user.last_name[0]
        else:
            initials = None

        return initials

    def get_fullname(self):
        user = self.user
        if user.first_name and user.last_name:
            fullname = user.first_name + " " + user.last_name
        elif user.first_name:
            fullname = user.first_name
        elif user.last_name:
            fullname = user.last_name
        else:
            fullname = user.email

        return fullname

    @property
    def company_users(self):
        """
        Return a list of ['user_slug', 'user_slug', ...]
        """
        results = list(self.company.profiles.all().values_list("slug", flat=True))
        return results


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created and not hasattr(instance, "Profile"):
        profile_object = Profile.objects.create(user=instance, id=instance.id)
        profile_object.save()


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    p, created = Profile.objects.get_or_create(user=instance)
    p.save()


class Service(CoreModel):
    SLUG_PREFIX = "service"

    slug = models.CharField(max_length=14, unique=True)
    name = models.CharField(max_length=64, unique=True)
    description = models.TextField(**default_null_blank)
    url = models.URLField("URL", max_length=1024, **default_null_blank)

    class Meta:
        db_table = "qux_service"
        verbose_name = "Service"
        verbose_name_plural = "Services"

    def __str__(self):
        return self.name

    def get_preferences(self, include=None, exclude=None):
        preferences = self.preferences.all()
        if include:
            preferences = preferences.filter(name__in=include)
        if exclude:
            preferences = preferences.exclude(name__in=exclude)

        prefs = []
        for item in [x.to_dict() for x in preferences]:
            item["value"] = cast(item["type"], item["value"])
            prefs.append(item)

        return prefs


class Preference(CoreModel):
    SLUG_PREFIX = "pref"

    slug = models.CharField(max_length=11, unique=True)
    user = models.ForeignKey(
        User, on_delete=models.DO_NOTHING, related_name="preferences"
    )
    service = models.ForeignKey(
        Service, on_delete=models.DO_NOTHING, related_name="preferences"
    )
    name = models.CharField(max_length=128)
    value = models.TextField(**default_null_blank)
    type = models.CharField(max_length=32, **default_null_blank)
    category = models.CharField(max_length=32, **default_null_blank)
    is_basic = models.BooleanField(default=False)

    class Meta:
        db_table = "qux_preference"
        verbose_name = "Preference"
        verbose_name_plural = "Preferences"
        unique_together = ("user", "service", "name")

    def __str__(self):
        return f"{self.service}.{self.name}"

    @classmethod
    def get_preferences(cls, user, service):
        return cls.objects.filter(user=user, service=service)

    @classmethod
    def loaddata(cls):
        fixtures = os.getenv("QUX_FIXTURES_PREFERENCE", "fixtures/preferences.json")
        if not os.path.exists(fixtures):
            return

        print(f"Fixture: {fixtures}")

        with open(fixtures, "r") as f:
            data = json.load(f)

        for item in data:
            try:
                item["user"] = User.objects.get(id=item["user"])
            except User.DoesNotExist:
                continue

            service = Service.objects.get_or_none(id=item["service"])
            if service is None:
                continue
            else:
                item["service"] = service

            cls.objects.update_or_create(**item)
