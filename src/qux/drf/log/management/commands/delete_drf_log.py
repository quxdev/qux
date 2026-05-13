"""``python manage.py delete_drf_log [--days_num N]`` — prune ``APIRequestLog`` rows.

With ``--days_num N``, deletes rows older than ``N`` days (keeps the last ``N``).
Without the flag, falls back to ``settings.DRF_TRACKING_RETENTION_DAYS``
(default 14). Wire this into a daily cron / Celery beat / systemd timer to
keep the log table from growing unbounded.

Only useful for projects that wire ``qux.drf.log.handlers.APIRequestLogDBHandler``
in their ``LOGGING`` config — the mixin no longer writes to ``APIRequestLog``
by default (May 2026 rewrite). Projects sending logs to file/JSON/ELK/Datadog
have nothing to prune via this command.
"""

import argparse
import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from ...app_settings import app_settings
from ...models import APIRequestLog


def _positive_int(value: str) -> int:
    """argparse type that accepts only positive integers."""
    try:
        ivalue = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{value!r} is not an integer") from exc
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(f"--days_num must be > 0; got {ivalue}")
    return ivalue


class Command(BaseCommand):
    help = "Remove all API logs OR all but the last n days of API logs"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days_num",
            help="Keep the last n days of logs and delete the rest. Must be > 0.",
            type=_positive_int,
        )

    def handle(self, *args, **options):
        days_num = options["days_num"] or app_settings.RETENTION_DAYS

        if days_num:
            today = timezone.now()
            start_date = today - datetime.timedelta(days=days_num)
            logs_to_delete = APIRequestLog.objects.filter(requested_at__lt=start_date)

        else:
            logs_to_delete = APIRequestLog.objects.all()

        deleted_logs_count = logs_to_delete.count()
        logs_to_delete.delete()

        if deleted_logs_count:
            success_message = (
                f"Successfully removed {deleted_logs_count} API "
                f'log{"s" if deleted_logs_count > 1 else ""}'
            )
        else:
            success_message = "No logs to delete"

        self.stdout.write(self.style.SUCCESS(success_message))
