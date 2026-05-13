"""``python manage.py backfill_api_logging_rules`` — create default APILoggingRule rows.

Iterates every user in ``AUTH_USER_MODEL`` and ensures each has an
``APILoggingRule(enabled=True, active=True)`` row. Existing rules are left
alone (idempotent ``get_or_create``). Reports the number of rows newly
created.

Historical context: when ``qux.drf.log.LoggingMixin`` consulted ``APILoggingRule``
to decide whether to log a given user's requests, this command pre-populated
the table so existing users defaulted to "logging on" rather than requiring
admins to opt them in manually.

**As of May 2026** the mixin emits to the ``qux.drf`` logger channel and no
longer reads ``APILoggingRule``. The model + table stay queryable for
historical data; this command is preserved for projects that wire a
``logging.Filter`` against ``APILoggingRule`` (per the recipe in
``README.drf-logging.md``). Projects that don't need per-user filtering
can ignore this command.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from qux.drf.log.models import APILoggingRule


class Command(BaseCommand):
    help = "Create default APILoggingRule(enabled=True) for users missing one"

    def handle(self, *args, **options):
        User = get_user_model()
        created = 0
        for user in User.objects.all().iterator():
            obj, was_created = APILoggingRule.objects.get_or_create(
                user=user, defaults={"enabled": True, "active": True}
            )
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Created {created} rules"))
