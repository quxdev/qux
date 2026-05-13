"""Shared helpers for ``appviews.py`` (HTML) and ``apiviews.py`` (DRF API).

Two concerns extracted from duplication:

- ``is_blocked_domain(email)`` — settings-driven ``BLOCKED_DOMAIN_FOR_MAGIC_LINK``
  check, used by both magic-link (HTML) and CLI-OTP (API) request flows.
- ``get_or_create_user_for_email(email)`` — username-collision-aware user
  creation. The HTML magic-link path always did this carefully; the API OTP
  path was using a naive ``username=email`` that would collide on second use.

Email sending is NOT extracted: ``django.core.mail.send_mail(...,
html_message=render_to_string(template, ctx))`` is already the right shape.
A custom wrapper added no value AND made it harder to ship a plain-text
alternative (spam-filter penalty for HTML-only).
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


def is_blocked_domain(email: str) -> bool:
    """True if ``email``'s domain is in ``settings.BLOCKED_DOMAIN_FOR_MAGIC_LINK``.

    Empty/missing setting → never blocks. Used to refuse magic-link / CLI-OTP
    requests from personal-email domains so corp-only auth flows stay
    enforceable per project policy.
    """
    blocked = getattr(settings, "BLOCKED_DOMAIN_FOR_MAGIC_LINK", []) or []
    if not blocked or "@" not in email:
        return False
    return email.rsplit("@", maxsplit=1)[-1] in blocked


def get_or_create_user_for_email(email: str):
    """Look up a User by email; create one with a unique username if absent.

    Username collision strategy: ``email`` first, then ``email1``, ``email2``,
    … on subsequent collisions. Matches the long-standing magic-link path's
    behavior; was missing from the CLI-OTP path (would collide on second use
    with the same email).
    """
    user = User.objects.filter(email=email).first()
    if user is not None:
        return user

    base_username = email
    candidate = base_username
    suffix = 1
    while User.objects.filter(username=candidate).exists():
        candidate = f"{base_username}{suffix}"
        suffix += 1
    return User.objects.create(username=candidate, email=email, is_active=True)
