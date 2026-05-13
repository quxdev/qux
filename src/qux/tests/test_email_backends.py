"""Tests for ``qux.backends.email.SESBackend``.

The backend extends ``django_ses.SESBackend``. We don't test SES network calls
— that's django-ses's responsibility. We test the Reply-To injection by
stubbing the upstream ``send_messages``.
"""

from __future__ import annotations

import importlib.util
import unittest
from unittest.mock import patch

from django.core.mail import EmailMessage
from django.test import SimpleTestCase, override_settings

DJANGO_SES_AVAILABLE = importlib.util.find_spec("django_ses") is not None

if DJANGO_SES_AVAILABLE:
    from qux.backends.email import SESBackend


@unittest.skipUnless(DJANGO_SES_AVAILABLE, "django-ses not installed")
class TestSESBackend(SimpleTestCase):
    def _backend(self):
        return SESBackend()

    @override_settings(REPLY_TO_EMAIL="ops@example.com")
    def test_injects_reply_to_when_unset(self):
        backend = self._backend()
        msg = EmailMessage(subject="S", body="B", from_email="hi@app.com", to=["u@x.com"])
        with patch("django_ses.SESBackend.send_messages", return_value=1) as upstream:
            backend.send_messages([msg])
        self.assertEqual(msg.reply_to, ["ops@example.com"])
        upstream.assert_called_once()

    @override_settings(REPLY_TO_EMAIL="ops@example.com")
    def test_does_not_overwrite_explicit_reply_to(self):
        backend = self._backend()
        msg = EmailMessage(
            subject="S",
            body="B",
            from_email="hi@app.com",
            to=["u@x.com"],
            reply_to=["caller@app.com"],
        )
        with patch("django_ses.SESBackend.send_messages", return_value=1):
            backend.send_messages([msg])
        self.assertEqual(msg.reply_to, ["caller@app.com"])

    def test_no_reply_to_setting_means_no_injection(self):
        backend = self._backend()
        msg = EmailMessage(subject="S", body="B", from_email="hi@app.com", to=["u@x.com"])
        # No REPLY_TO_EMAIL setting -> backend leaves reply_to empty.
        with patch("django_ses.SESBackend.send_messages", return_value=1):
            backend.send_messages([msg])
        self.assertEqual(msg.reply_to, [])
