import logging

from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.sites.shortcuts import get_current_site
from django.views.generic.base import ContextMixin

from .models import SEOSite, SEOPage

logger = logging.getLogger(__name__)


class SEOMixin(ContextMixin):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        site = self.getsite()
        if not site:
            return context

        seocontext = self.seocontext(site)
        if seocontext:
            context["meta"] = seocontext

        return context

    def getsite(self):
        # Prefer the site already resolved by middleware or mixin setup().
        if hasattr(self, "site") and self.site:
            return self.site

        if settings.SITE_ID == 1 and "sitename" in self.kwargs:
            sitename = self.kwargs["sitename"]
            site = Site.objects.filter(name=sitename).first()
        else:
            site = get_current_site(self.request)

        return site

    def seocontext(self, site: Site):
        siteobj = SEOSite.objects.get_or_none(site=site)
        if siteobj:
            result = siteobj.to_dict()
        else:
            logger.debug("SEOMixin.seocontext(SEOSite=None)")
            return {}

        url = getattr(self, "canonical_url", None)
        if url is None:
            path = self.request.get_full_path()
            url = path.split("?")[0]

        pageobj = SEOPage.objects.get_or_none(site=site, canonical=url)
        if pageobj:
            result = {**result, **pageobj.to_dict()}

        logger.debug(
            "SEOMixin.seocontext(SEOSite=%s, SEOPage=%s)",
            siteobj.id,
            pageobj.id if pageobj else None,
        )

        return result or None
