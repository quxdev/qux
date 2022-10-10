import os
from os import path
from django.conf import settings
from os import environ
from collections.abc import MutableMapping
from django.core.management.base import BaseCommand


# ------------------ COLORED MESSAGES ------------------
class BColors:
    INFO = "\033[94m"
    SUCCESS = "\033[92m"
    WARNING = "\033[93m"
    ERROR = "\033[91m"
    UNDERLINE = "\033[4m"


# noinspection PyProtectedMember
class Command(BaseCommand):
    help = "Qjango/Qux/Athena compliance checker for Django apps"

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def handle(self, *app_labels, **options):
        self.checkall()

    # ----------------- Configuration -----------------

    # files and directories to check

    dir_list = [
        "project",
        "apps",
        "common",
        "server",
        "qux",
        "templates",
        "data",
        "static",
    ]

    string_dict = {
        "project/urls.py": [
            "qux.auth.urls",
            'path("account/tokens/", include("qux.token.urls"))',
        ],
        "project/settings/__init__.py": [
            "from .settings import *",
            "from .db_settings import DATABASES",
        ],
        "project/settings/settings.py": [
            'os.path.join(BASE_DIR, "templates")',
            "LOGIN_URL",
            "LOGOUT_URL",
            "LOGIN_REDIRECT_URL",
            "LOGOUT_REDIRECT_URL",
            "SHOW_USERNAME_SIGNUP",
        ],
        "project/routers/__init__.py": [
            "from .authrouter import AuthRouter",
        ],
    }

    files = {
        "project/settings/db_settings.py": "db_settings.py",
        "project/routers/authrouter.py": "authrouter.py",
    }

    file_list = [
        "requirements.txt",
        "project/celery.py",
        "project/urls.py",
        "project/routers/authrouter.py",
        "templates/_blank.html",
        "templates/_footer.html",
        "templates/_navbar.html",
    ]

    apps = {
        "urls": [
            "apiurls.py",
            "appurls.py",
        ],
        "views": [
            "apiviews.py",
            "appviews.py",
            "shared.py",
        ],
    }

    config_files = [
        "server/etc/apache2/conf-available/fqdn.conf",
        "server/etc/apache2/sites-available/fmapp.conf",
        "server/etc/supervisor/conf.d/celery.conf",
    ]

    # environment variables to check
    env_dict = {
        "SECRET_KEY": None,
        "DJANGO_DEBUG": None,
        "ALLOWED_HOSTS": None,
        "DB_TYPE": None,
        "DB_NAME": None,
        "DB_USERNAME": None,
        "DB_PASSWORD": None,
        "DB_HOST": None,
        "EMAIL_BACKEND": None,
        "DEFAULT_FROM_EMAIL": None,
        "AWS_SES_REGION_NAME": None,
        "ATHENA_USERNAME": None,
        "ATHENA_PASSWORD": None,
        "ATHENA_HOST": None,
    }

    # settings entries to check
    installed_apps = ["qux", "qux.auth", "qux.seo", "qux.token", "qux.drf.log"]
    settings_dict = {
        "SECRET_KEY": None,
        "DEBUG": None,
        "ALLOWED_HOSTS": None,
        "LOGIN_URL": "/login/",
        "LOGOUT_URL": "/logout/",
        "LOGIN_REDIRECT_URL": None,
        "LOGOUT_REDIRECT_URL": None,
        "SHOW_USERNAME_SIGNUP": None,
        "EMAIL_BACKEND": None,
        "DEFAULT_FROM_EMAIL": None,
        "AWS_SES_REGION_NAME": None,
        "BROKER_URL": "redis://localhost:6379",
        "CELERY_RESULT_BACKEND": "redis://localhost:6379",
        "CELERY_ACCEPT_CONTENT": ["application/json"],
        "CELERY_TASK_SERIALIZER": "json",
        "CELERY_RESULT_SERIALIZER": "json",
        "CELERY_CREATE_MISSING_QUEUES": True,
        "DATABASE_ROUTERS": ["project.routers.AuthRouter"],
    }

    db_dict = {
        "DB_MYSQL": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": None,
            "USER": None,
            "PASSWORD": None,
            "HOST": None,
            "PORT": None,
            "OPTIONS": {
                "charset": "utf8mb4",
            },
        },
        "DB_ATHENA": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": "athena",
            "USER": os.getenv("ATHENA_USERNAME", None),
            "PASSWORD": os.getenv("ATHENA_PASSWORD", None),
            "HOST": os.getenv("ATHENA_HOST", None),
            "PORT": os.getenv("ATHENA_PORT", ""),
            "OPTIONS": {
                "charset": "utf8mb4",
                "ssl": {"ca": os.getenv("ATHENA_SSL_CERT", None)},
            },
        },
        "DB_SQLITE": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": None,
        },
    }

    drf_dict = {
        "REST_FRAMEWORK": {
            "DEFAULT_AUTHENTICATION_CLASSES": (
                "rest_framework.authentication.SessionAuthentication",
                "qux.token.models.CustomTokenAuthentication",
            ),
        }
    }
    # ------------------------------

    def checkall(self):
        base_dir = settings.BASE_DIR
        os.chdir(base_dir)
        cwd = os.getcwd()
        print("---------- QJANGO/QUX/ATHENA Compliance Checker ----------\n")
        print("Current working directory: {0}\n".format(cwd))

        self.check_structure()

        self.check_env_variables()

        self.check_settings()

        print(
            f"{BColors.SUCCESS}\n---------- QJANGO/QUX/ATHENA Compliance Checker Completed ----------\n"
        )

    def check_structure(self):
        print(f"{BColors.INFO}\nChecking project structure...\n")
        for dirpath in self.dir_list:
            self.checkdir(dirpath)

        for file in self.file_list:
            self.checkfile(file)

        for key, items in self.string_dict.items():
            for item in items:
                self.checkstringinfile(key, item)

        if path.exists("apps") and path.isdir("apps"):
            dlist = os.listdir("apps")
            for d in dlist:
                if path.exists(d) and path.isdir(d):
                    for dirpath in self.apps:
                        self.checkdir(f"apps/{d}/{dirpath}")
                        for file in self.apps[dirpath]:
                            self.checkfile(f"apps/{d}/{file}")

        print(f"{BColors.INFO}\nChecking config files ... \n")
        for config_file in self.config_files:
            self.checkfile(config_file)

        print(
            f"{BColors.INFO}\nPlease check your wsgi.py file and match with the standard qjango wsgi.py file \n"
        )

    def check_env_variables(self):
        print(f"{BColors.INFO}\nChecking environment variables...\n")
        for key, value in self.env_dict.items():
            self.checkenv(key, value)

    def check_settings(self):
        # check installed apps
        print(f"{BColors.INFO}\nChecking settings...installed apps...\n")
        iapps = getattr(settings, "INSTALLED_APPS")
        for app in self.installed_apps:
            if app in iapps:
                print(f"{BColors.SUCCESS}Installed App: {app} => OK")
            else:
                print(f"{BColors.ERROR}Installed App: {app} => NOT FOUND")

        print(f"{BColors.INFO}\nChecking settings...\n")
        for key, value in self.settings_dict.items():
            self.checksettings(key, value)

        # check database settings entries using db_dict
        print(f"{BColors.INFO}\nChecking settings...database settings...\n")

        dbkeys = self.db_dict.keys()
        for key in dbkeys:
            print("key: {0}".format(key))
            db_flat = self.flatten_dict(self.db_dict[key])
            settings_db_dict = getattr(settings, key, None)
            if settings_db_dict is not None:
                settings_db_flat = self.flatten_dict(settings_db_dict)
                for k in db_flat:
                    if k in settings_db_flat:
                        print(f"{BColors.SUCCESS}Database settings: {k} => OK")
                    else:
                        print(f"{BColors.ERROR}Database settings: {k} => NOT FOUND")
            else:
                print(f"{BColors.ERROR}Database settings: {key} => NOT FOUND")

        # check drf settings entries using drf_dict
        print(f"{BColors.INFO}\nChecking settings...drf settings...\n")
        drfkeys = self.drf_dict.keys()
        for key in drfkeys:
            settings_drf_dict = getattr(settings, key, None)
            if settings_drf_dict is not None:
                drf_flat = self.flatten_dict(self.drf_dict[key])
                settings_drf_flat = self.flatten_dict(settings_drf_dict)
                for k in drf_flat:
                    if k in settings_drf_flat:
                        print(f"{BColors.SUCCESS}DRF settings: {k} => OK")
                    else:
                        print(f"{BColors.ERROR}DRF settings: {k} => NOT FOUND")
            else:
                print(f"{BColors.ERROR}DRF settings: {key} => NOT FOUND")

        # display static files settings for verification
        print(f"{BColors.INFO}\nPlease validate your static files settings below...\n")
        staticfiles_dict = getattr(settings, "STATICFILES_DIRS", None)
        static_files_root = getattr(settings, "STATIC_ROOT", None)
        static_url = getattr(settings, "STATIC_URL", None)
        print(f"{BColors.INFO}STATIC_URL: {static_url}")
        print(f"{BColors.INFO}STATIC_ROOT: {static_files_root}")
        print(f"{BColors.INFO}STATICFILES_DIRS: {staticfiles_dict}")

    # ------------util functions below this line ------------

    @staticmethod
    def checkstringinfile(filepath, string):
        if path.exists(filepath):
            with open(filepath, "r") as f:
                if string in f.read():
                    print(f"{BColors.SUCCESS}String: {filepath}={string} => OK")
                    return True
                else:
                    print(f"{BColors.ERROR}String: {filepath}={string} => NOT FOUND")
        else:
            print(f"{BColors.ERROR}File: {filepath} => NOT FOUND")
        return False

    @staticmethod
    def checkenv(key, value):
        if key in environ:
            if value is not None:
                if environ[key] == value:
                    print(f"{BColors.SUCCESS}Env: {key}={value} => OK")
            elif environ[key] > "":
                print(f"{BColors.SUCCESS}Env: {key} => OK")
            return True

        print(f"{BColors.ERROR}Env: {key}={value} => NOT FOUND")
        return False

    @staticmethod
    def checkdir(dirname):
        if path.exists(dirname) and path.isdir(dirname):
            print(f"{BColors.SUCCESS}Dir: {dirname} => OK")
            return True

        print(f"{BColors.ERROR}Dir: {dirname} => NOT FOUND")
        return False

    @staticmethod
    def checkfile(filepath):
        if path.exists(filepath) and path.isfile(filepath):
            print(f"{BColors.SUCCESS}File: {filepath} => OK")
            return True

        print(f"{BColors.ERROR}File: {filepath} => NOT FOUND")
        return False

    @staticmethod
    def checksettings(key, value):
        if hasattr(settings, key):
            settings_value = getattr(settings, key)
            if value is not None:
                if settings_value == value:
                    print(f"{BColors.SUCCESS}Settings: {key}={value} => OK")
            else:
                print(
                    f"{BColors.WARNING}Settings: {key}={settings_value} => CHECK VALUES"
                )
            return True

        print(f"{BColors.ERROR}Settings: {key}={value} => NOT FOUND")
        return False

    def _flatten_dict_gen(self, d, parent_key, sep):
        for k, v in d.items():
            new_key = parent_key + sep + k if parent_key else k
            if isinstance(v, MutableMapping):
                yield from self.flatten_dict(v, new_key, sep=sep).items()
            else:
                yield new_key, v

    def flatten_dict(self, d: MutableMapping, parent_key: str = "", sep: str = "."):
        return dict(self._flatten_dict_gen(d, parent_key, sep))
