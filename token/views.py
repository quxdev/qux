from .forms import *

# from core.mixin import DjangoViewTrackingMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import UpdateView
from django.conf import settings


from qux.seo.mixin import SEOMixin

from .models import *


class CustomTokenListView(SEOMixin, LoginRequiredMixin, ListView):
    model = CustomToken
    queryset = CustomToken.objects.all()
    template_name = "token_list.html"
    fields = [
        "name",
    ]
    extra_context = {
        "breadcrumbs": ["API KEY"],
        "base_template": getattr(settings, "ROOT_TEMPLATE", "_blank.html"),
    }

    def get_queryset(self):
        # should not use self.queryset directly as list doesn't updated
        queryset = CustomToken.objects.all()
        queryset = queryset.filter(user=self.request.user)

        return queryset


class CustomTokenDetailView(SEOMixin, LoginRequiredMixin, DetailView):
    model = CustomToken
    template_name = "token_detail.html"
    extra_context = {
        "breadcrumbs": ["API KEY", "Detail"],
        "base_template": getattr(settings, "ROOT_TEMPLATE", "_blank.html"),
    }

    def get_object(self, *args, **kwargs):
        key = self.kwargs.get("key", None)

        obj = None
        if key:
            obj = self.model.objects.filter(user=self.request.user, key=key).first()

        if not obj:
            raise Http404

        return obj


class CustomTokenCreateView(SEOMixin, LoginRequiredMixin, CreateView):
    model = CustomToken
    form_class = CustomTokenForm
    template_name = "bs5/token_create.html" if getattr(settings, "BOOTSTRAP", "bs4") == "bs5" else "token_create.html"
    # fields = ['title', 'slug', 'body', 'citation', 'tags', 'is_draft', 'is_private', ]
    extra_context = {
        "breadcrumbs": ["API KEY", "New"],
        "base_template": getattr(settings, "ROOT_TEMPLATE", "_blank.html"),
    }

    def form_valid(self, form):
        form.save(self.request.user)
        return super(CustomTokenCreateView, self).form_valid(form)

    def get_success_url(self, *args, **kwargs):
        # return HttpResponseRedirect(reverse('token:home', kwargs={'key': self.object.key}))
        return reverse("qux_token:key", kwargs={"key": self.object.key})


class CustomTokenUpdateView(SEOMixin, LoginRequiredMixin, UpdateView):
    model = CustomToken
    form_class = CustomTokenForm
    template_name = "bs5/token_update.html" if getattr(settings, "BOOTSTRAP", "bs4") == "bs5" else "token_update.html"
    extra_context = {"base_template": getattr(settings, "ROOT_TEMPLATE", "_blank.html")}

    @staticmethod
    def get_success_url(*args, **kwargs):
        return reverse("qux_token:home")


class CustomTokenDeleteView(SEOMixin, LoginRequiredMixin, DeleteView):
    model = CustomToken
    extra_context = {"base_template": getattr(settings, "ROOT_TEMPLATE", "_blank.html")}

    @staticmethod
    def get_success_url(**kwargs):
        return reverse("qux_token:home")
