from django.core.management.base import BaseCommand
from ...models import APIRequestLog
import datetime
from django.utils import timezone


class Command(BaseCommand):
    help = "Remove all API logs OR all but the last n days of API logs"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days_num",
            help="Keep the last n number of days of logs and delete the rest",
            type=int,
            choices=[x + 1 for x in range(100000)],
        )

    def handle(self, *args, **options):
        days_num = options["days_num"]

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
