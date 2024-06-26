from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.contrib.auth.views import PasswordResetCompleteView
from django.contrib.auth.views import PasswordResetConfirmView
from django.contrib.auth.views import PasswordResetDoneView
from django.contrib.auth.views import PasswordResetView
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes
from django.views.generic import TemplateView
from django.views.generic import View

try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_str as force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.contrib.auth.models import User

from qux.seo.mixin import SEOMixin
from ..tokens import account_activation_token

from ..forms import (
    ChangePasswordForm,
    CustomAuthenticationForm,
    CustomPasswordResetForm,
    CustomSetPasswordForm,
    SignupForm,
    BaseSignupForm,
)


User._meta.get_field("email")._unique = True


class QuxSignupView(View):
    """
    Signup form.
    """

    show_username_signup = getattr(settings, "SHOW_USERNAME_SIGNUP", None)
    form_class = SignupForm if show_username_signup else BaseSignupForm
    activate_user = False

    def post(self, request):
        """
        POST method for Signup form.
        """
        form = self.form_class(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = self.activate_user
            if not self.show_username_signup:
                user.username = user.email
                counter = 1
                while User.objects.filter(username=user.username).exists():
                    user.username = user.username + str(counter)
                    counter += 1

            user.save()
            # current_site = get_current_site(request)
            mail_subject = "Activate your account."

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = account_activation_token.make_token(user)
            domain = request.build_absolute_uri("/")[:-1]
            activate_url = reverse(
                "qux_auth:activate", kwargs={"uidb64": uid, "token": token}
            )
            data = {
                "user": user,
                # 'domain': current_site.domain,
                "domain": domain,
                "uid": uid,
                "token": token,
                "activate_url": domain + activate_url,
            }
            message = render_to_string("acc_active_email.html", data)
            to_email = form.cleaned_data.get("email")
            email = EmailMessage(mail_subject, message, to=[to_email])
            email.content_subtype = "html"
            email.send()

            data = {
                "title": "Verify account",
                "messages": [
                    "We have sent an account verification email to <b>{}</b> to complete your registration.".format(
                        to_email
                    ),
                    # 'Check the <b>spam</b> folder if you do not see the email within a few minutes of the request.'
                ],
            }

            return render(request, "message.html", data)

        else:
            errors = form.errors.as_data()

            error_messages = []
            for field, field_errors in errors.items():
                for error in field_errors:
                    message = (
                        error.message % error.params if error.params else error.message
                    )
                    error_messages.append(message)

            data = {
                "title": "Invalid credentials.",
                "messages": error_messages,
            }
            return render(request, "message.html", data)

    def get(self, request):
        """
        GET method for Signup form.
        """
        form = self.form_class()

        if settings.BOOTSTRAP == "bs4":
            return render(request, "signup.html", {"form": form})
        elif settings.BOOTSTRAP == "bs5":
            return render(request, "bs5/signup.html", {"form": form})
        else:
            return render(request, "signup.html", {"form": form})


class QuxActivateView(View):
    """
    Activate account.
    """

    def get(self, request, uidb64, token):
        """
        GET method to activate a user account.
        """
        try:
            uid = force_text(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        if user is not None and account_activation_token.check_token(user, token):
            user.is_active = True
            user.save()
            login(request, user)
            data = {
                "title": "Account verified",
                "messages": [
                    '<a style="color:red" href="/">Click here<a/> to continue to your account.'
                ],
            }
            return render(request, "message.html", data)
        else:
            data = {
                "title": "Invalid URL",
                "messages": [
                    "Activation link is invalid!",
                ],
            }
            return render(request, "message.html", data)


class QuxLoginView(SEOMixin, LoginView):
    """
    Login View.
    """

    form_class = CustomAuthenticationForm
    template_name = (
        "bs5/login.html"
        if getattr(settings, "BOOTSTRAP", "bs4") == "bs5"
        else "login.html"
    )
    canonical_url = "/login/"
    extra_context = {
        "submit_btn_text": "Login",
        "base_template": getattr(settings, "ROOT_TEMPLATE", "_blank.html"),
    }

    # show a generic message on login failure
    def form_invalid(self, form) -> HttpResponse:
        messages.error(self.request, "Could not login, invalid credentials!!")
        return super().form_invalid(form)


class QuxChangePasswordView(SEOMixin, TemplateView):
    form_class = ChangePasswordForm
    template_name = (
        "bs5/change-password.html"
        if getattr(settings, "BOOTSTRAP", "bs4") == "bs5"
        else "change-password.html"
    )
    extra_context = {
        "submit_btn_text": "Change Password",
        "base_template": getattr(settings, "ROOT_TEMPLATE", "_blank.html"),
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
            user.set_password(form.cleaned_data.get("new_password"))
            user.save()
            messages.success(request, "Password changed successfully")
            return redirect("/")
        return render(request, self.template_name, context=dict(form=form))


class QuxPasswordResetView(SEOMixin, PasswordResetView):
    form_class = CustomPasswordResetForm
    template_name = (
        "bs5/password_reset_form.html"
        if getattr(settings, "BOOTSTRAP", "bs4") == "bs5"
        else "password_reset_form.html"
    )
    email_template_name = "password_reset_email.html"
    html_email_template_name = "password_reset_email.html"
    canonical_url = "/password-reset/"
    success_url = reverse_lazy("qux_auth:password_reset_done")
    extra_context = {
        "title": "Reset password",
        "submit_btn_text": "Password Reset",
        "base_template": getattr(settings, "ROOT_TEMPLATE", "_blank.html"),
    }


class QuxPasswordResetDoneView(SEOMixin, PasswordResetDoneView):
    template_name = "password_reset_done.html"
    extra_context = {
        "title": "Reset password",
        "base_template": getattr(settings, "ROOT_TEMPLATE", "_blank.html"),
    }


class QuxPasswordResetConfirmView(PasswordResetConfirmView):
    form_class = CustomSetPasswordForm
    template_name = (
        "bs5/password_reset_form.html"
        if getattr(settings, "BOOTSTRAP", "bs4") == "bs5"
        else "password_reset_form.html"
    )
    success_url = reverse_lazy("qux_auth:password_reset_complete")
    extra_context = {
        "title": f"Change password",
        "submit_btn_text": "Change Password",
        "base_template": getattr(settings, "ROOT_TEMPLATE", "_blank.html"),
    }


class QuxPasswordResetCompleteView(PasswordResetCompleteView):

    template_name = "password_reset_complete.html"
    extra_context = {
        "title": "Password changed successfully",
        "base_template": getattr(settings, "ROOT_TEMPLATE", "_blank.html"),
    }


def logout_request(request):
    """
    Function based logout view.
    """
    logout(request)
    messages.info(request, "Logged out successfully!")
    return redirect("/")


def login_request(request):
    """
    Function based login view.
    """
    next_path = request.GET.get("next")
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    if request.method == "POST":
        form = AuthenticationForm(request=request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"You are now logged in as {username}")
                redirect_to = settings.LOGIN_REDIRECT_URL
                if next_path:
                    redirect_to = next_path
                return redirect(redirect_to)

            messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    form = CustomAuthenticationForm()
    data = {
        # "canonical": reverse('qux_auth:login'),
        "form": form,
    }
    return render(request, "login.html", data)
