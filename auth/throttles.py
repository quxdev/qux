"""
Throttle classes for CLI OTP authentication endpoints.
Rates are hardcoded here (not in settings) to keep config local to this module.
"""

from rest_framework.throttling import SimpleRateThrottle


class OTPRequestIPThrottle(SimpleRateThrottle):
    """Limit OTP request attempts per IP address to 10 per hour."""

    rate = "10/hour"

    def get_cache_key(self, request, view):
        return self.get_ident(request)


class OTPRequestEmailThrottle(SimpleRateThrottle):
    """Limit OTP request attempts per email address to 3 per hour."""

    rate = "3/hour"

    def get_cache_key(self, request, view):
        email = request.data.get("email")
        return f"throttle_email_request_{email}" if email else None


class OTPVerifyThrottle(SimpleRateThrottle):
    """Limit OTP verification attempts per email to 3 per minute."""

    rate = "3/minute"

    def get_cache_key(self, request, view):
        email = request.data.get("email")
        return f"throttle_email_verify_{email}" if email else self.get_ident(request)
