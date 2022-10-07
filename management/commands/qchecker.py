
import os
from os import path
from django.conf import settings
from os import environ
from collections.abc import MutableMapping
from django.core.management.base import BaseCommand



# ------------------ COLORED MESSAGES ------------------
class bcolors:
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
        "config",
        "qux",
        "templates",
        "data",
        "static",
    ]

    string_dict = {
        "project/urls.py": "qux.auth.urls",
        "project/urls.py": 'path("account/tokens/", include("qux.token.urls"))',
        "project/settings.py": 'os.path.join(BASE_DIR, "templates")',
        "project/settings.py": "LOGIN_URL",
        "project/settings.py": "LOGOUT_URL",
        "project/settings.py": "LOGIN_REDIRECT_URL",
        "project/settings.py": "LOGOUT_REDIRECT_URL",
        "project/settings.py": "SHOW_USERNAME_SIGNUP",
        "project/settings.py": 'DB_MYSQL if os.getenv("DB_TYPE", "sqlite") == "mysql" else DB_SQLITE',
        "project/settings.py": '"athena": DB_ATHENA',
        "project/routers/__init__.py": "from .authrouter import AuthRouter",
    }
    file_list = [
        "project/celery.py",
        "project/urls.py",
        "templates/_blank.html",
        "templates/_footer.html",
        "templates/_navbar.html",
        "requirements.txt",
        "project/routers/authrouter.py",
    ]

    apps_dirs = ["urls", "views"]
    apps_files = [
        "urls/apiurls.py",
        "urls/appurls.py",
        "views/apiviews.py",
        "views/appviews.py",
        "views/shared.py",
    ]

    config_dict = [
        "config/etc/apache2/conf-available/fqdn.conf",
        "config/etc/apache2/sites-available/fmapp.conf",
        "config/etc/supervisor/conf.d/celery.conf",
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
            f"{bcolors.SUCCESS}\n---------- QJANGO/QUX/ATHENA Compliance Checker Completed ----------\n"
        )

    def check_structure(self):
        print(f"{bcolors.INFO}\nChecking project structure...\n")
        for dir in self.dir_list:
            self.checkdir(dir)

        for file in self.file_list:
            self.checkfile(file)

        for key, value in self.string_dict.items():
            self.checkStringInFile(key, value)

        if path.exists("apps") and path.isdir("apps"):
            dlist = os.listdir("apps")
            for d in dlist:
                if path.exists(d) and path.isdir(d):
                    for dir in self.apps_dirs.items():
                        self.checkdir(f"apps/{d}/{dir}")
                    for file in self.apps_files:
                        self.checkfile(f"apps/{d}/{file}")

        print(f"{bcolors.INFO}\nChecking config files ... \n")
        for file in self.config_dict:
            self.checkfile(file)

        print(
            f"{bcolors.INFO}\nPlease check your wsgi.py file and match with the standard qjango wsgi.py file \n"
        )


    def check_env_variables(self):
        print(f"{bcolors.INFO}\nChecking environment variables...\n")
        for key, value in self.env_dict.items():
            self.checkenv(key, value)


    def check_settings(self):
        # check installed apps
        print(f"{bcolors.INFO}\nChecking settings...installed apps...\n")
        iapps = getattr(settings, "INSTALLED_APPS")
        for app in self.installed_apps:
            if app in iapps:
                print(f"{bcolors.SUCCESS}Installed App: {app} ==> OK")
            else:
                print(f"{bcolors.ERROR}Installed App: {app} ==> NOT FOUND")

        print(f"{bcolors.INFO}\nChecking settings...\n")
        for key, value in self.settings_dict.items():
            self.checkSettings(key, value)

        # check database settings entries using db_dict
        print(f"{bcolors.INFO}\nChecking settings...database settings...\n")

        dbkeys = self.db_dict.keys()
        for key in dbkeys:
            print("key: {0}".format(key))
            db_flat = self.flatten_dict(self.db_dict[key])
            settings_db_dict = getattr(settings, key, None)
            if settings_db_dict is not None:
                settings_db_flat = self.flatten_dict(settings_db_dict)
                for k in db_flat:
                    if k in settings_db_flat:
                        print(f"{bcolors.SUCCESS}Database settings: {k} ==> OK")
                    else:
                        print(f"{bcolors.ERROR}Database settings: {k} ==> NOT FOUND")
            else:
                print(f"{bcolors.ERROR}Database settings: {key} ==> NOT FOUND")

        # check drf settings entries using drf_dict
        print(f"{bcolors.INFO}\nChecking settings...drf settings...\n")
        drfkeys = self.drf_dict.keys()
        for key in drfkeys:
            settings_drf_dict = getattr(settings, key, None)
            if settings_drf_dict is not None:
                drf_flat = self.flatten_dict(self.drf_dict[key])
                settings_drf_flat = self.flatten_dict(settings_drf_dict)
                for k in drf_flat:
                    if k in settings_drf_flat:
                        print(f"{bcolors.SUCCESS}DRF settings: {k} ==> OK")
                    else:
                        print(f"{bcolors.ERROR}DRF settings: {k} ==> NOT FOUND")
            else:
                print(f"{bcolors.ERROR}DRF settings: {key} ==> NOT FOUND")

        # display static files settings for verification
        print(f"{bcolors.INFO}\nPlease validate your static files settings below...\n")
        staticfiles_dict = getattr(settings, "STATICFILES_DIRS", None)
        static_files_root = getattr(settings, "STATIC_ROOT", None)
        static_url = getattr(settings, "STATIC_URL", None)
        print(f"{bcolors.INFO}STATIC_URL: {static_url}")
        print(f"{bcolors.INFO}STATIC_ROOT: {static_files_root}")
        print(f"{bcolors.INFO}STATICFILES_DIRS: {staticfiles_dict}")


    # ------------util functions below this line ------------


    def checkStringInFile(self, filepath, string):
        if path.exists(filepath):
            with open(filepath, "r") as f:
                if string in f.read():
                    print(f"{bcolors.SUCCESS}String: {filepath}-{string} ==> OK")
                    return True
                else:
                    print(f"{bcolors.ERROR}String: {filepath}-{string} ==> NOT FOUND")
        else:
            print(f"{bcolors.ERROR}File: {filepath} ==> NOT FOUND")
        return False


    def checkenv(self, key, value):
        if key in environ:
            if value is not None:
                if environ[key] == value:
                    print(f"{bcolors.SUCCESS}Env: {key}-{value} ==> OK")
            elif environ[key] > "":
                print(f"{bcolors.SUCCESS}Env: {key} ==> OK")
            return True

        print(f"{bcolors.ERROR}Env: {key}-{value} ==> NOT FOUND")
        return False


    def checkdir(self, dirname):
        if path.exists(dirname) and path.isdir(dirname):
            print(f"{bcolors.SUCCESS}Dir: {dirname} ==> OK")
            return True

        print(f"{bcolors.ERROR}Dir: {dirname} ==> NOT FOUND")
        return False


    def checkfile(self, filepath):
        if path.exists(filepath) and path.isfile(filepath):
            print(f"{bcolors.SUCCESS}File: {filepath} ==> OK")
            return True

        print(f"{bcolors.ERROR}File: {filepath} ==> NOT FOUND")
        return False


    def checkSettings(self, key, value):
        if hasattr(settings, key):
            settings_value = getattr(settings, key)
            if value is not None:
                if settings_value == value:
                    print(f"{bcolors.SUCCESS}Settings: {key}-{value} ==> OK")
            else:
                print(f"{bcolors.WARNING}Settings: {key}-{settings_value} ==> CHECK VALUES")
            return True

        print(f"{bcolors.ERROR}Settings: {key}-{value} ==> NOT FOUND")
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


