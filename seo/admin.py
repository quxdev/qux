from django.contrib import admin

from qux.admin import QuxModelAdmin
from .models import SEOSite, SEOPage


admin.site.register(SEOSite, QuxModelAdmin)

admin.site.register(SEOPage, QuxModelAdmin)
