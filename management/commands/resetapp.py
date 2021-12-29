import sys

from django.apps import apps
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.utils import ProgrammingError

from qux.utils.mysql import resetsequence


# noinspection PyProtectedMember
class Command(BaseCommand):
    help = "Clear data from all app tables in database"

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
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
        # self.verbosity = options.get('verbosity')
        # self.interactive = options.get('interactive')
        self.wipe = options.get("wipe", False)
        self.nuke = options.get("nuke", False)

        self.app_labels = set(app_labels)
        bad_app_labels = set()
        for app in [x for x in self.app_labels if x not in ["users"]]:
            try:
                apps.get_app_config(app)
            except LookupError:
                bad_app_labels.add(app)
        if bad_app_labels:
            for app in bad_app_labels:
                self.stderr.write(
                    "App '%s' could not be found. Is it in INSTALLED_APPS?" % app
                )
            sys.exit(2)

        if self.wipe:
            for app in self.app_labels:
                appmodels = apps.get_app_config(app).get_models(
                    include_auto_created=True
                )
                for appmodel in appmodels:
                    if appmodel._meta.managed:
                        print("Deleting all items in model {}".format(appmodel))
                        try:
                            appmodel.objects.all().delete()
                        except ProgrammingError:
                            print("model {} table is corrupt".format(appmodel))
                self.do_wipe(app)

        elif self.nuke:
            self.do_nuke()

        return

    @staticmethod
    def do_wipe(app):
        appmodels = apps.get_app_config(app).get_models(include_auto_created=True)
        resetsequence(appmodels)

    def do_nuke(self):
        if "users" in self.app_labels:
            print("NUKING users")
            [x.delete() for x in User.objects.all()]

            with connection.cursor() as cursor:
                sqlstr = "ALTER TABLE auth_user AUTO_INCREMENT = 1;"
                cursor.execute(sqlstr)

            self.app_labels.remove("users")

        with connection.cursor() as cursor:
            for app in self.app_labels:
                print("NUKING %s" % app)
                cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
                for table in self.apptables(app):
                    sqlstr = "DROP TABLE IF EXISTS {:s};".format(table)
                    print(sqlstr)
                    cursor.execute(sqlstr)

                cursor.execute("SHOW TABLES LIKE '{}_%'".format(app))
                tables = [x[0] for x in list(cursor.fetchall())]
                for table in tables:
                    sqlstr = "DROP TABLE IF EXISTS {:s};".format(table)
                    print(sqlstr)
                    cursor.execute(sqlstr)

                cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

                sqlstr = "DELETE FROM django_migrations WHERE app='{:s}';".format(app)
                print(sqlstr)
                cursor.execute(sqlstr)

    def apptables(self, app=None):
        target = [app] if app else self.app_labels
        tables = []
        for app in target:
            appmodels = apps.get_app_config(app).get_models(include_auto_created=True)
            for appmodel in appmodels:
                tables.append(appmodel._meta.db_table)

        return tables
