from django.conf import settings
from django.contrib.sites.models import Site
from django.db import models

from qux.models.base import CoreModel


class SiteConfiguration(CoreModel):

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="site_config")
    name = models.CharField(max_length=32)
    value = models.JSONField()
    description = models.CharField(max_length=255, null=True)

    @classmethod
    def setenv_site(cls, name, value, description=None):
        if not Site.objects.filter(id=settings.SITE_ID):
            print("INVALID SITE ID")
            return

        site = Site.objects.get(id=settings.SITE_ID)
        obj = cls.objects.get_or_none(name=name, site=site)

        if obj:
            obj.value = value
            if description:
                obj.description = description
            obj.save()
        else:
            obj = cls.objects.create(
                name=name, value=value, description=description, site=site
            )
        return obj

    @classmethod
    def getenv_site(cls, name, default_value):
        if not Site.objects.filter(id=settings.SITE_ID):
            print("INVALID SITE ID")
            return

        site = Site.objects.get(id=settings.SITE_ID)
        obj = cls.objects.get_or_none(name=name, site=site)
        if obj:
            return obj.value
        return default_value

    class Meta:
        unique_together = ("name", "site")
