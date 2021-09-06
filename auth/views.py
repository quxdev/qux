from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth.views import PasswordResetDoneView
from django.contrib.auth.views import PasswordResetConfirmView
from django.contrib.auth.views import PasswordResetCompleteView
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from qux.seo.mixin import SEOMixin
from .forms import ChangePasswordForm
from .forms import CustomAuthenticationForm
from .forms import CustomPasswordResetForm
from .forms import CustomSetPasswordForm


# class HomeView(TemplateView):
#     template_name = 'home.html'
#     extra_context = {
#         "canonical": reverse('qux_auth:home')
#     }


class CoreLoginView(SEOMixin, LoginView):
    form_class = CustomAuthenticationForm
    template_name = 'login.html'
    canonical_url = '/login/'
    extra_context = {
        'submit_btn_text': 'Login'
    }


def logout_request(request):
    logout(request)
    # messages.info(request, "Logged out successfully!")
    return redirect("/")


def login_request(request):
    next_path = request.GET.get('next')
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    if request.method == 'POST':
        form = AuthenticationForm(request=request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                # messages.info(request, f"You are now logged in as {username}")
                redirect_to = settings.LOGIN_REDIRECT_URL
                if next_path:
                    redirect_to = next_path
                return redirect(redirect_to)
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    form = CustomAuthenticationForm()
    data = {
        # "canonical": reverse('qux_auth:login'),
        "form": form,
    }
    return render(request, 'login.html', data)


class ChangePasswordView(SEOMixin, TemplateView):
    form_class = ChangePasswordForm
    template_name = 'change-password.html'
    extra_context = {
        'submit_btn_text': 'Change Password'
    }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(dict(form=self.form_class(user=self.request.user)))
        return ctx

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        form = self.form_class(data=request.POST, user=request.user)
        if form.is_valid():
            user = request.user
            user.set_password(form.cleaned_data.get('new_password'))
            user.save()
            messages.success(request, "Password changed successfully")
        return render(request, self.template_name, context=dict(form=form))


class CorePasswordResetView(SEOMixin, PasswordResetView):
    form_class = CustomPasswordResetForm
    template_name = 'password_reset_form.html'
    email_template_name = 'password_reset_email.html'
    canonical_url = '/password-reset/'
    success_url = reverse_lazy('qux_auth:password_reset_done')
    extra_context = {
        'title': 'Reset password',
        'submit_btn_text': 'Password Reset'
    }


class CorePasswordResetDoneView(SEOMixin, PasswordResetDoneView):
    template_name = 'password_reset_done.html'
    extra_context = {
        'title': 'Reset password'
    }


class CorePasswordResetConfirmView(PasswordResetConfirmView):
    form_class = CustomSetPasswordForm
    template_name = 'password_reset_form.html'
    success_url = reverse_lazy('qux_auth:password_reset_complete')
    extra_context = {
        'title': f'Change password',
        'submit_btn_text': 'Change Password'
    }


class CorePasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'password_reset_complete.html'
    extra_context = {
        'title': 'Password changed successfully'
    }