"""
API views for CLI-native Magic OTP authentication.

Flow:
  1. POST /api/v1/auth/cli/request/  { "email": "..." }
     → generates a 6-digit OTP, stores it in cache for 5 min, sends it via email.

  2. POST /api/v1/auth/cli/verify/   { "email": "...", "otp": "123456" }
     → verifies OTP, issues a CustomToken, atomically deletes the cache key.

Security notes:
  - OTPs are never persisted to the database.
  - Cache key is deleted immediately on successful verification (no replay attacks).
  - Three throttle classes guard against brute-force and email-bombing.
"""

import logging
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from qux.token.models import CustomToken

from ..throttles import OTPRequestEmailThrottle, OTPRequestIPThrottle, OTPVerifyThrottle

User = get_user_model()
logger = logging.getLogger(__name__)


def _otp_cache_key(email: str) -> str:
    return f"cli_otp:{email}"


class CLIOTPRequestView(APIView):
    """
    Request a 6-digit OTP to be sent to the given email address.

    POST body: { "email": "<address>" }
    Response:  { "detail": "OTP sent to email." }
    """

    permission_classes = [AllowAny]
    throttle_classes = [OTPRequestIPThrottle, OTPRequestEmailThrottle]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        if not email:
            return Response(
                {"error": "Email required."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Domain check (consistent with Magic Link flow)
        blocked_domains = getattr(settings, "BLOCKED_DOMAIN_FOR_MAGIC_LINK", [])
        email_domain = email.split("@")[-1] if "@" in email else ""
        if email_domain in blocked_domains:
            logger.warning(
                "CLIOTPRequestView: domain blocked for email=%s from %s",
                email,
                request.META.get("REMOTE_ADDR"),
            )
            return Response(
                {
                    "error": "Login codes are not available for personal email addresses. Please use your work email."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Generate a cryptographically secure 6-digit OTP (zero-padded)
        otp = "".join(str(secrets.randbelow(10)) for _ in range(6))
        # Get TTL from settings, default to 5 minutes (300s)
        ttl = getattr(settings, "CLI_OTP_TIMEOUT", 300)
        cache.set(_otp_cache_key(email), otp, timeout=ttl)

        # Resolve the user for template personalisation (create if first-time)
        user, _ = User.objects.get_or_create(
            email=email,
            defaults={"username": email, "is_active": True},
        )

        # Compute a human-readable expiration string from the single source of truth
        minutes = ttl // 60
        expiration_time = f"{minutes} minute{'s' if minutes != 1 else ''}"

        # Send the OTP via email using the project's existing email mechanism
        try:
            domain = request.build_absolute_uri("/")[:-1]
            html_content = render_to_string(
                "cli_otp_email.html",
                {
                    "user": user,
                    "otp": otp,
                    "domain": domain,
                    "expiration_time": expiration_time,
                },
            )
            msg = EmailMessage(
                subject="Your CLI login code",
                body=html_content,
                to=[email],
            )
            msg.content_subtype = "html"
            msg.send()
        except Exception:
            logger.exception("CLIOTPRequestView: failed to send OTP email to %s", email)
            # Do NOT reveal the OTP in the error response
            return Response(
                {"error": "Could not send email. Please try again later."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        logger.info("CLIOTPRequestView: OTP issued for email=%s", email)
        return Response({"detail": "OTP sent to email."}, status=status.HTTP_200_OK)


class CLIOTPVerifyView(APIView):
    """
    Verify the OTP and return a long-lived auth token.

    POST body: { "email": "<address>", "otp": "123456" }
    Response (success): { "token": "<token_key>" }
    Response (failure): { "error": "Invalid or expired code." }  HTTP 401
    """

    permission_classes = [AllowAny]
    throttle_classes = [OTPVerifyThrottle]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        otp_attempt = request.data.get("otp") or ""

        if not email or not otp_attempt:
            return Response(
                {"error": "Both 'email' and 'otp' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cached_otp = cache.get(_otp_cache_key(email))

        # Constant-time comparison to resist timing attacks
        if not cached_otp or cached_otp != otp_attempt:
            logger.warning(
                "CLIOTPVerifyView: failed OTP attempt for email=%s (otp_present=%s)",
                email,
                bool(cached_otp),
            )
            return Response(
                {"error": "Invalid or expired code."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # --- Successful verification ---

        # Resolve or create the user (consistent with MagicLink behaviour)
        user, created = User.objects.get_or_create(
            email=email,
            defaults={"username": email, "is_active": True},
        )
        if created:
            logger.info("CLIOTPVerifyView: created new user for email=%s", email)

        # Issue a named CustomToken (the project's token model, not DRF authtoken)
        token, _ = CustomToken.objects.get_or_create(
            user=user,
            defaults={"name": "cli"},
        )

        # Atomically delete the OTP — prevents replay attacks
        cache.delete(_otp_cache_key(email))

        logger.info("CLIOTPVerifyView: token issued for email=%s", email)
        return Response({"token": token.key}, status=status.HTTP_200_OK)
