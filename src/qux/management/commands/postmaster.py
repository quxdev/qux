"""``python manage.py postmaster`` — verify ``EMAIL_BACKEND`` credentials work.

Sends one test message through the project's configured ``settings.EMAIL_BACKEND``.
If the backend is misconfigured (bad creds, sender not verified, network blocked)
the underlying call raises and the command exits non-zero.

Default recipients: ``settings.ADMINS`` (via ``mail_admins``).
Override with ``--to`` (repeatable). Override sender with ``--from``.
"""

from __future__ import annotations

from django.conf import settings
from django.core.mail import mail_admins, send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Send a test email through the configured EMAIL_BACKEND to verify credentials."

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            action="append",
            metavar="EMAIL",
            help="Override recipient. Repeat for multiple. Default: settings.ADMINS via mail_admins().",
        )
        parser.add_argument(
            "--from",
            dest="from_email",
            metavar="EMAIL",
            help="Override sender. Default: settings.SERVER_EMAIL.",
        )
        parser.add_argument(
            "--subject",
            default="qux postmaster check",
            help="Subject line. Default: 'qux postmaster check'.",
        )

    def handle(self, *args, **options):
        backend = settings.EMAIL_BACKEND
        sender = options["from_email"] or settings.SERVER_EMAIL
        to_override: list[str] | None = options["to"]
        subject: str = options["subject"]

        recipients = to_override if to_override else [a[1] for a in settings.ADMINS]
        if not recipients:
            raise CommandError("No recipients: settings.ADMINS is empty and --to was not given.")

        self.stdout.write(self.style.MIGRATE_HEADING("EMAIL_BACKEND check"))
        self.stdout.write(f"  backend:    {backend}")
        self.stdout.write(f"  sender:     {sender}")
        self.stdout.write(f"  recipients: {', '.join(recipients)}")

        body = (
            "If you received this, the configured EMAIL_BACKEND is wired correctly "
            "from this host.\n"
            f"\nbackend: {backend}\nsender:  {sender}\n"
        )

        if to_override:
            sent = send_mail(
                subject=subject,
                message=body,
                from_email=sender,
                recipient_list=recipients,
                fail_silently=False,
            )
        else:
            mail_admins(subject=subject, message=body, fail_silently=False)
            sent = len(recipients)

        self.stdout.write(self.style.SUCCESS(f"sent: {sent} message(s)."))
