# Migrating from pre-May-2026 qux

This guide takes a downstream project running the previous qux version (pre-May-2026 cleanup) and walks through everything needed to bring it onto the new qux.

## TL;DR — what bites and how loud it is

| Change | Symptom | Loudness | Action required |
|---|---|---|---|
| `Preference` / `Service` models removed from `qux.auth` | **`ImportError` at import time** | LOUD | Required for any project that imports them. See §1. |
| drf/log `LoggingMixin` no longer writes to DB by default | **`APIRequestLog` table silently stops growing** | **SILENT** | Required for any project that has `LoggingMixin` wired AND queries `APIRequestLog`. See §2. |
| `cast` moved from `qux.devtools` to `qux.utils.coerce` | `ImportError` if importing from `qux.devtools` | LOUD | Update imports to `from qux.utils.coerce import cast`. See §3. |
| `qux.mail` package deleted entirely | `ImportError` if anything imports from `qux.mail` | LOUD (but zero known consumers) | Switch to Django's mail framework + `qux.backends.email.SESBackend`. See §4. |
| `qux.logger` package deleted entirely | `ImportError` if anything imports `CoreURLLog` / `CoreCommLog` / `DownloadLog` / `UploadLog` | LOUD (but zero known consumers) | Replace with stdlib `logging` channels OR copy the model into your own app. See §5. |
| `qux.phone.fakephonenumber` deleted | `ImportError` if anything imports it | LOUD (but zero known consumers) | Remove the import. See §6. |
| `Preference.loaddata` removed | `AttributeError` if anything calls it | LOUD (but zero known consumers) | Use Django's `python manage.py loaddata` instead. See §7. |
| `pyproject.toml` `[aws]` extra → `[ses]` extra | `pip install qux[aws]` fails | LOUD | Update install command. See §8. |
| Utility leaf modules live under `qux.utils.<X>` again (not `qux.<X>`) | `ImportError` if importing from the brief flat layout, e.g. `from qux.date import …` | LOUD | Update imports to `qux.utils.<X>`. See §9. |

The two that need real attention are §1 (Preference/Service) and §2 (drf/log silent behavior change). The rest either have zero known consumers or are handled by tooling.

---

## §1. `Preference` + `Service` models removed from `qux.auth`

**What happened:** The `Preference` and `Service` ORM models (and their admin registrations) were removed from `qux.auth.models`. The database tables (`qux_preference`, `qux_service`) were NOT dropped — historical data stays queryable. Migrations stay intact. Only the model classes are gone.

**Why:** They were generic key/value-by-name storage that didn't belong in an authentication subpackage. Project-specific (only one downstream consumer in production: odin's battery-spec preferences). qux.auth is now authentication-only.

**Symptom:** Any project that does `from qux.auth.models import Preference` or `from qux.auth.models import Service` will fail at import time.

**Migration steps:**

1. **Define your own `Preference` and `Service` models** in your project's own app (e.g. `myapp/models.py`):

   ```python
   from django.contrib.auth import get_user_model
   from django.db import models
   from qux.models import CoreModel, default_null_blank

   User = get_user_model()


   class Service(CoreModel):
       SLUG_PREFIX = "service"
       slug = models.CharField(max_length=14, unique=True)
       name = models.CharField(max_length=64, unique=True)
       description = models.TextField(**default_null_blank)
       url = models.URLField("URL", max_length=1024, **default_null_blank)

       class Meta:
           db_table = "qux_service"   # <-- point at the existing table
           managed = False             # <-- existing migrations stay in qux's history

       def __str__(self):
           return self.name


   class Preference(CoreModel):
       SLUG_PREFIX = "pref"
       slug = models.CharField(max_length=11, unique=True)
       user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="preferences")
       service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="preferences")
       name = models.CharField(max_length=128)
       value = models.TextField(**default_null_blank)
       type = models.CharField(max_length=32, **default_null_blank)
       category = models.CharField(max_length=32, **default_null_blank)
       is_basic = models.BooleanField(default=False)

       class Meta:
           db_table = "qux_preference"   # <-- point at the existing table
           managed = False
           constraints = [
               models.UniqueConstraint(
                   fields=["user", "service", "name"],
                   name="unique_user_service_preference",
               ),
           ]

       def __str__(self):
           return f"{self.service}.{self.name}"
   ```

   `managed = False` tells Django not to manage the schema (qux's old migrations created the tables; your new model just maps to them).

2. **Update imports throughout your project:**

   ```diff
   - from qux.auth.models import Preference, Service
   + from myapp.models import Preference, Service
   ```

3. **Re-register admin if you used the qux admin classes** (in `myapp/admin.py`):

   ```python
   from django.contrib import admin
   from .models import Preference, Service

   @admin.register(Service)
   class ServiceAdmin(admin.ModelAdmin):
       list_display = ("id", "slug", "name", "description")
       search_fields = list_display

   @admin.register(Preference)
   class PreferenceAdmin(admin.ModelAdmin):
       fields = ("user", "service", "category", "name", "value")
       list_display = fields
       raw_id_fields = ("user", "service")
   ```

**Verify:** `python manage.py check` runs clean. Existing `Preference.objects.get(name="...")` queries still return rows.

---

## §2. drf/log `LoggingMixin` no longer writes to DB by default

**What happened:** `LoggingMixin` used to dispatch to `persist_api_log.delay(...)` (celery) → DB INSERT into `APIRequestLog`, with a synchronous fallback. **Now it emits a structured log record on the `qux.drf` logger channel and does NOT write to `APIRequestLog`.** The model and table stay; nothing populates them by default.

**Why:** API request logging at any non-trivial volume should not synchronously INSERT into the OLTP database. The new shape (logger channel) lets operators ship records to a log aggregator (file, ELK, Datadog, Loki) which is the standard pattern at scale. Projects that genuinely want DB-backed request logs add an opt-in handler.

**Symptom:** **Silent.** No error. `APIRequestLog.objects.count()` stops increasing. Dashboards / queries / cron jobs that read from the table return progressively staler data.

**Affected projects in `~/Code`:** `batteryos/odin` (settings.py + 2 view files), `batteryos/zeus` (settings.py).

**Migration — pick ONE:**

### Option A: Restore DB persistence (one-line LOGGING config addition)

Add the opt-in handler to your `LOGGING`:

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        # ... your existing handlers ...
        "qux_drf_db": {"class": "qux.drf.log.handlers.APIRequestLogDBHandler"},
    },
    "loggers": {
        # ... your existing loggers ...
        "qux.drf": {"handlers": ["qux_drf_db"], "level": "INFO", "propagate": False},
    },
}
```

This restores the pre-rewrite behavior end-to-end: every request logged by `LoggingMixin` produces an `APIRequestLog` row. Synchronous INSERT (no celery dep). At low volume this is fine.

### Option B: Switch to a log-file or aggregator sink

If you don't query `APIRequestLog` and want to ship logs elsewhere (file, JSON to ELK/Datadog/Loki, syslog):

```python
LOGGING = {
    "version": 1,
    "handlers": {
        "qux_drf_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/var/log/myapp/api-requests.log",
            "maxBytes": 50_000_000,
            "backupCount": 10,
        },
    },
    "loggers": {
        "qux.drf": {"handlers": ["qux_drf_file"], "level": "INFO", "propagate": False},
    },
}
```

Then ship the file via your normal log pipeline (Vector, Fluentd, Datadog agent). The `APIRequestLog` table can stay empty going forward — historical rows remain queryable.

### Drop the celery dep (if you only had it for drf/log)

If your `requirements.txt` or `pyproject.toml` pulled in celery solely so `LoggingMixin` could `.delay()`:

```diff
- celery>=5.3
- # plus broker (redis, rabbitmq, etc.)
```

Drop it. Drop your celery worker process (`celery -A project worker -Q drf_log` or similar). The `DRF_TRACKING_LOG_QUEUE` setting is gone (no-op now).

**Verify:** Hit one of your DRF endpoints. Confirm a record appears either in `APIRequestLog` (Option A) or in your log file (Option B). `python manage.py check` runs clean.

**Per-user filter rules:** The `APILoggingRule` model is no longer consulted by the mixin. If you previously used "log requests from user X" rules, replace with a `logging.Filter`:

```python
# myapp/log_filters.py
import logging

class OnlyUsersFilter(logging.Filter):
    def __init__(self, user_ids):
        super().__init__()
        self._allowed = set(user_ids)

    def filter(self, record):
        return getattr(record, "user_id", None) in self._allowed
```

Wire it via `LOGGING["filters"]` and attach to your handler. The filter can consult any source (DB, cache, settings list, env var) — see `src/qux/drf/log/README.drf-logging.md` for the full recipe.

---

## §3. `cast` moved from `qux.devtools` to `qux.utils.coerce`

**What happened:** The string-typed coercion function `cast(valtype, value, default=None)` moved from `qux.devtools` to `qux.utils.coerce` alongside its sibling helpers (`toint`, `tofloat`, `tobool`). A pre-existing bug where `cast("int", "abc")` raised `ValueError` instead of returning `default` was fixed.

**Why:** Same concern as the typed coerce helpers; should live together. `devtools` is now single-purpose (just `stacktrace`).

**Symptom:**
- `from qux.devtools import cast` → `ImportError`.
- `from qux.utils import cast` → `ImportError` (the `qux.utils` package does not re-export symbols; import from leaf modules).

**Migration:**

```diff
- from qux.devtools import cast
+ from qux.utils.coerce import cast
```

or, if you were on the very old `from qux.utils import cast` shim:

```diff
- from qux.utils import cast
+ from qux.utils.coerce import cast
```

**Bonus:** any `cast("int", "garbage")` calls that previously raised `ValueError` now correctly return `default`. If your code was catching that ValueError, you can simplify.

**Verify:** `python -c "from qux.utils.coerce import cast; print(cast('int', 'abc', default=-1))"` prints `-1`.

---

## §4. `qux.mail` package deleted entirely

**What happened:** The whole `qux.mail/` subpackage is gone. Old API (`qux.mail.Email`, `qux.mail.sendgrid.QuxSendGrid`) and the never-shipped intermediate API (`Message` dataclass, providers, `send()`) — all removed.

**Why:** It reinvented Django's mail framework and `django-anymail` without adding load-bearing value. Use Django's stdlib mail directly.

**Symptom:** Any `from qux.mail import ...` → `ImportError`. (Confirmed zero downstream consumers in `~/Code`; this section is for projects we may not have grepped.)

**Migration:** Switch to Django's stdlib mail.

```diff
- from qux.mail import Email
- e = Email()
- e.sender = "noreply@app.com"
- e.to = "user@example.com"
- e.subject = "Hi"
- e.message = "<p>Hi</p>"
- obj, response, status = e.send()

+ from django.core.mail import send_mail
+ from django.template.loader import render_to_string
+
+ sent_count = send_mail(
+     subject="Hi",
+     message="Hi (plain text fallback)",
+     from_email="noreply@app.com",
+     recipient_list=["user@example.com"],
+     html_message="<p>Hi</p>",  # multipart/alternative; better deliverability than HTML-only
+ )
```

For SES specifically — install `django-ses` (or `pip install qux[ses]`) and:

```python
# settings.py
EMAIL_BACKEND = "qux.backends.email.SESBackend"   # injects Reply-To from settings
REPLY_TO_EMAIL = "support@app.com"
AWS_SES_REGION_NAME = "us-east-1"
AWS_SES_V2 = True
# AWS credentials via env vars / IAM role / ~/.aws/credentials
```

Verify with `python manage.py postmaster --to ops@example.com`.

---

## §5. `qux.logger` package deleted entirely

**What happened:** The whole `qux.logger/` subpackage is gone (`DownloadLog`, `UploadLog`, `CoreURLLog`, `CoreCommLog` model classes).

**Why:** No migrations directory → these models had never been deployed via qux's migration history. Tests were attribute-roundtrip only (didn't exercise DB). Survey of `~/Code` showed zero real downstream consumers.

**Symptom:** Any `from qux.logger.models import ...` → `ImportError`.

**Migration:** If you somehow had these tables in your DB (highly unlikely given the migration gap), define the models in your own app pointing at the existing tables:

```python
# myapp/models.py
from django.db import models

class CoreCommLog(models.Model):
    # ... copy the field definitions from the old qux.logger.models.CoreCommLog ...
    class Meta:
        db_table = "qux_log_comm"
        managed = False
```

Otherwise, just remove the import.

For "log HTTP communications" use cases: prefer Python's stdlib `logging` on a named channel (the same pattern qux.drf and qux.mail use post-rewrite).

---

## §6. `qux.phone.fakephonenumber` deleted

**What happened:** The IN-only stub `fakephonenumber()` is gone.

**Why:** Acknowledged-incomplete (returned None for any non-IN country). Survey showed zero real downstream callers.

**Symptom:** `from qux.utils.phone import fakephonenumber` → `ImportError`.

**Migration:** Remove the import. If you genuinely need fixture phone numbers, use [`faker`](https://faker.readthedocs.io/) which has `Faker().phone_number()` with locale support:

```python
from faker import Faker
fake = Faker("en_IN")  # or any other locale
phone = fake.phone_number()
```

`phone_number()` and `format_phone_number()` are unchanged.

---

## §7. `Preference.loaddata` removed

**What happened:** The classmethod `Preference.loaddata()` (which read `QUX_FIXTURES_PREFERENCE` env var and loaded preferences from a JSON file) is gone. Then the `Preference` model itself was removed (see §1). Survey showed zero callers.

**Migration:** Use Django's stock `python manage.py loaddata <fixture.json>` instead. Drop any `QUX_FIXTURES_PREFERENCE` env-var setup.

---

## §8. `pyproject.toml` `[aws]` extra renamed to `[ses]`

**What happened:** The `[aws]` extra (which pulled `boto3`) is gone. Replaced by `[ses]` which pulls `django-ses` (which transitively pulls boto3 + botocore).

**Why:** The new `qux.backends.email.SESBackend` is a `django_ses.SESBackend` subclass, so `django-ses` is the actual dep. `boto3` alone was insufficient.

**Symptom:** `pip install qux[aws]` → "WARNING: qux 0.4.0 does not provide the extra 'aws'" (or fails outright in strict mode).

**Migration:**

```diff
- pip install qux[aws]
+ pip install qux[ses]
```

In `requirements.txt` / `pyproject.toml` / `setup.py`:

```diff
- qux[aws]
+ qux[ses]
```

---

## §9. Utility leaf modules live under `qux.utils.<X>` (the flat layout was a brief intermediate state)

**What happened:** The pure-utility modules (`coerce`, `date`, `decorators`, `devtools`, `file`, `forms`, `json`, `modelfields`, `mysql`, `phone`, `random`, `urls`, `validators`) live under `qux.utils.*` as they did pre-2026. An interim flat layout — `qux.coerce`, `qux.date`, etc. at the package root — was reverted because the namespace-collision concern that motivated the move did not survive scrutiny: `qux` is a regular package (it has `__init__.py`), so no external distribution can collide with `qux.utils`; and flat names like `qux.json` / `qux.random` actually *increase* internal shadowing risk versus the namespaced form. The flat layout was never published (no git tag), so most downstream consumers never saw it.

**Why:** Cleaner top-level namespace for the package; collapses the `import-linter` "utilities don't depend on apps" contract to one source module (`qux.utils`) instead of thirteen.

**Symptom:**
- `from qux.coerce import cast` → `ImportError`. (Use `qux.utils.coerce`.)
- `from qux.date import todate` → `ImportError`. (Use `qux.utils.date`.)
- Same shape for `decorators`, `devtools`, `file`, `forms`, `json`, `modelfields`, `mysql`, `phone`, `random`, `urls`, `validators`.

**Migration:** Mechanical rewrite. From the root of your downstream project:

```bash
perl -i -pe 's{\bqux\.(coerce|date|decorators|devtools|file|forms|json|modelfields|mysql|phone|random|urls|validators)\b}{qux.utils.$1}g' \
  $(git ls-files '*.py')
```

The `qux.utils` package does not re-export its leaves. Always import from the leaf module (`from qux.utils.coerce import cast`), not from the package (`from qux.utils import cast` → `ImportError`).

**Note:** The previously-shipped helper script `scripts/migrate_qux_utils_imports.py` (which rewrote in the *opposite* direction) and `scripts/alias_qux_modules.py` have been removed — they migrated to a layout that no longer exists.

---

## §10. Other internal cleanups (no migration needed)

These changed but won't break anything downstream:

- `auth/views/shared.py` extracted from `appviews.py` + `apiviews.py`. Public class names (`MagicLinkRequestView`, `CLIOTPRequestView`, `QuxLoginView`, `QuxSignupView`, etc.) are unchanged — downstream imports still work.
- HTML-only-no-text-fallback fix: signup verification, magic link, and CLI OTP emails now ship as multipart/alternative (HTML + plain-text). **Bonus** — better deliverability, no spam-filter penalty for HTML-only.
- `delete_drf_log --days_num` argparse: was building a 100k-element validation list at every command startup. Replaced with `_positive_int` argparse type. Same behavior for valid inputs; better error messages for invalid ones.
- Module docstrings added to 9 top-level utility modules; READMEs added to 3 subpackages. Code unchanged.
- Commented-out `save()` block in `models/base.py` deleted. Was always dead.

---

## Verification checklist

After running through the relevant sections above, verify:

1. **Imports resolve:** `python manage.py check` in your project — no `ImportError` from qux.
2. **Auth still works:** Hit `/auth/login/`, `/auth/signup/`, `/auth/magic-link/` — pages render, flows complete end-to-end.
3. **DRF tokens still work:** Existing `CustomToken` rows continue to authenticate (no schema change).
4. **API logging produces records somewhere:** If you have `LoggingMixin` wired, hit one of those endpoints. Confirm either (a) a row appears in `APIRequestLog` (Option A in §2), or (b) a structured record appears in your configured log sink (Option B). If neither, your LOGGING config didn't get updated.
5. **SES sends still go out:** `python manage.py postmaster --to ops@example.com` exits with `sent: 1 message(s).`
6. **Existing data is intact:** `Preference.objects.count()` (via your new model) returns the same number it did before. Same for `Service`, `APIRequestLog`, `qux_preference` table, etc.

If anything from this list fails: file an issue with the symptom + which section you ran through. We'd rather hear about a missed migration step than have you debug it alone.
