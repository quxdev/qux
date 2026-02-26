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
