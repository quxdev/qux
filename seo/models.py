from django.db import models
from django.contrib.sites.models import Site

from qux.models import QuxModel, default_null_blank


class SEOModel(QuxModel):
    class Meta:
        abstract = True


class SEOSite(SEOModel):
    site = models.OneToOneField(Site, on_delete=models.CASCADE)
    name = models.CharField(max_length=64)
    title = models.CharField(max_length=64)
    domain = models.CharField(max_length=128)
    twitter = models.CharField(max_length=16, **default_null_blank)

    class Meta:
        db_table = "qux_seo_site"
        verbose_name = "Site Data"
        verbose_name_plural = "Site Data"

    def __str__(self):
        return self.name


class SEOPage(SEOModel):
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    canonical = models.CharField(max_length=255)
    page_name = models.CharField(max_length=64, **default_null_blank)
    page_title = models.CharField(max_length=256, **default_null_blank)
    description = models.CharField(max_length=512, **default_null_blank)
    keywords = models.CharField(max_length=512, **default_null_blank)

    class Meta:
        db_table = "qux_seo_page"
        verbose_name = "Page Data"
        verbose_name_plural = "Page Data"
        constraints = [
            models.UniqueConstraint(
                fields=["site", "canonical"], name="unique_site_canonical"
            ),
        ]

    def __str__(self):
        return f"{self.site.domain}{self.canonical}"


# ---------------------------------------------------------------------------
# SEO Audit models — store results of automated SEO scans
# ---------------------------------------------------------------------------

AUDIT_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("running", "Running"),
    ("completed", "Completed"),
    ("failed", "Failed"),
]


class SEOAudit(QuxModel):
    """A single audit run for a website."""

    domain = models.CharField(max_length=255, db_index=True)
    status = models.CharField(
        max_length=16, choices=AUDIT_STATUS_CHOICES, default="pending"
    )
    dtm_audited = models.DateTimeField(**default_null_blank)
    total_urls = models.IntegerField(default=0)
    total_errors = models.IntegerField(default=0)
    total_warnings = models.IntegerField(default=0)

    class Meta:
        db_table = "qux_seo_audit"
        verbose_name = "SEO Audit"
        verbose_name_plural = "SEO Audits"
        ordering = ["-dtm_created"]

    def __str__(self):
        return f"{self.domain} ({self.dtm_created:%Y-%m-%d %H:%M})"


class SEOAuditURL(QuxModel):
    """Results for a single URL within an audit run."""

    audit = models.ForeignKey(
        SEOAudit, on_delete=models.CASCADE, related_name="results"
    )
    url = models.CharField(max_length=2048)
    status_code = models.IntegerField(**default_null_blank)

    # Extracted SEO tag values
    title = models.CharField(max_length=512, **default_null_blank)
    meta_description = models.TextField(**default_null_blank)
    canonical = models.CharField(max_length=2048, **default_null_blank)
    og_url = models.CharField(max_length=2048, **default_null_blank)
    og_title = models.CharField(max_length=512, **default_null_blank)
    og_description = models.TextField(**default_null_blank)
    og_image = models.CharField(max_length=2048, **default_null_blank)
    og_site_name = models.CharField(max_length=256, **default_null_blank)
    twitter_card = models.CharField(max_length=64, **default_null_blank)
    twitter_title = models.CharField(max_length=512, **default_null_blank)
    twitter_description = models.TextField(**default_null_blank)
    twitter_image = models.CharField(max_length=2048, **default_null_blank)

    # Validation results
    errors = models.JSONField(default=list, blank=True)
    warnings = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "qux_seo_audit_url"
        verbose_name = "SEO Audit URL"
        verbose_name_plural = "SEO Audit URLs"

    def __str__(self):
        return self.url

    @property
    def has_errors(self):
        return len(self.errors) > 0

    @property
    def has_warnings(self):
        return len(self.warnings) > 0
