# qux --- Major Hardening & Audit Infrastructure Release

------------------------------------------------------------------------

## Release Summary

Add 100% test coverage, pagespeed/sitespeed modules, and code quality
improvements

-   Add standalone test runner (runtests.py) with in-memory SQLite for
    running tests without a full Django project: python -m qux.runtests

-   Add 632 unit tests across all modules achieving 100% code coverage

-   Add .pylintrc config; all code scores pylint 10.00/10 and is
    black-formatted

-   Add qux.pagespeed module: 12 reusable PageSpeed check functions for
    template/CSS auditing (lazy loading, font-display, alt attributes,
    image dimensions, script defer/async, CSS minification, hardcoded
    URLs, resource hints, WOFF2 font format)

    -   checks.py: reusable check functions, regex patterns, template
        scanning
    -   config.py: project-specific constants and run_all_checks()
        wiring

-   Add qux.sitespeed module: Endpoint class for live infrastructure
    delivery auditing (HTTP/2, TLS certificates, DNS resolution,
    compression, security headers, CDN cache, cookie flags, redirect
    chains, HSTS preload)

-   Add management commands:

    -   pagespeed: generate PageSpeed findings report (--detailed, -o
        file)
    -   sitespeed: audit site + CDN delivery stack (--json, --compact)

-   Refactor management commands:

    -   resetapp: parameterized SQL, input validation, nuke confirmation
        prompt, use get_user_model() instead of hardcoded User import
    -   qchecker: replace print() with logging, use super() without args

-   Fix bugs and improve robustness across modules:

    -   auth: fix signup view template resolution for BS4/BS5
    -   seo: rename \_seo.html to seo.html, fix scanner edge cases
    -   qhook: add SSRF protection to validate_target_url
    -   token: add db_table meta, fix form save signature
    -   contacts: normalize phone numbers on save via signal
    -   models/base: improve slug generation collision handling
    -   drf/log: fix sensitive field scrubbing, IPv6 handling

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

------------------------------------------------------------------------

## Migration Guide

# Migration Guide: Upgrading to the Latest qux

This guide covers all breaking changes, signature changes, and behaviour
changes when upgrading from the previous version of qux (`384d26d`).

------------------------------------------------------------------------

## 1. Import Path Changes

### PageSpeed helpers moved from project to qux

**Before:**

``` python
from apps.tests.test_pagespeed._helpers import (
    run_all_checks, format_summary, get_template_dirs,
    check_lazy_loading, check_font_display, ...
)
```

**After:**

``` python
from qux.pagespeed.checks import (
    format_summary, get_template_dirs, check_lazy_loading,
    check_font_display, check_alt_attributes, check_image_dimensions,
    check_script_loading, check_resource_hints, check_css_minified,
    check_css_imports, check_font_format_woff2, check_hardcoded_static_urls,
    check_hardcoded_media_urls, check_hardcoded_domain_in_static,
    scan_template_content, read_project_file, find_icon_font_css,
    IMG_TAG_RE, SCRIPT_SRC_RE, FONT_FACE_RE, CSS_IMPORT_RE,
)
from qux.pagespeed.config import (
    run_all_checks, FONT_CSS_FILES, ICON_FONT_CSS,
    LAZY_LOADING_EXCEPTIONS, ALT_ATTRIBUTE_EXCEPTIONS,
    SCRIPT_ALLOWLIST, BASE_TEMPLATE, VIEWPORT_SEARCH_PATHS, HEAD_CSS_FILES,
)
```

### Endpoint class extracted from management command

**Before:**

``` python
# Endpoint was embedded in management/commands/site_audit.py — not importable
```

**After:**

``` python
from qux.sitespeed.endpoint import Endpoint

ep = Endpoint("https://example.com", timeout=10, parse_html=True)
print(ep.status())   # "PASS", "WARN", or "FAIL"
print(ep.data)       # dict of all collected metrics
```

### User model references

All modules now use `get_user_model()` instead of importing
`django.contrib.auth.models.User` directly. If you subclass or override
any of these, update accordingly: - `qux.auth.forms` -
`qux.auth.views.appviews` - `qux.auth.models.models` -
`qux.management.commands.resetapp`

------------------------------------------------------------------------

## 2. Management Command Renames

  -------------------------------------------------------------------------------------
  Before                          After                          Notes
  ------------------------------- ------------------------------ ----------------------
  `python manage.py site_audit`   `python manage.py sitespeed`   Command file renamed

  (not available)                 `python manage.py pagespeed`   New command
  -------------------------------------------------------------------------------------

------------------------------------------------------------------------

## 3. Template Rename

**Before:** `qux/seo/templates/_seo.html` **After:**
`qux/seo/templates/seo.html`

Update any `{% extends %}` or `{% include %}` tags referencing
`_seo.html`.

------------------------------------------------------------------------

## 4. Signature Changes

### `CoreModelPlus.delete()` --- parameter change

``` python
# Before
def delete(self):

# After
def delete(self, *args, **kwargs):
```

Now matches Django's `Model.delete()` signature. Callers are unaffected.

### `CoreModelPlus.save()` --- REMOVED

The custom `save()` method that set `dtm_created` and `dtm_updated` has
been deleted. The model now relies on `CoreModel`'s auto-timestamp
fields.

**Action:** If you overrode `CoreModelPlus.save()` and called
`super().save()`, verify your override still works. The parent
`CoreModel.save()` handles timestamps via `auto_now_add` and `auto_now`.

### `CustomTokenForm.save()` --- new parameter

``` python
# Before
def save(self, user=None):

# After
def save(self, commit=None, user=None):
```

**Action:** If you call `form.save(user=request.user)` with keyword
args, no change needed. If you call `form.save(request.user)`
positionally, it will now be interpreted as `commit`, not `user`. Use
keyword argument:

``` python
form.save(user=request.user)
```

### `QuxComplexEncoder.default()` --- parameter renamed

``` python
# Before
def default(self, obj):

# After
def default(self, o):
```

**Action:** If you subclass `QuxComplexEncoder` and override
`default()`, rename the parameter to match.

### `qux_max` renamed to `qux_min` (templatetags/qux.py)

The filter function was named `qux_max` but registered as `"min"`. The
function is now correctly named `qux_min`. The template filter name
`min` is unchanged.

**Action:** If you called `qux_max()` directly from Python code (not via
templates), rename to `qux_min()`.

------------------------------------------------------------------------

## 5. Behaviour Changes --- Breaking

### Audit trail: no more fallback to User(id=1)

`post_save_coremodel` previously fell back to `User.objects.get(id=1)`
when no user was found for audit logging. Now it logs a warning and
**skips the audit record**.

**Action:** If you rely on audit records always being created, ensure
the request user is properly set. If you depended on the User(id=1)
fallback, update your code to explicitly set the user.

### `AbstractContactPhone.save()` always saves now

Previously, if `phone_number()` returned falsy (invalid phone), the
method returned early **without saving**. Now it **always calls
`super().save()`**.

**Action:** If you relied on invalid phone numbers being silently
discarded, add validation in your form or serializer instead.

### `BaseSignupForm.clean_email()` enforces uniqueness

New method raises `ValidationError` if a user with the same email
already exists.

**Action:** If your project allows duplicate emails across users,
override `clean_email()` in your signup form.

### `QuxSignupView` no longer monkey-patches User.email uniqueness

Removed `User._meta.get_field("email")._unique = True` at module load.
Email uniqueness is now enforced via `clean_email()` in the form
instead.

### `CustomTokenAuthentication` rejects inactive tokens

New `authenticate_credentials(key)` method raises `AuthenticationFailed`
for inactive tokens. Previously, inactive tokens were silently accepted.

**Action:** If you have inactive tokens that should still authenticate,
reactivate them or adjust your auth flow.

### `QHookTarget.register()` validates URLs for SSRF

`validate_target_url()` now blocks private IPs, loopback, link-local,
localhost, and cloud metadata endpoints.

**Action:** If you register webhook targets pointing to internal
services, you'll need to override `validate_target_url()` or use public
URLs.

### `qhook` decorator raises specific exceptions

``` python
# Before: raises Exception
raise Exception("Identifier is required")
raise Exception("Hook not found")

# After: raises ValueError / LookupError
raise ValueError("Identifier is required")
raise LookupError("Hook not found")
```

**Action:** If you catch `Exception` broadly, no change needed. If you
catch specific exception types, update accordingly.

### `getconfig` template filter blocks sensitive settings

New blocklist prevents reading `SECRET_KEY`, `DATABASES`,
`DATABASE_PASSWORD`, and any setting containing `SECRET` or `PASSWORD`.

**Action:** If templates read sensitive settings via
`{{ "SECRET_KEY"|getconfig }}`, they will now return `None`. Move
sensitive values to explicit context variables.

### `QuxSendGrid` default sender/subject changed to `None`

``` python
# Before
self.sender = "raptor@finmachines.net"
self.subject = "[FM Energy] Raptor Pricing"

# After
self.sender = None
self.subject = None
```

**Action:** Always set `sender` and `subject` before calling `send()`.

### `Email.__init__` sender is now optional

``` python
# Before — raises AttributeError if EMAIL_SENDER not in settings
self.sender = settings.EMAIL_SENDER

# After — returns None if missing
self.sender = getattr(settings, "EMAIL_SENDER", None)
```

**Action:** Ensure `EMAIL_SENDER` is set in your settings, or set
`email.sender` explicitly before sending.

------------------------------------------------------------------------

## 6. Behaviour Changes --- Non-Breaking

These are improvements that shouldn't break existing code but are worth
knowing about:

  ---------------------------------------------------------------------------
  Module                                  Change
  --------------------------------------- -----------------------------------
  `decorators.qux_debug`                  `print()` → `logger.debug()`

  `token.mixins.authenticate_user`        `print()` → `logger.debug()`

  `utils.devtools.stacktrace`             `print()` → `logger.debug()`

  `utils.file.uploadfile`                 `print()` → `logger.debug()`, bare
                                          `except:` →
                                          `except (IOError, OSError):`

  `utils.file.filehash`                   Uses `with open()` context manager,
                                          bare `except:` →
                                          `except (IOError, OSError):`

  `utils.urls.fetchurl`                   Added `timeout=30` to
                                          `requests.get()` and `urlopen()`

  `utils.urls.MetaURL.load`               Added `timeout=30` to
                                          `requests.get()`

  `qhook.decorators.qhook`                Added `@wraps(func)` to preserve
                                          function metadata

  `qhook.decorators.call_target_url`      Added `timeout=30` to
                                          `requests.post()`

  `templatetags.qux.divide`               Now catches `ZeroDivisionError`
                                          (returns 0)

  `templatetags.qux.qux_floatformat`      Handles negative numbers correctly

  `admin.base.QuxModelAdmin.get_fields`   Field order now preserved (was
                                          unordered `set()`)

  `auth.views.QuxActivateView`            `login()` now passes explicit
                                          `backend=` kwarg

  `auth.views.QuxChangePasswordView`      Calls `update_session_auth_hash()`
                                          (keeps user logged in)

  `auth.views.QuxSignupView`              Username collision handling fixed
                                          (no more cascading suffixes)

  `validators.ValidateListOfN.__eq__`     Returns `NotImplemented` for
                                          non-matching types (was
                                          `AttributeError`)

  `models.base.CoreModel.add_tag`         Prevents duplicate tags

  `utils.misc`                            `numpy` import is now optional
                                          (graceful degradation)
  ---------------------------------------------------------------------------

------------------------------------------------------------------------

## 7. New Migrations

``` bash
python manage.py migrate qux_token     # db_table meta option
python manage.py migrate qux_qhook     # unique constraint changes
```

------------------------------------------------------------------------

## 8. Deleted Files

  ----------------------------------------------------------------------------------------
  File                                    Replacement
  --------------------------------------- ------------------------------------------------
  `qux/pagespeed/_helpers.py`             `qux/pagespeed/checks.py` +
                                          `qux/pagespeed/config.py`

  `qux/pagespeed/tests/test_storage.py`   Removed (tested `project.storage`, not qux)
  ----------------------------------------------------------------------------------------

------------------------------------------------------------------------

## 9. Running Tests

``` bash
# Run all tests
python -m qux.runtests

# Run with coverage
coverage run --source=qux \
  --omit='qux/tests/*,qux/*/tests/*,qux/drf/log/tests/*,qux/*/migrations/*' \
  -m qux.runtests
coverage report
```

------------------------------------------------------------------------

## 10. Quick Checklist

-   [ ] Update `apps.tests.test_pagespeed._helpers` imports →
    `qux.pagespeed.checks` / `config`
-   [ ] Update `_seo.html` references → `seo.html`
-   [ ] Update `site_audit` command → `sitespeed`
-   [ ] Change `form.save(request.user)` →
    `form.save(user=request.user)` for `CustomTokenForm`
-   [ ] If subclassing `QuxComplexEncoder`, rename `default(self, obj)`
    → `default(self, o)`
-   [ ] If calling `qux_max()` directly, rename to `qux_min()`
-   [ ] Set `sender` and `subject` on `QuxSendGrid` before `send()` (no
    more defaults)
-   [ ] Ensure `EMAIL_SENDER` is in settings (no longer crashes if
    missing, but `None`)
-   [ ] Run `python manage.py migrate` for token and qhook migrations
-   [ ] If using `resetapp --nuke`, note the new confirmation prompt
-   [ ] If parsing `qchecker` output from stdout, switch to a logging
    handler
-   [ ] If registering webhook targets to internal IPs, review SSRF
    validation
-   [ ] If relying on audit trail fallback to User(id=1), set user
    explicitly
-   [ ] If relying on `AbstractContactPhone.save()` silently discarding
    invalid phones, add form validation

------------------------------------------------------------------------

## Updated Toolkit Documentation

# qux --- Django Toolkit

qux is a reusable Django library providing base models, authentication,
SEO management, API tokens, webhooks, DRF request logging, template/CSS
auditing, site delivery auditing, and general-purpose utilities.

------------------------------------------------------------------------

## Installation

Add `qux` to your `INSTALLED_APPS`:

``` python
INSTALLED_APPS = [
    # ...
    "qux",
    "qux.auth",         # optional: authentication views & models
    "qux.seo",          # optional: SEO metadata & auditing
    "qux.token",        # optional: named API tokens
    "qux.qhook",        # optional: webhooks
    "qux.contacts",     # optional: contact management
    # ...
]
```

Run migrations:

``` bash
python manage.py migrate
```

------------------------------------------------------------------------

## Table of Contents

1.  [Base Models](#1-base-models)
2.  [Admin Classes](#2-admin-classes)
3.  [Forms](#3-forms)
4.  [Authentication (qux.auth)](#4-authentication)
5.  [SEO (qux.seo)](#5-seo)
6.  [API Tokens (qux.token)](#6-api-tokens)
7.  [Webhooks (qux.qhook)](#7-webhooks)
8.  [Contacts (qux.contacts)](#8-contacts)
9.  [DRF Request Logging (qux.drf.log)](#9-drf-request-logging)
10. [Logger Models (qux.logger)](#10-logger-models)
11. [PageSpeed Auditing (qux.pagespeed)](#11-pagespeed-auditing)
12. [Site Delivery Auditing (qux.sitespeed)](#12-site-delivery-auditing)
13. [Template Tags & Filters](#13-template-tags--filters)
14. [Utilities](#14-utilities)
15. [Management Commands](#15-management-commands)
16. [Decorators & Validators](#16-decorators--validators)
17. [Running Tests](#17-running-tests)

------------------------------------------------------------------------

## 1. Base Models

### CoreModel

The foundation for all qux models. Provides timestamps, slugs, tagging,
audit trail, and test data generation.

``` python
from qux.models import CoreModel

class Article(CoreModel):
    title = models.CharField(max_length=200)
    body = models.TextField()

    # Optional: customise slug generation
    SLUG_PREFIX = "art"
    SLUG_ALLOWED_CHARS = "abcdefghijklmnopqrstuvwxyz0123456789"
```

**Built-in fields:** - `dtm_created` --- auto-set on creation -
`dtm_updated` --- auto-set on every save

**Built-in manager (`objects = CoreManager()`):**

``` python
# Returns None instead of raising DoesNotExist
article = Article.objects.get_or_none(slug="abc123")
```

**Slug generation:**

``` python
# Auto-generated on first save when a `slug` field exists
article = Article(title="Hello World")
article.save()
print(article.slug)  # e.g. "art_k8mf2x"
```

**Tagging (comma-separated tags in a `tags` TextField):**

``` python
article.settag("python")
article.settag("django")
article.hastag("python")     # True
article.gettags()            # "python,django"
article.gettaglist()         # ["python", "django"]
article.deltag("python")
```

**Audit trail (set `AUDIT_MODE = True` on the model):**

``` python
class Article(CoreModel):
    AUDIT_MODE = True
    title = models.CharField(max_length=200)

    class AuditSummary(CoreModelAuditSummary):
        pass

    class AuditDetails(CoreModelAuditDetails):
        audit_summary = models.ForeignKey(AuditSummary, on_delete=models.CASCADE)
```

When `AUDIT_MODE = True`, every save that changes a field value creates
an `AuditSummary` + `AuditDetails` record tracking who changed what.

**Test data generation:**

``` python
# Fill all fields with random data (useful for tests/fixtures)
article = Article()
article.randomize()
article.save()
```

**Serialization:**

``` python
article.to_dict()                    # all fields
article.to_dict(exclude=["body"])    # exclude specific fields
Article.get_dict(pk=1)               # fetch + serialize in one call
```

### CoreModelPlus (Soft Delete)

Extends CoreModel with soft-delete support.

``` python
from qux.models import CoreModelPlus

class Project(CoreModelPlus):
    name = models.CharField(max_length=200)

# Soft delete (sets is_deleted=True, row stays in DB)
project.delete()

# Restore
project.restore()

# Default manager excludes deleted rows
Project.objects.all()              # only non-deleted
Project.objects.all_with_deleted() # includes deleted
```

### AbstractLead

Pre-built lead capture model with UTM tracking.

``` python
from qux.models import AbstractLead

class Lead(AbstractLead):
    pass

# Create from an HTTP request (captures UTM params, user agent, IP, etc.)
lead = Lead.update_or_create_from_request(
    request,
    additional_fields={"source": "homepage"}
)
```

**Fields:** `firstname`, `lastname`, `email`, `phone`,
`http_accept_language`, `http_user_agent`, `remote_addr`, `utm_source`,
`utm_medium`, `utm_campaign`, `utm_term`, `utm_content`, `get_params`
(JSONField).

### AbstractCompany / AbstractProfile

``` python
from qux.models import AbstractCompany, AbstractProfile

class Company(AbstractCompany):
    pass   # inherits: slug, name, address, domain, url

class Profile(AbstractProfile):
    pass   # inherits: slug, phone, title, is_live; OneToOne to User
```

Profile is auto-created when a User is created (via `post_save` signal).

``` python
profile = Profile.get_user(slug="usr_abc123")
profile.get_fullname()    # "John Doe"
profile.get_initials()    # "JD"
```

------------------------------------------------------------------------

## 2. Admin Classes

``` python
from qux.admin import QuxModelAdmin, QuxPlusModelAdmin

@admin.register(Article)
class ArticleAdmin(QuxModelAdmin):
    pass
    # Automatically:
    # - Excludes dtm_created, dtm_updated from fieldsets
    # - Sets id, slug as readonly
    # - Builds list_display from all local fields
    # - list_per_page = 50

@admin.register(Project)
class ProjectAdmin(QuxPlusModelAdmin):
    pass
    # Same as above, plus:
    # - list_filter includes is_deleted
    # - get_queryset shows soft-deleted rows too
```

------------------------------------------------------------------------

## 3. Forms

Bootstrap-ready forms that auto-add CSS classes to all fields.

``` python
from qux.forms import QuxForm, QuxModelForm

class ContactForm(QuxForm):
    name = forms.CharField()
    email = forms.EmailField()
    # All fields automatically get class="form-control"
    # Checkboxes get class="form-check-input"
    # File inputs get class="custom-file-input"
    # Selects get class="form-select"

class ArticleForm(QuxModelForm):
    class Meta:
        model = Article
        fields = ["title", "body"]
```

------------------------------------------------------------------------

## 4. Authentication

Full authentication flow with signup, login, logout, password reset,
email verification, and service preferences.

### Setup

``` python
# settings.py
INSTALLED_APPS = [..., "qux.auth"]

# urls.py
urlpatterns = [
    path("auth/", include("qux.auth.urls.appurls")),
]
```

### Routes

  ---------------------------------------------------------------------------------------------------
  URL                                  View                           Purpose
  ------------------------------------ ------------------------------ -------------------------------
  `/auth/signup/`                      QuxSignupView                  User registration with email
                                                                      verification

  `/auth/activate/<uidb64>/<token>/`   QuxActivateView                Email verification link

  `/auth/login/`                       QuxLoginView                   Login (supports email or
                                                                      username)

  `/auth/logout/`                      logout_request                 Logout

  `/auth/change-password/`             QuxChangePasswordView          Change password (requires
                                                                      login)

  `/auth/password-reset/`              QuxPasswordResetView           Request password reset email

  `/auth/password-reset/done/`         QuxPasswordResetDoneView       Reset email sent confirmation

  `/auth/reset/<uidb64>/<token>/`      QuxPasswordResetConfirmView    Set new password

  `/auth/reset/done/`                  QuxPasswordResetCompleteView   Password reset complete
  ---------------------------------------------------------------------------------------------------

### Service Preferences

Store per-user, per-service settings:

``` python
from qux.auth.models.models import Service, Preference

service = Service.objects.create(name="MyApp", slug="myapp")
Preference.objects.create(
    user=user, service=service,
    name="theme", value="dark", type="str", category="display"
)

# Retrieve preferences
prefs = Preference.get_preferences(user=user, service=service)
# {"theme": "dark"}

# Service-level with type casting
prefs = service.get_preferences(include=["theme"])
```

------------------------------------------------------------------------

## 5. SEO

SEO metadata management and automated site auditing.

### Setup

``` python
INSTALLED_APPS = [..., "django.contrib.sites", "qux.seo"]
SITE_ID = 1
```

### Per-Page SEO Metadata

``` python
from qux.seo.models import SEOSite, SEOPage

# Create site-level defaults
seo_site = SEOSite.objects.create(
    site=Site.objects.get_current(),
    name="My Site",
    title="My Site — Tagline",
    domain="example.com",
    twitter="@mysite",
)

# Create page-level overrides
SEOPage.objects.create(
    site=Site.objects.get_current(),
    canonical="/about/",
    page_name="About",
    page_title="About Us — My Site",
    description="Learn more about us.",
    keywords="about, company",
)
```

### SEO Mixin for Views

``` python
from qux.seo.mixin import SEOMixin

class AboutView(SEOMixin, TemplateView):
    template_name = "about.html"

# In the template:
# {{ meta.title }}
# {{ meta.description }}
# {{ meta.site_name }}
# {{ meta.twitter }}
```

### Automated SEO Auditing

``` python
from qux.seo.scanner import scan_site, format_report

# Crawl sitemap and audit every page
audit = scan_site("example.com", scheme="https")
print(format_report(audit))
```

Or via management command:

``` bash
python manage.py seo_audit example.com --scheme https --report
```

The scanner checks: - Required tags: title, meta description, canonical,
og:url/title/description/image - Title quality (not generic like
"Home") - Meta description length (50--160 chars) - Canonical/og:url
consistency - Duplicate canonicals across pages - og:title vs title
consistency - Twitter card vs OG tag consistency

------------------------------------------------------------------------

## 6. API Tokens

Named, per-user API tokens for DRF authentication.

### Setup

``` python
INSTALLED_APPS = [..., "rest_framework", "qux.token"]

# urls.py
urlpatterns = [
    path("tokens/", include("qux.token.urls")),
]
```

### Creating and Using Tokens

``` python
from qux.token.models import CustomToken

token = CustomToken.objects.create(user=user, name="CI Pipeline")
print(token.key)  # 40-char hex string
```

Authenticate API requests with `Authorization: Token <key>`.

### Token Access Mixin (Group-Based Access Control)

``` python
from qux.token.mixins import TokenAccessMixin

class ProtectedView(TokenAccessMixin, View):
    access_required = ["editors"]  # user must be in "editors" group

    def get(self, request):
        # request.user is authenticated via token or session
        ...
```

Returns JSON `{"error": "Unauthorized"}` (401) or
`{"error": "Forbidden"}` (403).

### Token Management UI

Built-in views for users to manage their own tokens: - `/tokens/home/`
--- list tokens - `/tokens/create/` --- create token - `/tokens/<key>/`
--- token detail - `/tokens/update/<pk>/` --- rename token -
`/tokens/delete/<pk>/` --- delete token

------------------------------------------------------------------------

## 7. Webhooks

Register and deliver webhooks with SSRF protection.

### Setup

``` python
INSTALLED_APPS = [..., "qux.qhook"]

# settings.py
QHOOK_EVENTS = ["order.created", "order.updated"]
QHOOK_MAX_ATTEMPTS = 3
```

### Registering Webhooks

``` python
from qux.qhook.models import QHookTarget

target = QHookTarget.register(
    request=request,
    identifier="customer_123",
    event="order.created",
)
```

URLs are validated against SSRF attacks (private IPs, loopback, metadata
endpoints are blocked).

### Triggering Webhooks

``` python
from qux.qhook.decorators import qhook

@qhook
def create_order(order):
    # ... business logic ...
    return {
        "identifier": order.customer_id,
        "event": "order.created",
        "data": order.to_dict(),
    }
```

The `@qhook` decorator automatically looks up registered targets for the
identifier/event and POSTs the data. Failed deliveries are retried up to
`QHOOK_MAX_ATTEMPTS` times.

------------------------------------------------------------------------

## 8. Contacts

Contact management with phone number normalisation.

### Setup

``` python
INSTALLED_APPS = [..., "qux.contacts"]
```

### Usage

``` python
from qux.contacts.models import Contact, AbstractContactPhone, AbstractContactEmail

# Create concrete phone/email models
class ContactPhone(AbstractContactPhone):
    pass

class ContactEmail(AbstractContactEmail):
    pass

# Create a contact
contact = Contact.objects.create(
    first_name="Jane",
    last_name="Doe",
    email="jane@example.com",
    phone="+14155551234",
)

contact.displayname()       # "Jane Doe"
contact.primaryphone()      # ContactPhone instance or None
contact.primaryemail()      # ContactEmail instance or None
contact.hasphone("+1415")   # True (normalises before comparison)
contact.asdict()            # full dict with phones/emails
```

Phone numbers are automatically normalised to E.164 format on save.

------------------------------------------------------------------------

## 9. DRF Request Logging

Automatic request/response logging for Django REST Framework views.

### Setup

``` python
INSTALLED_APPS = [..., "rest_framework", "qux.drf.log"]

# Optional settings (with defaults shown)
DRF_TRACKING_ADMIN_LOG_READONLY = False
DRF_TRACKING_DECODE_REQUEST_BODY = True
DRF_TRACKING_PATH_LENGTH = 256
DRF_TRACKING_LOOKUP_FIELD = "email"
DRF_TRACKING_MAX_SIZE = 4096
```

### Usage

``` python
from qux.drf.log.mixins import LoggingMixin, LoggingErrorsMixin

class MyAPIView(LoggingMixin, APIView):
    """Logs all requests and responses."""
    pass

class MyStrictAPIView(LoggingErrorsMixin, APIView):
    """Only logs requests that return status >= 400."""
    pass
```

**What gets logged:** - User, username, request timestamp - HTTP method,
path, query params, request body - Response body, status code, response
time (ms) - Remote IP address (handles X-Forwarded-For, IPv4, IPv6)

**Sensitive fields are automatically scrubbed:** `api`, `token`, `key`,
`secret`, `password`, `signature` are replaced with
`********************`.

**Admin dashboard:** Includes a daily request chart with time-series
data at `/admin/log/apirequestlog/`.

------------------------------------------------------------------------

## 10. Logger Models

General-purpose logging models for file operations, URL requests, and
communications.

``` python
from qux.logger.models import DownloadLog, UploadLog, CoreURLLog, CoreCommLog

# Log a file download
DownloadLog.objects.create(
    user=request.user,
    url="https://example.com/report.pdf",
    original="report.pdf",
    filename="report_20240101.pdf",
)

# Log a file upload (auto-computes MD5 hash on save)
UploadLog.objects.create(
    user=request.user,
    filename="data.csv",
    filepath="/uploads/data.csv",
)

# Log a communication
CoreCommLog.objects.create(
    comm_type="email",
    provider="sendgrid",
    sender="noreply@example.com",
    to="user@example.com",
    subject="Welcome",
    status="sent",
)
```

------------------------------------------------------------------------

## 11. PageSpeed Auditing

Static analysis of templates and CSS for PageSpeed / Core Web Vitals
issues.

### Using Check Functions Directly

``` python
from qux.pagespeed.checks import (
    check_lazy_loading,
    check_alt_attributes,
    check_image_dimensions,
    check_font_display,
    check_script_loading,
    check_resource_hints,
    check_css_minified,
    check_hardcoded_static_urls,
    format_summary,
)

# Check all images have loading="lazy"
missing = check_lazy_loading()
for relpath, line_no, tag in missing:
    print(f"{relpath}:{line_no} — missing loading='lazy'")

# Check all images have alt attributes
missing = check_alt_attributes()

# Check font-display declarations
findings = check_font_display(
    font_css_files=["static/css/fonts.css"],
    icon_font_css="static/bootstrap-icons/font/bootstrap-icons.css",
)
```

### Running All Checks

``` python
from qux.pagespeed.config import run_all_checks
from qux.pagespeed.checks import format_summary

checks = run_all_checks()
for line in format_summary(checks):
    print(line)
# Output:
# FONTS
#     [PASS] @font-face must declare font-display
#     [PASS] @font-face should prefer WOFF2 format
# IMAGES
#     [FAIL] missing loading="lazy" [!3]
# ...
```

### Management Command

``` bash
# Summary report to stdout
python manage.py pagespeed

# Detailed report with per-file findings
python manage.py pagespeed --detailed

# Write report to file
python manage.py pagespeed -o report.txt
```

### What It Checks

  -------------------------------------------------------------------------
  Category                         Check                  Why
  -------------------------------- ---------------------- -----------------
  FONTS                            `font-display: swap`   Prevents Flash of
                                   on all `@font-face`    Invisible Text
                                                          (FOIT)

  FONTS                            WOFF2 format preferred 30-50% smaller
                                                          than OTF/TTF

  IMAGES                           `loading="lazy"` on    Defers off-screen
                                   all `<img>`            images

  IMAGES                           Non-empty `alt` on all Accessibility +
                                   `<img>`                SEO

  IMAGES                           Explicit               Prevents
                                   `width`/`height` on    Cumulative Layout
                                   `<img>`                Shift (CLS)

  SCRIPTS                          `async` or `defer` on  Prevents render
                                   `<script src>`         blocking

  CSS                              `.min.css` variants    Reduces file size
                                   used                   

  CSS                              No `@import url()` in  Prevents
                                   head CSS               render-blocking
                                                          chain

  URLS                             No hardcoded           Should use
                                   `/static/` paths       `{% static %}`
                                                          tag

  URLS                             No hardcoded `/media/` Should use
                                   paths                  storage `.url()`

  URLS                             No hardcoded domain    Breaks
                                   before `{% static %}`  CDN/environment
                                                          portability

  HINTS                            `preconnect`,          Speeds up
                                   `dns-prefetch`,        cross-origin
                                   viewport               requests
  -------------------------------------------------------------------------

------------------------------------------------------------------------

## 12. Site Delivery Auditing

Live infrastructure auditing via HTTP/2. Probes a URL and reports on
delivery stack health.

### Using Endpoint Directly

``` python
from qux.sitespeed.endpoint import Endpoint

# Audit a single URL
ep = Endpoint("https://example.com", timeout=10, parse_html=True)

print(ep.status())              # "PASS", "WARN", or "FAIL"
print(ep.data["http_version"])  # "HTTP/2"
print(ep.data["tls_version"])   # "TLSv1.3"
print(ep.data["ttfb_ms"])       # 142.5
print(ep.data["compression_ratio"])  # 0.312
print(ep.warnings)              # ["Missing Header: Content-Security-Policy"]

# Full metrics dict
import json
print(json.dumps(ep.data, indent=2))
```

### Management Command

``` bash
# Full table output
python manage.py sitespeed --url https://example.com --cdn https://cdn.example.com

# JSON output (for CI/CD pipelines)
python manage.py sitespeed --url https://example.com --cdn https://cdn.example.com --json

# Compact output
python manage.py sitespeed --url https://example.com --cdn https://cdn.example.com --compact
```

Exit codes: `0` = PASS, `1` = WARN, `2` = FAIL.

### What It Checks

  -----------------------------------------------------------------------
  Metric                            Details
  --------------------------------- -------------------------------------
  HTTP version                      Warns if not HTTP/2

  TLS                               Version, certificate expiry (warns \<
                                    14 days), issuer, SANs

  HSTS                              Preload readiness (max-age \>= 1yr,
                                    includeSubDomains, preload)

  Compression                       gzip/brotli ratio, warns if not
                                    compressed

  TTFB                              Warns if \> 500ms

  Security headers                  HSTS, X-Content-Type-Options,
                                    X-Frame-Options, CSP,
                                    Referrer-Policy, Permissions-Policy

  DNS                               Resolution time (warns \> 100ms), A
                                    record count, IPv6 support

  CDN                               Cloudflare cache status, POP
                                    location, cdn-cgi/trace

  Cookies                           Secure flag, HttpOnly flag, SameSite
                                    consistency

  Redirects                         Chain length (warns \> 2 hops)

  HTML analysis                     Stylesheet count (warns \> 3),
                                    blocking scripts (warns \> 0),
                                    payload size (warns \> 150KB)
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 13. Template Tags & Filters

``` django
{% load qux %}
{% load quxform %}
```

### Math Filters

``` django
{{ value|multiply:2 }}        {# 10 * 2 = 20 #}
{{ value|divide:3 }}          {# 9 / 3 = 3 #}
{{ value|atleast:5 }}         {# max(value, 5) #}
{{ value|min:100 }}           {# min(value, 100) #}
```

### Number Formatting

``` django
{{ 1234567.89|qux_floatformat_us:2 }}   {# 1,234,567.89 #}
{{ 1234567.89|qux_floatformat_in:2 }}   {# 12,34,567.89 (Indian lakh/crore) #}
```

### String Filters

``` django
{{ "  hello  "|strip }}                 {# "hello" #}
{{ "  hello  "|strip:"h" }}            {# "  hello  " stripped of "h" #}
{{ "prefix"|addstr:"suffix" }}          {# "prefix_suffix" #}
```

### Date Filter

``` django
{{ 30|date_before }}   {# ISO date string 30 days ago #}
```

### Settings Access

``` django
{{ "SITE_NAME"|getconfig }}     {# reads settings.SITE_NAME #}
{# Blocks SECRET_KEY, DATABASE passwords, etc. for security #}
```

### URL Manipulation

``` django
{# Preserve existing query params while changing page #}
<a href="?{% url_replace request 'page' 2 %}">Page 2</a>
{# e.g. ?search=foo&page=2 #}
```

### Smart Static Tags

``` django
{# Auto-switches to .min.js/.min.css in production #}
{# Supports lazy loading (CSS: media=print swap, JS: defer) #}
{% qux_static "css" "css/styles.css" %}
{% qux_static "js" "js/app.js" %}
{% qux_static "css" "css/below-fold.css" lazy=True %}
```

### Remove Blank Lines

``` django
{% lineless %}
  {% if show_header %}
    <h1>Title</h1>
  {% endif %}
{% endlineless %}
{# Strips blank lines from rendered output #}
```

### Form Field Detection

``` django
{% load quxform %}
{% if field|is_checkbox %}
  <div class="form-check">{{ field }}</div>
{% else %}
  <div class="form-group">{{ field }}</div>
{% endif %}
```

------------------------------------------------------------------------

## 14. Utilities

### Type Conversion

``` python
from qux.utils.misc import todate, tofloat, toint, tostring, tobool

todate("2024-01-15")           # date(2024, 1, 15)
todate("Jan 15, 2024")         # date(2024, 1, 15)  — tries 19 formats
todate("invalid", default=date.today())  # falls back to default

tofloat("3.14")                # 3.14
tofloat("invalid", 0.0)       # 0.0

toint("42")                    # 42
toint("invalid", 0)           # 0

tostring(1234567.89)           # "1,234,567.89"

tobool("yes")                  # True
tobool("false")                # False
```

### JSON Encoding

``` python
from qux.utils.misc import QuxComplexEncoder
import json

data = {"date": date.today(), "amount": Decimal("19.99"), "id": uuid4()}
json.dumps(data, cls=QuxComplexEncoder)
# Works with date, datetime, Decimal, UUID, numpy types
```

### Random Data

``` python
from qux.utils.misc import random_string, random_number

random_string(12)    # "kXmPqRsTuVwY"
random_number(6)     # "483721"
```

### Date Utilities

``` python
from qux.utils.date import eomonth, fomonth, daterange

eomonth(date(2024, 1, 15), 0)    # date(2024, 1, 31) — end of current month
eomonth(date(2024, 1, 15), 2)    # date(2024, 3, 31) — end of month +2
fomonth(date(2024, 3, 15), -1)   # date(2024, 2, 1)  — first of month -1

for d in daterange(date(2024, 1, 1), date(2024, 1, 5)):
    print(d)  # 2024-01-01 through 2024-01-05
```

### File Utilities

``` python
from qux.utils.file import filedate, uploadfile, filehash

filedate("/path/to/file.txt")   # datetime or None if missing
filehash("/path/to/file.txt")   # MD5 hex digest or None
success, name = uploadfile(request.FILES["doc"], "/uploads/doc.pdf")
```

### Phone Numbers

``` python
from qux.utils.phone import phone_number, format_phone_number, fakephonenumber

phone_number("+14155551234")              # "+14155551234" (validated E.164)
phone_number("415-555-1234", country="US")  # "+14155551234"
phone_number("invalid")                    # None

format_phone_number("+14155551234", "national")       # "(415) 555-1234"
format_phone_number("+14155551234", "international")  # "+1 415-555-1234"

fakephonenumber("IN")  # random valid Indian phone number
```

### URL Fetching & Open Graph

``` python
from qux.utils.urls import fetchurl, fetchurl_to_file, MetaURL

content, status = fetchurl("https://example.com")
fetchurl_to_file("https://example.com/image.png", "/tmp/image.png")

meta = MetaURL()
meta.url = "https://example.com/article"
meta.load()
print(meta.title)        # "Article Title"
print(meta.description)  # "Article description..."
print(meta.image)        # "https://example.com/og-image.jpg"
print(meta.type)         # "article"
print(meta.to_dict())    # full dict
```

### Email

``` python
from qux.utils.mail.mail import Email

email = Email()
email.to = "user@example.com"
email.subject = "Welcome"
email.message = "<h1>Hello!</h1>"
email.files = ["/path/to/attachment.pdf"]
log, response, status = email.send()
```

Requires `SENDGRID_API_KEY` in settings.

### XML Conversion

``` python
from qux.utils.xmlchemy import alchemy_xmltodict, alchemy_dictoxml

data = alchemy_xmltodict("data.xml")     # XML file → dict
xml_bytes = alchemy_dictoxml(data)        # dict → XML bytes
```

### Debug Utilities

``` python
from qux.utils.devtools import cast, stacktrace

cast("int", "42")          # 42
cast("float", "3.14")      # 3.14
cast("bool", "true")       # True
cast("int", None, 0)       # 0

# In an except block — logs traceback to debug logger
try:
    risky_operation()
except Exception:
    stacktrace()
```

------------------------------------------------------------------------

## 15. Management Commands

### pagespeed --- Template/CSS PageSpeed Audit

``` bash
python manage.py pagespeed                    # summary to stdout
python manage.py pagespeed --detailed         # per-file findings
python manage.py pagespeed -o report.txt      # write to file
```

### sitespeed --- Site Delivery Audit

``` bash
python manage.py sitespeed --url https://example.com --cdn https://cdn.example.com
python manage.py sitespeed --url https://example.com --cdn https://cdn.example.com --json
python manage.py sitespeed --url https://example.com --cdn https://cdn.example.com --compact
```

### seo_audit --- SEO Site Audit

``` bash
python manage.py seo_audit example.com --scheme https --report
```

### resetapp --- Clear App Data

``` bash
python manage.py resetapp myapp --wipe      # delete all rows, reset sequences
python manage.py resetapp myapp --nuke      # DROP tables + remove migrations (confirms)
```

### qchecker --- Compliance Checker

``` bash
python manage.py qchecker
```

Checks: directory structure, required files, environment variables,
Django settings (INSTALLED_APPS, LOGIN/LOGOUT URLs, database, DRF,
static files).

------------------------------------------------------------------------

## 16. Decorators & Validators

### @qux_debug

Logs function calls with arguments, file, and line number when
`DEBUG=True`.

``` python
from qux.decorators import qux_debug

@qux_debug
def process_order(order_id, **kwargs):
    ...
# When DEBUG=True, logs: "process_order called from views.py:42 with (123,) {}"
```

### ValidateListOfN

Validates comma-separated strings have exactly N values.

``` python
from qux.validators import ValidateListOfN

class MyModel(models.Model):
    coordinates = models.CharField(
        max_length=100,
        validators=[ValidateListOfN(3)],  # must be "x,y,z"
    )
```

### FloatListField

Model field for comma-separated float lists.

``` python
from qux.modelfields import FloatListField

class DataPoint(models.Model):
    values = FloatListField()  # stores "1.5,2.7,3.9"
```

------------------------------------------------------------------------

## 17. Running Tests

qux includes a standalone test runner for running tests without a full
Django project:

``` bash
# Run all 632 tests
python -m qux.runtests

# Run with coverage
coverage run --source=qux \
  --omit='qux/tests/*,qux/*/tests/*,qux/drf/log/tests/*,qux/*/migrations/*' \
  -m qux.runtests
coverage report

# Run a specific test module
python -m qux.runtests qux.tests.test_forms

# Run a specific test class
python -m qux.runtests qux.tests.test_models.test_model_base.TestCoreModel
```

This is the standard pattern for reusable Django apps. Tests use an
in-memory SQLite database and do not require project-level settings.

------------------------------------------------------------------------

## Notes

This document consolidates:

1.  Commit-level release notes
2.  All migration and breaking change documentation
3.  Complete updated usage documentation

Architecture remains unchanged. This is a stability, safety, and
operability release.
