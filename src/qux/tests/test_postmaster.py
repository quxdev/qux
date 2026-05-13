"""Tests for the ``manage.py postmaster`` management command.

Uses Django's locmem email backend (configured in ``runtests.py``) so messages
land in ``django.core.mail.outbox`` instead of being sent.
"""

from __future__ import annotations

from io import StringIO

from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings


class TestPostmaster(SimpleTestCase):
    def setUp(self) -> None:
        mail.outbox = []  # locmem outbox is module-global; reset per test

    def test_to_override_sends(self):
        out = StringIO()
        call_command(
            "postmaster",
            "--to",
            "ops@example.com",
            "--from",
            "noreply@example.com",
            "--subject",
            "ping",
            stdout=out,
        )
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.subject, "ping")
        self.assertEqual(msg.from_email, "noreply@example.com")
        self.assertEqual(msg.to, ["ops@example.com"])
        self.assertIn("sent: 1 message(s).", out.getvalue())

    def test_multiple_to_recipients(self):
        out = StringIO()
        call_command(
            "postmaster",
            "--to",
            "a@example.com",
            "--to",
            "b@example.com",
            "--from",
            "noreply@example.com",
            stdout=out,
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["a@example.com", "b@example.com"])

    def test_no_recipients_raises(self):
        # Default: no --to, settings.ADMINS empty in runtests.py -> CommandError.
        with self.assertRaises(CommandError):
            call_command("postmaster", stdout=StringIO())

    @override_settings(ADMINS=[("Ops", "ops@example.com")])
    def test_admins_default_uses_mail_admins(self):
        out = StringIO()
        call_command("postmaster", stdout=out)
        # mail_admins prepends EMAIL_SUBJECT_PREFIX; just check one outbox entry
        # to the configured admin.
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("ops@example.com", mail.outbox[0].to)
