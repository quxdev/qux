"""Email backends — values for ``settings.EMAIL_BACKEND``.

``SESBackend`` extends ``django_ses.SESBackend`` to inject one default header
on outgoing messages before delegating to the upstream backend's serialization
+ send:

* ``Reply-To: settings.REPLY_TO_EMAIL`` (only if the caller did not set one).

Why this exists at all (vs. using ``django_ses.SESBackend`` directly): Django
has no ``DEFAULT_REPLY_TO_EMAIL`` setting and no pre-send signal. Without a
backend wrapper, every developer must remember ``reply_to=[…]`` on every
``EmailMessage`` — easy to forget, common bug when ``from_email`` is
``no-reply@…`` and the reply silently bounces. Setting it here makes the
default automatic and overridable per-message.

Other hygiene headers (``Auto-Submitted``, ``Precedence: bulk``, etc.) are
deliberately NOT added by default — they're opinionated about mail kind
(``Precedence: bulk`` is right for digests, wrong for password resets) and
projects with a specific mail profile should set them per-call via
``EmailMessage(headers={...})`` or by subclassing this backend.

django-ses (with ``AWS_SES_V2=True``) serializes ``EmailMessage`` to raw MIME
via ``EmailMessage.message().as_bytes()`` and ships it as ``Content.Raw.Data``,
so ``reply_to`` set on the message reaches SES as a real header. SES preserves
it (only ``Message-ID`` and ``Date`` are overwritten server-side per AWS docs).

Usage:

    EMAIL_BACKEND = "qux.backends.email.SESBackend"
    REPLY_TO_EMAIL = "support@app.com"
    # plus the standard django-ses settings: AWS_SES_REGION_NAME,
    # AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY (or an IAM role), AWS_SES_V2=True

Verify the wiring with ``python manage.py postmaster``.

Requires ``pip install django-ses>=4`` — declared as the ``[ses]`` extra in
``pyproject.toml``.
"""

from __future__ import annotations

from django.conf import settings

import django_ses


class SESBackend(django_ses.SESBackend):
    """SESBackend that injects a default Reply-To header when the caller
    didn't set one. See module docstring for rationale."""

    def send_messages(self, email_messages):
        reply_to = getattr(settings, "REPLY_TO_EMAIL", None)
        if reply_to:
            for msg in email_messages:
                if not msg.reply_to:
                    msg.reply_to = [reply_to]
        return super().send_messages(email_messages)
