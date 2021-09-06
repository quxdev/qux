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

from qux.seo.mixin import SEOMixin

from .models import *

# class CustomTokenAllowedMixin:
#     def dispatch(self, request, *args, **kwargs):
#         if request.user.is_superuser:
#             return super().dispatch(request, *args, **kwargs)

#         for confuser in request.user.ivruser_set.filter(ivr__config_type__api_allowed=True):
#             if confuser.isallowed_reports or confuser.is_admin or confuser.is_owner:
#                 return super().dispatch(request, *args, **kwargs)

#         return redirect('/')


class CustomTokenListView(SEOMixin, LoginRequiredMixin, ListView):
    model = CustomToken
    queryset = CustomToken.objects.all()
    template_name = 'token_list.html'
    fields = ['name', ]
    extra_context = {
        'breadcrumbs': ['API KEY'],
    }

    def get_queryset(self):
        queryset = CustomToken.objects.all()  # should not use self.queryset directly as list doesn't updated
        queryset = queryset.filter(user=self.request.user)

        # if not self.request.user.profile.is_paid_account():
        #     return queryset.none()

        return queryset


class CustomTokenDetailView(SEOMixin, LoginRequiredMixin, DetailView):
    model = CustomToken
    template_name = "token_detail.html"
    extra_context = {
        'breadcrumbs': ['API KEY', 'Detail'],
    }

    def get_object(self, *args, **kwargs):
        key = self.kwargs.get('key', None)

        obj = None
        if key:
            obj = self.model.objects.filter(user=self.request.user, key=key).first()

        if not obj:
            raise Http404

        return obj


class CustomTokenCreateView(SEOMixin, LoginRequiredMixin, CreateView):
    model = CustomToken
    form_class = CustomTokenForm
    template_name = 'token_create.html'
    # fields = ['title', 'slug', 'body', 'citation', 'tags', 'is_draft', 'is_private', ]
    extra_context = {
        'breadcrumbs': ['API KEY', 'New'],
    }

    def form_valid(self, form):
        form.save(self.request.user)
        return super(CustomTokenCreateView, self).form_valid(form)

    def get_success_url(self, *args, **kwargs):
        # return HttpResponseRedirect(reverse('token:home', kwargs={'key': self.object.key}))
        return reverse('qux_token:key', kwargs={'key': self.object.key})


class CustomTokenUpdateView(SEOMixin, LoginRequiredMixin, UpdateView):
    model = CustomToken
    form_class = CustomTokenForm
    template_name = "token_update.html"

    @staticmethod
    def get_success_url(*args, **kwargs):
        return reverse("qux_token:home")


class CustomTokenDeleteView(SEOMixin, LoginRequiredMixin, DeleteView): 
    # template_name = "token_delete.html"
    model = CustomToken
    # slug_field = 'name'

    # def delete(self, request, *args, **kwargs):
    #     name = self.kwargs['name']
    #
    #     tokens = CustomToken.objects.filter(name=name, user=self.request.user)
    #     if tokens:
    #         tokens.delete()
    #     else:
    #         raise Http404
    #
    #     return HttpResponseRedirect(reverse("token:home"))

    @staticmethod
    def get_success_url():
        return reverse("qux_token:home")
