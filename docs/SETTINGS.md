# Qux settings reference

Every Django setting that qux reads, with its default and what it controls. Settings whose default works for most projects are marked **(default OK)**; the others either need to be set deliberately or change behavior in ways downstream should know about.

Standard Django settings (`AUTH_USER_MODEL`, `BASE_DIR`, `DEBUG`, `INSTALLED_APPS`, `LOGIN_REDIRECT_URL`, `PASSWORD_RESET_TIMEOUT`, `SITE_ID`, `STATIC_ROOT`, `STATIC_URL`, `STATICFILES_DIRS`, `TEMPLATES`) are not duplicated here — see Django's docs.

---

## Templates and theming

### `ROOT_TEMPLATE`
Default: `"_blank.html"`. **(default OK)**

The base template every qux view extends via `{% extends base_template %}`. Override to point qux's auth, token, and password-reset pages at your project's site shell.

### `BOOTSTRAP`
Default: `"bs4"`. Allowed: `"bs4"` or `"bs5"`. **(default OK; bs5 recommended for new projects)**

Picks the Bootstrap variant qux's templates render against. `"bs5"` selects the `bs5/<page>.html` templates; anything else (including unset) selects the legacy bs4 templates.

---

## Auth — magic link

### `USE_MAGIC_LINK`
Default: `False`.

Master switch for magic-link sign-in. When `False`, `MagicLinkRequestView.dispatch()` returns 404 even though the URL is always registered — this lets `reverse("qux_auth:magic_link")` and `{% url %}` resolve in templates without crashing on every page that links to the feature.

### `BLOCKED_DOMAIN_FOR_MAGIC_LINK`
Default: `[]`.

List of email domains (lowercase) blocked from requesting magic links. Used in `MagicLinkRequestView.post()` and `apiviews.py`. Example: `["aol.com", "hotmail.com"]`.

### `MAGIC_LINK_EMAIL_LIMIT`
Default: `5`.

Per-email-address request cap inside `MAGIC_LINK_RATE_PERIOD`.

### `MAGIC_LINK_RATE_LIMIT`
Default: `10`.

Per-IP+UA-fingerprint request cap inside `MAGIC_LINK_RATE_PERIOD`.

### `MAGIC_LINK_RATE_PERIOD`
Default: `3600` (seconds).

Sliding window length for both rate limits above.

### `MAGIC_LINK_MIN_SUBMIT_TIME`
Default: `2` (seconds).

Bot protection: requests submitted faster than this after the form was rendered are rejected.

### `CLI_OTP_TIMEOUT`
Default: `300` (seconds).

TTL for OTP codes issued via the CLI auth endpoint (`apiviews.py`).

---

## Auth — signup / profile

### `SHOW_USERNAME_SIGNUP`
Default: `None` (treated as falsy).

When truthy, the signup form requires a separate username field. Otherwise the user's email becomes their username (collisions are auto-suffixed `email1`, `email2`, …).

### `SHOW_COMPLETE_PROFILE_FORM`
Default: not set (falsy via `hasattr`).

When truthy, post-magic-link login flow gates redirect on whether `first_name` + `last_name` are populated; missing → user is sent to `update-profile/` first.

---

## Mail

qux does not ship its own mail subsystem. Use Django's built-in mail framework:

```python
from django.core.mail import send_mail, EmailMessage
send_mail("subject", "body", "from@x.com", ["to@x.com"], html_message="<p>hi</p>")
```

Set `EMAIL_BACKEND` to pick the transport (Django's stock SMTP / console / file / locmem; or `qux.backends.email.SESBackend` for AWS SES via IAM creds). Set `SERVER_EMAIL` for the default sender and `ADMINS` for `mail_admins()` recipients.

### `EMAIL_BACKEND = "qux.backends.email.SESBackend"`

Subclass of `django_ses.SESBackend` that injects one default header on every outgoing message:

- `Reply-To: settings.REPLY_TO_EMAIL` (only if the caller didn't set one).

Why this exists at all (vs. using `django_ses.SESBackend` directly): Django has no `DEFAULT_REPLY_TO_EMAIL` setting and no pre-send signal. Without a backend, every developer must remember `reply_to=[…]` on every `EmailMessage` — easy to forget when `from_email` is `no-reply@…`, common bug, replies silently bounce.

Other hygiene headers (`Auto-Submitted`, `Precedence`, etc.) are deliberately not added by default — they're opinionated about mail kind (`Precedence: bulk` is right for digests, wrong for password resets). Set them per-call via `EmailMessage(headers={...})` if your project's mail profile fits.

Requires `pip install django-ses>=4` (or `pip install qux[ses]`). All standard `django_ses` settings apply: `AWS_SES_REGION_NAME`, `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (or an IAM role), `AWS_SES_V2=True`, etc.

### `REPLY_TO_EMAIL`
Default: not set (no Reply-To header injected).

When `EMAIL_BACKEND` is `SESBackend`, this address is set as `Reply-To:` on any outgoing message that doesn't already have one. Useful when `from_email` is `no-reply@…` and you want replies to land in an on-call mailbox.

### Verifying your config

```
python manage.py postmaster                         # uses settings.ADMINS
python manage.py postmaster --to ops@example.com    # explicit recipient
```

Sends one message through the configured `EMAIL_BACKEND`. Misconfigured backends raise and the command exits non-zero. See `src/qux/management/commands/postmaster.py`.

---

## Webhooks (qhook)

### `QHOOK_EVENTS`
Default: not set — **must be defined** if you use `@hook`. Required.

List of allowed event names. The `@hook(event=...)` decorator no-ops if the event isn't in this list. Example: `["calculation_completed", "user_signed_up"]`.

### `QHOOK_MAX_ATTEMPTS`
Default: not set — **must be defined** if you use `@hook`. Required.

Number of times qhook retries a failing webhook delivery. See `src/qux/qhook/README.md` for the full retry shape.

---

## DRF request logging (`qux.drf.log`)

All DRF-log settings are read with the prefix `DRF_TRACKING_`. The keys below show the **fully-prefixed setting name** to set in `settings.py`. Defaults from `src/qux/drf/log/app_settings.py`.

### `DRF_TRACKING_ENABLED`
Default: `True`. Master switch — set to `False` to skip all DRF request logging.

### `DRF_TRACKING_ALWAYS_LOG_ERRORS`
Default: `True`. When `True`, 4xx/5xx responses are always logged regardless of sampling rules.

### `DRF_TRACKING_DECODE_REQUEST_BODY`
Default: `True`. Decode `request.body` to a string before logging. Set `False` for endpoints that accept large file uploads to avoid `RequestDataTooBig`.

### `DRF_TRACKING_STORE_RESPONSE_ON_ERRORS_ONLY`
Default: `True`. When `True`, only error responses (≥400) have their bodies stored. Reduces storage cost.

### `DRF_TRACKING_MAX_BODY_BYTES`
Default: `4096`. Truncate stored request/response bodies to this many bytes.

### `DRF_TRACKING_MAX_SIZE`
Default: `4096`. Per-field max size — fields exceeding this are dropped from the log entry entirely.

### `DRF_TRACKING_PATH_LENGTH`
Default: `256`. Max length of stored request paths.

### `DRF_TRACKING_USERNAME_LENGTH`
Default: `128`. Max length for the username column.

### `DRF_TRACKING_VIEW_LENGTH`
Default: `256`. Max length for the view-name column.

### `DRF_TRACKING_VIEW_METHOD_LENGTH`
Default: `256`. Max length for the view-method column.

### `DRF_TRACKING_LOOKUP_FIELD`
Default: `"email"`. Field on the User model used to identify the user in log entries.

### `DRF_TRACKING_RETENTION_DAYS`
Default: `14`. Default age (days) past which `prune_apirequestlog` removes log entries.

### `DRF_TRACKING_LOG_QUEUE`
Default: `"drf_log"`. Celery queue name for the async log-persist task. Only relevant if you wire up Celery.

### `DRF_TRACKING_ADMIN_LOG_READONLY`
Default: `False`. When `True`, `APIRequestLog` admin pages disable add/change/delete.

---

## SEO scanner (`qux.seo.scanner`)

The scanner makes external HTTP requests to the target site (sitemap.xml + every URL listed). These three settings keep it well-behaved — without them, a sitemap with thousands of URLs becomes a DDoS-shaped burst on the target.

### `QUX_SEO_REQUEST_DELAY_MS`
Default: `250`.

Milliseconds of `time.sleep()` between consecutive HTTP requests. Set to `0` to disable throttling entirely (fast scans on a site you know can take it). Negative values are clamped to 0.

### `QUX_SEO_USER_AGENT`
Default: `"qux-seo-scanner (+https://github.com/quxdev/qux)"`.

The `User-Agent` header on every outgoing request. The default identifies the scanner clearly so target-site logs can attribute traffic. Override to identify your specific deployment (e.g. `"acme-internal-seo-scanner/1.0 (ops@acme.com)"`).

### `QUX_SEO_MAX_URLS`
Default: `10000`.

Hard cap on URLs scanned per `scan_site` invocation. If a sitemap returns more URLs than this, the list is truncated (with a warning logged) and the scan proceeds on the first N. Sanity guard against accidentally pointing the scanner at a site with a runaway sitemap.

---

## Misc

### `DEBUG_VERBOSE`
Default: `False`. **(default OK)**

When `True`, qux's model code (`qux.models.base`) emits extra debug logging during `.randomize()` and other dev-only helpers.
