# qux/backends

Pluggable backends — values for Django settings like `EMAIL_BACKEND`. Modules here implement the `<app>.backends.<name>.<Class>` Django convention (cf. `django.contrib.sessions.backends.cache.SessionStore`).

## `email.SESBackend`

Subclass of `django_ses.SESBackend` that injects one default header on outgoing messages: `Reply-To: settings.REPLY_TO_EMAIL` (only if the caller didn't set one). Saves operators from the common bug where `from_email="no-reply@..."` causes silent reply bounces.

```python
# settings.py
EMAIL_BACKEND = "qux.backends.email.SESBackend"
REPLY_TO_EMAIL = "support@app.com"
# plus standard django-ses settings: AWS_SES_REGION_NAME, IAM credentials, AWS_SES_V2=True
```

Requires `pip install django-ses>=4` (or `pip install qux[ses]`).

Verify your wiring with `python manage.py postmaster`.

See `src/qux/backends/email.py` for the full module docstring (rationale + non-goals); see `docs/SETTINGS.md` § Mail for the setting reference.

## What's NOT here (and why)

- Hygiene headers like `Auto-Submitted` and `Precedence: bulk` — opinionated about mail kind. `Precedence: bulk` is right for digests/notifications, wrong for transactional (password resets, OTPs). Set per-call via `EmailMessage(headers={...})` if your project's profile fits.
- Other ESP backends (SendGrid, Postmark, Mailgun, etc.) — `django-anymail` covers ~12 ESPs as a maintained library. Use that if you need them; qux doesn't reinvent the wheel.
- Cache, session, storage backends — qux doesn't ship these. If a project needs custom non-email backends, they live in the project, not in a shared library.
