import re
import sys

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.utils import ProgrammingError

from qux.utils.mysql import resetsequence

# Only allow valid Django app label characters
APP_LABEL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")


# noinspection PyProtectedMember
class Command(BaseCommand):
    help = "Clear data from all app tables in database"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.wipe = False
        self.nuke = False
        self.app_labels = None

    def add_arguments(self, parser):
        parser.add_argument("args", metavar="app_label", nargs="*", help="Name of app")
        parser.add_argument(
            "--wipe",
            dest="wipe",
            action="store_true",
            default=False,
            help="Delete all data",
        )
        parser.add_argument(
            "--nuke",
            dest="nuke",
            action="store_true",
            default=False,
            help="Delete all data and tables",
        )

    def handle(self, *app_labels, **options):
        self.wipe = options.get("wipe", False)
        self.nuke = options.get("nuke", False)

        self.app_labels = set(app_labels)
        bad_app_labels = set()
        for app in [x for x in self.app_labels if x not in ["users"]]:
            if not APP_LABEL_RE.match(app):
                self.stderr.write(f"Invalid app label: '{app}'")
                sys.exit(2)
            try:
                apps.get_app_config(app)
            except LookupError:
                bad_app_labels.add(app)
        if bad_app_labels:
            for app in bad_app_labels:
                self.stderr.write(
                    f"App '{app}' could not be found. Is it in INSTALLED_APPS?"
                )
            sys.exit(2)

        if self.nuke:
            confirm = input(
                f"This will DROP tables for {self.app_labels}. Type 'yes' to confirm: "
            )
            if confirm != "yes":
                self.stdout.write("Aborted.")
                return

        if self.wipe:
            for app in self.app_labels:
                appmodels = apps.get_app_config(app).get_models(
                    include_auto_created=True
                )
                for appmodel in appmodels:
                    if appmodel._meta.managed:
                        self.stdout.write(f"Deleting all items in model {appmodel}")
                        try:
                            appmodel.objects.all().delete()
                        except ProgrammingError:
                            self.stderr.write(f"model {appmodel} table is corrupt")
                self.do_wipe(app)

        elif self.nuke:
            self.do_nuke()

    @staticmethod
    def do_wipe(app):
        appmodels = apps.get_app_config(app).get_models(include_auto_created=True)
        resetsequence(appmodels)

    def do_nuke(self):
        User = get_user_model()
        if "users" in self.app_labels:
            self.stdout.write("NUKING users")
            User.objects.all().delete()
            self.app_labels.remove("users")

        with connection.cursor() as cursor:
            for app in self.app_labels:
                self.stdout.write(f"NUKING {app}")

                # Drop known model tables
                for table in self.apptables(app):
                    cursor.execute(f"DROP TABLE IF EXISTS {table};")

                # Parameterized delete from migrations
                cursor.execute("DELETE FROM django_migrations WHERE app = %s;", [app])

    def apptables(self, app=None):
        target = [app] if app else self.app_labels
        tables = []
        for label in target:
            appmodels = apps.get_app_config(label).get_models(include_auto_created=True)
            for appmodel in appmodels:
                tables.append(appmodel._meta.db_table)

        return tables
