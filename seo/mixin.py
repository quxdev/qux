import json
from .models import SEOSite, SEOPage
from django.contrib.sites.models import Site
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site


class SEOMixin:
    def get_context_data(self, **kwargs):
        print("SEOMixin.get_context_data()")

        context = super().get_context_data(**kwargs)

        site = self.getsite()
        print(f"SEOMixin.Site = {site.id}:{site}")
        if not site:
            return context

        seocontext = self.seocontext(site)
        if seocontext:
            context['meta'] = seocontext

        return context

    def getsite(self):
        if settings.SITE_ID == 1 and 'sitename' in self.kwargs:
            sitename = self.kwargs['sitename']
            site = Site.objects.filter(name=sitename).first()
        else:
            site = get_current_site(self.request)

        return site

    def seocontext(self, site: Site):
        siteobj = SEOSite.objects.get_or_none(site=site)
        if siteobj:
            prnstr = f"SEOMixin.seocontext(SEOSite={siteobj.id}"
            result = siteobj.to_dict()
        else:
            print(f"SEOMixin.seocontext(SEOSite=None)")
            result = {}
            return result

        if hasattr(self.__class__, 'canonical_url'):
            url = self.__class__.canonical_url
        else:
            path = self.request.get_full_path()
            url = path.split('?')[0]

        pageobj = SEOPage.objects.get_or_none(site=site, canonical=url)
        if pageobj:
            print(f"{prnstr}, SEOPage={pageobj.id})")
            result = {**result, **pageobj.to_dict()}
        else:
            print(f"{prnstr}, SEOPage=None)")

        if not result:
            result = None

        return result
