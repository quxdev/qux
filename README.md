# Qux — a reusable Django app

Qux is the shared Django foundation for vishalapte/quxdev projects: augmented model bases, magic-link/OTP auth, DRF request logging, SEO scaffolding, webhook delivery, vendored static, and a grab-bag of utilities. Similar in spirit to `django-extensions` but opinionated for our stack.

## Layout

PyPA-canonical src layout:

```
qux/                        ← repo root
  pyproject.toml            ← package metadata; dynamic version from VERSION
  VERSION                   ← single source of truth for package version
  README.md
  CHANGELOG.md              ← per-release notes, newest first
  MIGRATION.md              ← downstream upgrade guide
  runtests.py
  setup.py                  ← cmdclass shim for asset unpack on install
  docs/
    SETTINGS.md             ← every Django setting qux reads
    plans/                  ← deferred design work
  scripts/
    migrate_qux_submodule.sh
  src/qux/                  ← THE package
    __init__.py             ← __version__ via importlib.metadata
    apps.py                 ← QuxConfig — unpacks asset bundles on Django startup
    _assets/bundles/        ← bootstrap-icons, bootstrap, select2, fonts as zips
    auth/  contacts/  drf/log/  qhook/  seo/  telemetry/  token/   ← Django apps
    pagespeed/  sitespeed/                                          ← audit tools
    admin/  backends/  management/  models/  templatetags/  utils/  ← shared infra
    static/  templates/  tests/
```

Each subpackage's role is detailed in the [Subpackages table](#subpackages); each has its own `README.md`.

Vendored third-party static (bootstrap-icons, bootstrap, select2, qux-fonts) ships as one zip per library under `src/qux/_assets/bundles/`. The unpacked tree is gitignored and recreated at install time by `qux.apps.QuxConfig.ready()` — idempotent via per-bundle marker files in `static/.qux-bundles/`, and a marker is believed only while the files it claims are still on disk. Manual re-trigger: `qux-install-assets`.

On top of the versioned tree, `qux._assets.manifest.ALIASES` declares **stable paths** — `qux/js/bootstrap/`, `qux/css/bootstrap/`, `qux/css/fonts/bootstrap-icons*.css` — mirrored from the unpacked bundle at the same time. Downstream templates and stylesheets reference those, never a version literal, so a library bump is a change to `manifest.py` and a pin bump downstream, nothing else. The mirrors are generated output: gitignored, excluded from the wheel, rebuilt (and refreshed after a bump) on every boot.

If anything the manifest declares is missing, the `qux.W001` system check names it on every `manage.py check`, `collectstatic`, and `runserver`, with `qux-install-assets` as the fix. Failure is loud on purpose: a project using `ManifestStaticFilesStorage` gets no unhashed fallback, so a silently skipped unpack is a sitewide 404. Details in [_assets/README.md](src/qux/_assets/README.md).

## Install

Qux is consumed two ways:

### 1. Editable install (recommended for new projects)

```bash
pip install -e /path/to/qux              # runtime only
pip install -e /path/to/qux[dev]         # + tests, linters, build
pip install -e /path/to/qux[numpy]       # runtime + optional model helpers
```

After install, asset bundles auto-unpack on first `python manage.py runserver` (or any other Django entrypoint). Re-trigger manually with `qux-install-assets --force`.

### 2. Git submodule (legacy)

For the ~40 projects that vendor qux as a git submodule and reference subpackages directly in `INSTALLED_APPS`. Submodule path is conventionally `<sibling>/qux/`, so `<sibling>/` on PYTHONPATH makes `from qux import …` resolve. Migrate any project to the editable-install path with `scripts/migrate_qux_submodule.sh` (auto-detects the submodule, removes it, adds `-e <qux-path>` to `requirements.txt`).

## Wiring up in a Django project

```python
# settings.py
INSTALLED_APPS = [
    *DJANGO_BUILTIN_APPS,
    "rest_framework",
    "qux",                   # top-level qux app — owns asset unpack on startup
    "qux.auth",              # magic link, OTP, signup, password reset
    "qux.seo",
    "qux.token",
    "qux.qhook",
    "qux.drf.log",           # DRF request logger
    "qux.contacts",
]

# Standard auth wiring
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# Common qux settings (full list: docs/SETTINGS.md)
ROOT_TEMPLATE = "_app.html"
BOOTSTRAP = "bs5"
USE_MAGIC_LINK = True
```

```python
# urls.py
urlpatterns += [
    path("auth/", include("qux.auth.urls.appurls", namespace="qux_auth")),
    path("token/", include("qux.token.urls", namespace="qux_token")),
]
```

Each subpackage is its own Django app with its own migrations; you list them individually rather than relying on `qux` to pull them in (intentional — see the design rationale in CHANGELOG / commit history).

## Subpackages

| Path | Purpose | README |
|---|---|---|
| `qux.auth` | Magic-link sign-in, CLI OTP, signup, password reset, throttles | [auth/README.md](src/qux/auth/README.md) |
| `qux.token` | DRF token CRUD with per-user UI | [token/README.md](src/qux/token/README.md) |
| `qux.seo` | Per-page SEO scaffolding and site-audit models | [seo/README.md](src/qux/seo/README.md) |
| `qux.qhook` | Outbound webhook delivery + retry | [qhook/README.md](src/qux/qhook/README.md) |
| `qux.drf.log` | Per-endpoint DRF request logger with sampling rules | [drf/log/README.md](src/qux/drf/log/README.md) |
| `qux.contacts` | Contact + Company models with phone/email subrecords | [contacts/README.md](src/qux/contacts/README.md) |
| `qux.telemetry` | Structured event emission on the `qux` logger channel | [telemetry/README.md](src/qux/telemetry/README.md) |
| `qux.models` | Abstract model bases (timestamps, soft-delete, audit, abstract company/profile) | [models/README.md](src/qux/models/README.md) |
| `qux.utils` | Pure-utility leaves; no upward dependencies (enforced by `import-linter`) | [utils/README.md](src/qux/utils/README.md) |
| `qux.backends` | Pluggable Django backends (currently `SESBackend` for AWS SES email) | [backends/README.md](src/qux/backends/README.md) |
| `qux.admin` | Shared Django admin helpers | [admin/README.md](src/qux/admin/README.md) |
| `qux.templatetags` | `qux` and `quxform` template tag libraries | [templatetags/README.md](src/qux/templatetags/README.md) |
| `qux.pagespeed` | Front-end performance checks (templates + static assets) | [pagespeed/README.md](src/qux/pagespeed/README.md) |
| `qux.sitespeed` | Infrastructure audit (HTTP/2, TLS, DNS, compression, security headers) | [sitespeed/README.md](src/qux/sitespeed/README.md) |
| `qux._assets` | Vendored static asset bundles + install hook | [_assets/README.md](src/qux/_assets/README.md) |

## Models

Abstract model bases (`CoreModel`, `CoreModelPlus`, `QuxModel`, audit, abstract company/profile) live in [`models/README.md`](src/qux/models/README.md). Concrete models live with their owning app — see each app's README in the [Subpackages table](#subpackages). `qux.auth` no longer ships ORM models of its own ([MIGRATION.md §1](MIGRATION.md)).

## Template tags

```django
{% load qux quxform %}
```

`qux` library: `multiply`, `divide`, `atleast`, `qux_min`, `qux_max`, `date_before`, `addstr`, `url_replace`, `{% lineless %}…{% endlineless %}`.

`quxform` library: `is_checkbox` → bool. Used to differentiate Bootstrap form rendering.

## Settings

Every Django setting qux reads is documented in **[docs/SETTINGS.md](docs/SETTINGS.md)** with default and purpose. The most commonly set ones: `ROOT_TEMPLATE`, `BOOTSTRAP`, `USE_MAGIC_LINK`, `BLOCKED_DOMAIN_FOR_MAGIC_LINK`, `REPLY_TO_EMAIL`, `QHOOK_EVENTS`, `QHOOK_MAX_ATTEMPTS`.

## Management commands

Each command's full purpose, args, and gotchas live in its module docstring. Quick map:

| Command | What it does | Source |
|---|---|---|
| `postmaster` | Send one test email through the configured `EMAIL_BACKEND` to verify creds work. `--to` overrides recipients; defaults to `settings.ADMINS` via `mail_admins()`. | `src/qux/management/commands/postmaster.py` |
| `qchecker` | "qjango/qux/athena" project-template compliance checker — verifies a downstream project has the expected dir layout, env vars, settings keys, DB shape, DRF auth classes. Mildly stale on celery checks (May 2026). | `src/qux/management/commands/qchecker.py` |
| `resetapp` | Destructive: `--wipe` deletes all rows for the listed apps + resets sequences; `--nuke` drops tables + clears `django_migrations` rows for those apps (interactive `yes` confirmation). Local-dev tool. | `src/qux/management/commands/resetapp.py` |
| `pagespeed` | Static-analysis report of templates + CSS for PageSpeed-relevant issues. | `src/qux/management/commands/pagespeed.py` |
| `sitespeed` | Audits a deployed site's HTTP/2, TLS, DNS, compression, and security-header configuration. | `src/qux/management/commands/sitespeed.py` |
| `seo_audit` | Crawls a sitemap and runs SEO checks per URL (title length, OG tags, canonical, etc.). | `src/qux/seo/management/commands/seo_audit.py` |
| `backfill_api_logging_rules` | Creates a default `APILoggingRule(enabled=True)` for every existing user. Only useful if your `LOGGING` config wires a `Filter` against `APILoggingRule` (per `src/qux/drf/log/README.md`). | `src/qux/drf/log/management/commands/backfill_api_logging_rules.py` |
| `delete_drf_log` | Prunes `APIRequestLog` rows older than `--days_num N` (or `settings.DRF_TRACKING_RETENTION_DAYS`). Only useful if the `APIRequestLogDBHandler` is wired; otherwise nothing populates that table. | `src/qux/drf/log/management/commands/delete_drf_log.py` |

## Telemetry

Qux emits structured events on the `qux` logger channel for product visibility (login success/failure, magic link sent/refused, mail send success/failure, lifecycle events, etc.). One channel, one handler, JSON-formatted records ready for `jq`. **Anonymous by design** — no user identifiers, IPs, or user-agent strings.

See **[src/qux/telemetry/README.md](src/qux/telemetry/README.md)** for the catalog, setup recipe, correlation IDs, and `jq` query examples.

## Tests

```bash
python runtests.py
```

Runs the full suite (~640 tests, ~22s) with an in-memory SQLite database. No Django project setup required — `runtests.py` configures Django itself.

## Tooling

- `isort` then `black` for formatting (configs in `pyproject.toml`). The order matters — `isort` reorders imports; `black` then re-wraps the result. Reverse order is not idempotent in one pass.
- `import-linter` for architectural contracts (utilities can't depend on apps; apps stay independent).
- `pylint` + `pylint-django` for static analysis.

## Migrating from earlier versions

If you're upgrading a downstream project from pre-May-2026 qux, read **[MIGRATION.md](MIGRATION.md)** first. The two changes that need attention: `Preference` / `Service` models removed from `qux.auth` (loud import error; downstream redefines them locally), and drf/log `LoggingMixin` no longer writes to `APIRequestLog` by default (silent behavior change; one-line LOGGING config addition restores the old behavior). Everything else is either zero-impact (verified zero downstream consumers) or a mechanical `qux.X → qux.utils.X` import rewrite documented in `MIGRATION.md §9`.

## Release notes

Per-release changes are in **[CHANGELOG.md](CHANGELOG.md)**, newest first. Releases before 0.8.3 predate the file; see `git log` and [MIGRATION.md](MIGRATION.md).

## Deferred work

Active design docs live in [`docs/plans/`](docs/plans/). Each plan carries its own status header and decision log.
