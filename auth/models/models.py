import json
import os

from django.contrib.auth.models import User
from django.db import models

from qux.models import CoreModel, default_null_blank
from qux.utils import cast


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
