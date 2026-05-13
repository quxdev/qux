import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import cast

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    get_user_model,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LoginView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_bytes, force_str
from django.utils.http import base36_to_int, urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.timezone import now as django_now
from django.views.generic import TemplateView, View

from qux.seo.mixin import SEOMixin
from qux.telemetry import EVENTS, emit
from qux.telemetry import events as qux_events

from ..forms import (
    BaseSignupForm,
    ChangePasswordForm,
    CompleteProfileForm,
    CustomAuthenticationForm,
    CustomPasswordResetForm,
    CustomSetPasswordForm,
    MagicLinkRequestForm,
    SignupForm,
)
from ..tokens import account_activation_token, magic_link_token

logger = logging.getLogger("qux")
User = get_user_model()


class QuxSignupView(View):
    """
    Signup form.
    """

    show_username_signup = getattr(settings, "SHOW_USERNAME_SIGNUP", None)
    template_name = (
        "bs5/signup.html" if getattr(settings, "BOOTSTRAP", "bs4") == "bs5" else "signup.html"
    )
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
                base_username = user.email
                user.username = base_username
                counter = 1
                while User.objects.filter(username=user.username).exists():
                    user.username = f"{base_username}{counter}"
                    counter += 1

            user.save()

            qux_events.auth_signup()

            to_email = send_signup_verification_email(request, user, form)

            data = {
                "title": "Verify account",
                "messages": [
                    (
                        f"We have sent an account verification email to <b>{to_email}</b> "
                        "to complete your registration."
                    ),
                    (
                        "Check the <b>spam</b> folder if you do not see the email within a "
                        "few minutes of the request."
                    ),
                ],
            }

            return render(request, "message.html", data)

        errors_obj = getattr(form, "errors", None)

        error_messages: list[str] = []
        if errors_obj:
            for field_errors in errors_obj.values():
                for message in field_errors:
                    if message:
                        error_messages.append(str(message))

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
        context = {"form": form}
        return render(request, template_name=self.template_name, context=context)


def send_signup_verification_email(request, user, form):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = account_activation_token.make_token(user)
    domain = request.build_absolute_uri("/")[:-1]
    activate_url = reverse("qux_auth:activate", kwargs={"uidb64": uid, "token": token})
    full_url = domain + activate_url
    to_email = form.cleaned_data.get("email")
    send_mail(
        subject="Activate your account.",
        message=f"Activate your account: {full_url}",
        from_email=None,  # uses settings.DEFAULT_FROM_EMAIL
        recipient_list=[to_email],
        html_message=render_to_string(
            "acc_active_email.html",
            {
                "user": user,
                "domain": domain,
                "uid": uid,
                "token": token,
                "activate_url": full_url,
            },
        ),
    )
    return to_email


class QuxActivateView(View):
    """
    Activate account.
    """

    @staticmethod
    def get(request, uidb64, token):
        """
        GET method to activate a user account.
        """
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, ObjectDoesNotExist):
            user = None
        if user is not None and account_activation_token.check_token(user, token):
            user.is_active = True
            user.save()
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            data = {
                "title": "Account verified",
                "messages": [
                    '<a style="color:red" href="/">Click here</a> to continue to your account.'
                ],
            }
            return render(request, "message.html", data)

        # else
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
        "bs5/login.html" if getattr(settings, "BOOTSTRAP", "bs4") == "bs5" else "login.html"
    )
    canonical_url = "/login/"
    extra_context = {
        "submit_btn_text": "Login",
        "base_template": getattr(settings, "ROOT_TEMPLATE", "_blank.html"),
    }

    # show a generic message on login failure
    def form_invalid(self, form) -> HttpResponse:
        messages.error(self.request, "Could not login, invalid credentials!!")
        qux_events.auth_login_failed(reason=_login_failure_reason(form))
        return super().form_invalid(form)


def _login_failure_reason(form) -> str:
    """Best-effort categorization of why a login failed.

    Maps Django's CustomAuthenticationForm error codes to a small enum so the
    telemetry payload stays bounded-cardinality (`bad_password`, `unknown_user`,
    `inactive`, `locked`, or `unknown`). Operators alert on the parent event;
    reason is for triage drill-down.
    """
    errors = getattr(form, "errors", None)
    if not errors:
        return "unknown"
    text = (
        " ".join(str(e) for e in errors.as_data().values()).lower()
        if hasattr(errors, "as_data")
        else ""
    )
    if "inactive" in text:
        return "inactive"
    if "locked" in text:
        return "locked"
    # Django's default invalid-credentials message covers both unknown user and
    # bad password without distinguishing — by design (don't leak which one).
    # We fold them into one bucket.
    return "bad_credentials"


class QuxChangePasswordView(LoginRequiredMixin, SEOMixin, TemplateView):
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
        ctx["form"] = self.form_class(user=self.request.user)
        return ctx

    def post(self, request):
        form = self.form_class(data=request.POST, user=request.user)
        if form.is_valid():
            user = request.user
            user.set_password(form.cleaned_data.get("new_password"))
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password changed successfully")
            return redirect("/")
        return render(request, cast(str, self.template_name), context={"form": form})


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

    def form_valid(self, form):
        emit(EVENTS.AUTH_PASSWORD_RESET_REQUESTED, ok=True)
        return super().form_valid(form)


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
        "title": "Change password",
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


class MagicLinkRequestView(SEOMixin, TemplateView):
    template_name = (
        "bs5/magic_link_request.html"
        if getattr(settings, "BOOTSTRAP", "bs4") == "bs5"
        else "magic_link_request.html"
    )
    extra_context = {
        "title": "Magic link",
        "submit_btn_text": "Send magic link",
        "base_template": getattr(settings, "ROOT_TEMPLATE", "_blank.html"),
    }

    def dispatch(self, request, *args, **kwargs):
        if not getattr(settings, "USE_MAGIC_LINK", False):
            raise Http404("Magic link sign-in is disabled.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if "form" not in ctx:
            initial = {"render_ts": time.time()}
            prefill_email = self.request.GET.get("email")
            if prefill_email:
                initial["email"] = prefill_email
            ctx["form"] = MagicLinkRequestForm(initial=initial)
        return ctx

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(settings.LOGIN_REDIRECT_URL)
        return super().get(request)

    def _get_fingerprint(self, request):
        ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get(
            "REMOTE_ADDR", ""
        )
        ua = request.META.get("HTTP_USER_AGENT", "")
        return hashlib.sha256(f"{ip}:{ua}".encode()).hexdigest()

    def _is_rate_limited(self, request, email):
        """Returns (is_limited, is_email_limit)"""
        fingerprint = self._get_fingerprint(request)
        fp_key = f"qux_auth_ml_fp:{fingerprint}"
        email_key = f"qux_auth_ml_email:{email}"

        fp_limit = getattr(settings, "MAGIC_LINK_RATE_LIMIT", 10)
        email_limit = getattr(settings, "MAGIC_LINK_EMAIL_LIMIT", 5)
        period = getattr(settings, "MAGIC_LINK_RATE_PERIOD", 3600)

        fp_count = cache.get(fp_key, 0)
        if fp_count >= fp_limit:
            return True, False

        email_count = cache.get(email_key, 0)
        if email_count >= email_limit:
            return True, True

        cache.set(fp_key, fp_count + 1, period)
        cache.set(email_key, email_count + 1, period)
        return False, False

    def _get_expiration_time_str(self):
        hours = int(settings.PASSWORD_RESET_TIMEOUT / 3600)
        minutes = int(settings.PASSWORD_RESET_TIMEOUT % 3600 / 60)
        expiration_time = ""
        if hours > 0:
            expiration_time = f"{hours} hour{'' if hours == 1 else 's'}"
        if minutes > 0:
            expiration_time += (
                f"{' and ' if hours > 0 else ''}" + f"{minutes} minute{'' if minutes == 1 else 's'}"
            )
        return expiration_time

    def _error_response(self, request, title, error_messages):
        return render(
            request,
            (
                "bs5/message.html"
                if getattr(settings, "BOOTSTRAP", "bs4") == "bs5"
                else "message.html"
            ),
            {
                "title": title,
                "messages": error_messages,
                "show_login_link": True,
            },
        )

    def _success_response(self, request, email):
        expiration_time = self._get_expiration_time_str()
        return render(
            request,
            "message.html",
            {
                "title": "Check your email",
                "messages": [
                    f"We sent a magic link to <b>{email}</b>. It expires in {expiration_time}.",
                    "Check spam if you do not see it in a couple of minutes.",
                ],
                "show_login_link": True,
            },
        )

    def post(self, request):
        form = MagicLinkRequestForm(request.POST)
        if not form.is_valid():
            return self.render_to_response({"form": form})

        email = form.cleaned_data["email"].strip().lower()
        render_ts = form.cleaned_data.get("render_ts")
        now = time.time()

        # 1. Honeypot check
        if form.cleaned_data.get("phone_number"):
            logger.warning(
                "Bot detected via honeypot (phone_number field): %s from %s",
                email,
                request.META.get("REMOTE_ADDR"),
            )
            qux_events.auth_magic_link_refused(reason="bot_check")
            return self._success_response(request, email)

        # 2. Timing check (Silent)
        min_time = getattr(settings, "MAGIC_LINK_MIN_SUBMIT_TIME", 2)
        if render_ts and (now - render_ts) < min_time:
            logger.warning("Bot detected via timing: %s submitted in %.2fs", email, now - render_ts)
            qux_events.auth_magic_link_refused(reason="bot_check")
            return self._success_response(request, email)

        # 3. Domain check
        blocked_domains = getattr(settings, "BLOCKED_DOMAIN_FOR_MAGIC_LINK", [])
        email_domain = email.split("@")[-1] if "@" in email else ""
        if email_domain in blocked_domains:
            logger.warning(
                "Domain blocked for magic link: %s from %s",
                email,
                request.META.get("REMOTE_ADDR"),
            )
            qux_events.auth_magic_link_refused(reason="blocked_domain")
            error_msg = "Magic links are not available for personal email addresses."
            return self._error_response(request, "Please use your work email", [error_msg])

        # 4. Rate limiting (Transparent to users)
        limited, is_email_limit = self._is_rate_limited(request, email)
        if limited:
            qux_events.auth_magic_link_refused(reason="rate_limit")
            error_msg = (
                "You have requested too many magic links. Please wait an hour and try again."
            )
            return self._error_response(request, "Too many requests", [error_msg])

        try:
            user = User.objects.get(email=email)
        except ObjectDoesNotExist:
            base_username = email
            candidate_username = base_username
            suffix = 1
            while User.objects.filter(username=candidate_username).exists():
                candidate_username = f"{base_username}{suffix}"
                suffix += 1
            user = User.objects.create(
                username=candidate_username,
                email=email,
                is_active=True,
            )

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = magic_link_token.make_token(user)
        domain = request.build_absolute_uri("/")[:-1]
        next_path = request.GET.get("next") or request.POST.get("next")
        callback_kwargs = {"uidb64": uid, "token": token}
        callback_url = reverse("qux_auth:login_link", kwargs=callback_kwargs)
        if next_path:
            callback_url = f"{callback_url}?next={next_path}"

        expiration_time = self._get_expiration_time_str()
        magic_link_url = domain + callback_url
        send_mail(
            subject="Your magic link",
            message=f"Sign in: {magic_link_url} (expires in {expiration_time}).",
            from_email=None,  # uses settings.DEFAULT_FROM_EMAIL
            recipient_list=[email],
            html_message=render_to_string(
                "magic_link_email.html",
                {
                    "user": user,
                    "domain": domain,
                    "magic_link_url": magic_link_url,
                    "expiration_time": expiration_time,
                },
            ),
        )

        qux_events.auth_magic_link_requested()
        return self._success_response(request, email)


class MagicLinkLoginView(SEOMixin, View):
    @staticmethod
    def _get_token_status(user: User | None, token: str) -> str:
        """Return one of: "valid", "expired", or "invalid" using public APIs."""
        if not user or not token:
            return "invalid"

        # Extract timestamp from token
        try:
            ts_b36, _ = token.split("-")
            ts = base36_to_int(ts_b36)
        except (ValueError, TypeError):
            return "invalid"

        # Determine expiry strictly by timestamp window. The 2001-01-01 anchor
        # matches Django's PasswordResetTokenGenerator timestamp encoding.
        anchor = datetime(2001, 1, 1, tzinfo=timezone.utc)
        now_seconds = int((django_now() - anchor).total_seconds())
        if (now_seconds - ts) > settings.PASSWORD_RESET_TIMEOUT:
            return "expired"

        # Within window → rely on Django's public check_token for validity
        return "valid" if magic_link_token.check_token(user, token) else "invalid"

    @staticmethod
    def _log_magic_link_event(
        request,
        *,
        status: str,
        user: User | None,
        reason: str | None = None,
    ) -> None:
        """Log a magic link login event for monitoring and counting."""
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip = (
            forwarded_for.split(",")[0].strip()
            if forwarded_for
            else request.META.get("REMOTE_ADDR", "")
        )
        ua = request.META.get("HTTP_USER_AGENT", "")
        next_path = request.GET.get("next")
        user_id = getattr(user, "id", None)
        email = getattr(user, "email", "")
        logger.info(
            "magic_link_login status=%s reason=%s user_id=%s email=%s ip=%s ua=%s next=%s",
            status,
            reason or "",
            user_id,
            email,
            ip,
            ua,
            next_path,
        )

    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, ObjectDoesNotExist):
            user = None

        status = self._get_token_status(user, token)

        if status != "valid":
            next_path = request.GET.get("next")
            magic_link_url = reverse("qux_auth:magic_link")
            if next_path:
                magic_link_url = f"{magic_link_url}?next={next_path}"
            # Pre-fill email if we could resolve the user
            if user and user.email:
                sep = "&" if "?" in magic_link_url else "?"
                magic_link_url = f"{magic_link_url}{sep}email={user.email}"
            title = "Link expired" if status == "expired" else "Invalid link"
            reason = (
                "This magic link has expired."
                if status == "expired"
                else "This magic link is invalid. Please request a new one."
            )
            self._log_magic_link_event(
                request,
                status=status,
                user=user,
                reason="expired" if status == "expired" else "invalid",
            )
            return render(
                request,
                "message.html",
                {
                    "title": title,
                    "messages": [
                        reason,
                        (
                            f'<a class="btn btn-outline-primary btn-block w-100 py-2 mt-3" '
                            f'href="{magic_link_url}">Get a new magic link</a>'
                        ),
                    ],
                },
            )
        # Proceed to login directly on GET (fast one-click flow)
        next_path = request.GET.get("next")
        login(request, user)
        self._log_magic_link_event(request, status="success", user=user)
        emit(EVENTS.AUTH_MAGIC_LINK_CONSUMED, ok=True)
        # If first-time login (no first_name/last_name), route to complete-profile
        if (
            user
            and hasattr(settings, "SHOW_COMPLETE_PROFILE_FORM")
            and settings.SHOW_COMPLETE_PROFILE_FORM
            and not user.first_name
            and not user.last_name
        ):
            url = reverse("qux_auth:update_profile")
            if next_path:
                url = f"{url}?next={next_path}"
            return redirect(url)

        redirect_to = next_path or settings.LOGIN_REDIRECT_URL
        return redirect(redirect_to)


class CompleteProfileView(LoginRequiredMixin, SEOMixin, TemplateView):
    template_name = (
        "bs5/complete_profile.html"
        if getattr(settings, "BOOTSTRAP", "bs4") == "bs5"
        else "complete_profile.html"
    )
    extra_context = {
        "title": "Update your profile",
        "submit_btn_text": "Save and continue",
        "base_template": getattr(settings, "ROOT_TEMPLATE", "_blank.html"),
    }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = CompleteProfileForm(instance=self.request.user)
        return ctx

    def get(self, request):
        if (
            hasattr(settings, "SHOW_COMPLETE_PROFILE_FORM")
            and settings.SHOW_COMPLETE_PROFILE_FORM
            and request.user.first_name
            and request.user.last_name
        ):
            redirect_to = request.GET.get("next") or settings.LOGIN_REDIRECT_URL
            return redirect(redirect_to)
        return super().get(request)

    def post(self, request):
        form = CompleteProfileForm(request.POST, instance=request.user)
        if not form.is_valid():
            return self.render_to_response({"form": form})
        form.save()
        redirect_to = request.GET.get("next") or settings.LOGIN_REDIRECT_URL
        return redirect(redirect_to)


class QuxSetPasswordView(LoginRequiredMixin, SEOMixin, TemplateView):
    template_name = (
        "bs5/set_password.html"
        if getattr(settings, "BOOTSTRAP", "bs4") == "bs5"
        else "set_password.html"
    )
    extra_context = {
        "form_title": "Set your password",
        "submit_btn_text": "Save and continue",
        "base_template": getattr(settings, "ROOT_TEMPLATE", "_blank.html"),
    }

    def get(self, request):
        # If user already has a password, redirect them
        if request.user.password:
            redirect_to = request.GET.get("next") or settings.LOGIN_REDIRECT_URL
            return redirect(redirect_to)
        return super().get(request)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = CustomSetPasswordForm(self.request.user)
        return ctx

    def post(self, request):
        form = CustomSetPasswordForm(request.user, request.POST)
        if not form.is_valid():
            return self.render_to_response({"form": form})

        # Set the new password
        user = request.user
        user.set_password(form.cleaned_data.get("new_password1"))
        user.save()

        messages.success(request, "Password set successfully!")

        emit(EVENTS.AUTH_PASSWORD_RESET_COMPLETED, ok=True)

        # Redirect to next page or default
        redirect_to = request.GET.get("next") or settings.LOGIN_REDIRECT_URL
        return redirect(redirect_to)
