from django.db import models
from django.contrib.sites.models import Site
from qux.models import CoreModel, default_null_blank


class SEOModel(CoreModel):
    class Meta:
        abstract = True


class SEOSite(SEOModel):
    site = models.OneToOneField(Site, on_delete=models.CASCADE)
    name = models.CharField(max_length=64)
    title = models.CharField(max_length=64)
    domain = models.CharField(max_length=128)
    twitter = models.CharField(max_length=16, **default_null_blank)

    class Meta:
        db_table = 'qux_seo_site'
        verbose_name = 'Site Data'
        verbose_name_plural = 'Site Data'


class SEOPage(SEOModel):
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    canonical = models.CharField(max_length=255, unique=True)
    page_name = models.CharField(max_length=64, **default_null_blank)
    page_title = models.CharField(max_length=256, **default_null_blank)
    description = models.CharField(max_length=512, **default_null_blank)
    keywords = models.CharField(max_length=512, **default_null_blank)

    class Meta:
        db_table = 'qux_seo_page'
        verbose_name = 'Page Data'
        verbose_name_plural = 'Page Data'
