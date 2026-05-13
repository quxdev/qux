# Plan: rebuild `qux.auth` on top of `django-allauth`

**Status:** plan, May 2026. Implementation deferred to a focused multi-day session.

**Why:** qux.auth currently maintains ~1,400 LOC of bespoke login/signup/magic-link/password-reset views + forms + Bootstrap templates. `django-allauth` (~10k stars, mature, broadly adopted) ships the same flows AND adds social-auth providers (Google, LinkedIn, Apple, Facebook, GitHub, Microsoft, ~75 more), email verification, MFA, and a maintained adapter pattern. Reframing qux.auth as **opinionated configuration + qjango-flavored template overrides + bot-defense adapter** on top of allauth gets us:

- Social login (the immediate motivator) for free.
- Maintenance-free password-reset / change-password / activation flows.
- Email verification done properly (currently qux uses a custom token; allauth's `EmailAddress` model is more robust).
- Rate-limiting via allauth's `rates` framework instead of bespoke cache-key code.
- Lower ongoing maintenance: allauth absorbs Django version bumps, security fixes, OAuth provider API changes.

**Estimate:** 5-6 focused days. Phasable; not big-bang.

---

## Scope: what migrates, what stays, what's out

### Migrates to allauth (we delete the qux equivalent)

| Concern | Today (qux) | After (allauth) |
|---|---|---|
| Login | `QuxLoginView` + `CustomAuthenticationForm` + login.html | `account_login` view + form + adapter |
| Signup | `QuxSignupView` + `BaseSignupForm` + signup.html | `account_signup` view + form + adapter |
| Account activation | `QuxActivateView` + `account_activation_token` | `account_confirm_email` + `EmailAddress` model |
| Password reset | `QuxPasswordResetView` + 3 sibling views + `CustomPasswordResetForm` | `account_reset_password*` (4 views) + form |
| Change password | `QuxChangePasswordView` + `ChangePasswordForm` | `account_change_password` + form |
| Set password (post-magic-link first time) | `QuxSetPasswordView` + `CustomSetPasswordForm` | `account_set_password` + form |
| Magic link | `MagicLinkRequestView` + `MagicLinkLoginView` + `magic_link_token` | allauth's "Login by code" flow (`account_login_by_code`) + bot-defense adapter |
| Rate limiting | Bespoke cache-key code in `MagicLinkRequestView._is_rate_limited` | allauth's `ACCOUNT_RATE_LIMITS` |

### Stays bespoke in qux (allauth doesn't cover these)

| Concern | Reason |
|---|---|
| **CLI OTP API** (`/api/v1/auth/cli/request/`, `/verify/`) | No-browser auth flow for CLI tools; allauth is browser-flow-centric. Could wire via `dj-rest-auth` if we want a maintained replacement, but the qux-bespoke version is small (~80 LOC) and proven. Keep as-is initially; reconsider in phase 5. |
| **CompleteProfileView** (post-first-login "enter your name" prompt) | Bespoke flow gating on `SHOW_COMPLETE_PROFILE_FORM`. Allauth doesn't have a "fill profile after first login" concept. Wire via `user_signed_up` / `user_logged_in` signal: redirect to qux's existing CompleteProfileView when first_name/last_name empty. |
| **Telemetry events** (`AUTH_LOGIN_SUCCESS`, `AUTH_LOGIN_FAILED`, `AUTH_SIGNUP`, `AUTH_MAGIC_LINK_*`) | EVENTS catalog stays. Wiring point changes from qux views to allauth signals (`user_logged_in`, `user_login_failed`, `user_signed_up`, `email_confirmed`, etc.). |
| **`qux.token.CustomToken` + `CustomTokenAuthentication`** | DRF named-token-with-rotation. Distinct concern from allauth (which is browser sessions). Untouched. |

### Adds (the social-auth payoff)

| Provider | allauth module | Setup work |
|---|---|---|
| Google | `allauth.socialaccount.providers.google` | OAuth client ID + secret in Google Cloud Console |
| LinkedIn | `allauth.socialaccount.providers.linkedin_oauth2` | LinkedIn Developer app credentials |
| Apple | `allauth.socialaccount.providers.apple` | Apple Developer account + key + team ID + service ID (most involved setup) |
| Facebook | `allauth.socialaccount.providers.facebook` | Facebook for Developers app credentials |

For each: drop the provider into `INSTALLED_APPS`, add credentials to settings, add a "Sign in with X" button to the login template. allauth handles OAuth callback, account linking, email matching.

### Out of scope (not in this plan)

- 2FA via `allauth[mfa]` — separate plan if/when needed.
- Email-link login WITHOUT browser (raw email-only auth) — same as CLI OTP concern; defer.
- Replacing `qux.token` with `django-rest-knox` or `dj-rest-auth` — separate question, separate plan.
- WebAuthn / passkeys — allauth supports but separate scope.

---

## Phasing

### Phase 1: Foundation (1 day)

**Goal:** allauth installed, basic email login + signup working at allauth's URLs, qux's existing URLs still working, no behavior regressions.

- Add to `pyproject.toml`: `allauth = ["django-allauth>=0.61"]` extra.
- Settings additions: `INSTALLED_APPS += ["allauth", "allauth.account", "allauth.socialaccount"]`, `MIDDLEWARE += ["allauth.account.middleware.AccountMiddleware"]`, `AUTHENTICATION_BACKENDS = (..., "allauth.account.auth_backends.AuthenticationBackend")`, `ACCOUNT_LOGIN_METHODS = {"email"}`, `ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]`, `ACCOUNT_EMAIL_VERIFICATION = "mandatory"`, `LOGIN_REDIRECT_URL`, `ACCOUNT_LOGOUT_REDIRECT_URL`.
- URL include: `path("accounts/", include("allauth.urls"))`.
- Smoke test: hit `/accounts/signup/`, `/accounts/login/`, `/accounts/logout/`, `/accounts/password/reset/` — confirm allauth's default templates render and the flows complete end-to-end.
- Existing `/auth/...` URLs keep working (qux.auth views unchanged).

**Verify:** `python manage.py check`. Existing test suite stays at 672+. Hit `/accounts/login/` in browser, sign up + log in.

**Risk:** Email verification mandatory may surprise existing users — document in migration notes that this is a settable knob.

### Phase 2: Templates (qjango BS5/BS4 overrides) (½ day)

**Goal:** allauth's UI looks like qux's existing UI (Bootstrap-styled forms, qjango layout).

- Per-template override pattern: create `qux/auth/templates/account/login.html`, `signup.html`, `password_reset.html`, etc. Each extends `qux/auth/templates/account/base.html` which extends the project's `ROOT_TEMPLATE`.
- Use `{% load allauth account socialaccount %}` for allauth-specific tags.
- BS5 vs BS4 strategy: allauth's templates are framework-agnostic; we override with our existing BS5/BS4 templates lightly adapted.
- Keep `MagicLinkRequestForm` as inspiration — bot defenses (honeypot, timing) get reimplemented in adapter (phase 3), not in templates.

**Verify:** Visual: login/signup/reset pages match the existing qux.auth look. Tests: existing template tests still pass.

**Risk:** Template override path conflicts. allauth looks in `templates/account/` first; need to ensure qux's templates take precedence over allauth's defaults via `INSTALLED_APPS` ordering or `TEMPLATES["DIRS"]`.

### Phase 3: Magic link via allauth's login-by-code + bot defenses (½ day)

**Goal:** Replace `MagicLinkRequestView` + `MagicLinkLoginView` with allauth's "Login by code" flow, preserving the four bot defenses (honeypot, timing minimum, domain blocking, rate limiting).

- Enable: `ACCOUNT_LOGIN_BY_CODE_ENABLED = True`, `ACCOUNT_LOGIN_BY_CODE_REQUIRED_AT_SIGNUP = False` (login-only feature).
- Custom adapter `qux.auth.adapters.QuxAccountAdapter(DefaultAccountAdapter)`:
  - `clean_email(email)` — domain blocking against `BLOCKED_DOMAIN_FOR_MAGIC_LINK` setting.
  - Honeypot + timing-minimum: implemented in a custom form subclassing allauth's `RequestLoginCodeForm`. Setting: `ACCOUNT_FORMS = {"request_login_code": "qux.auth.forms.QuxRequestLoginCodeForm"}`.
- Remove `MagicLinkRequestView`, `MagicLinkLoginView`, `magic_link_token`, `MagicLinkRequestForm` from qux.auth.
- Rate limiting: `ACCOUNT_RATE_LIMITS = {"login_by_code_request": "5/300s/key", "login_by_code_request:ip": "10/300s/ip"}` — replaces the bespoke cache-key code.

**Verify:** Magic-link tests in `qux/auth/tests/test_magic_link.py` rewritten to point at allauth URLs. Bot defenses pinned: honeypot test, timing-min test, blocked-domain test, rate-limit test.

**Risk:** allauth's login-by-code wasn't widely used until ~2024; verify it ships in the version we pin and behaves as expected.

### Phase 4: Telemetry signal wiring (½ day)

**Goal:** Existing EVENTS catalog continues firing, but from allauth signals instead of qux views.

- Signal handlers in `qux.auth.signals` (new module):
  - `user_logged_in` → `events.auth_login_success()`
  - `user_login_failed` → `events.auth_login_failed(reason=...)` (allauth provides reason via signal kwarg or via the credentials).
  - `user_signed_up` → `events.auth_signup()`
  - `email_confirmed` → consider new event `EVENTS.AUTH_EMAIL_CONFIRMED`.
  - `password_reset` → `events.auth_password_reset_requested()` / `events.auth_password_reset_completed()`.
- For login-by-code (magic-link replacement), allauth fires `user_logged_in` on success; for the request step, hook the form's clean to emit `auth_magic_link_requested`. For refusals (rate limit, blocked domain, bot check), the form raises and we emit `auth_magic_link_refused(reason=...)` from the form's clean methods.

**Verify:** Telemetry tests pinning that each EVENTS firing still happens, just from a different code path. Operators with alerts on `qux.auth.login_failed` etc. see no behavior change.

**Risk:** allauth's `user_login_failed` signal may not carry as much reason detail as our existing `_login_failure_reason()` extracted from form errors. May need to inspect the credentials dict + cross-reference allauth's adapter rejection codes.

### Phase 5: Social providers (½ day per provider — Google + LinkedIn + Facebook fast; Apple slower)

**Goal:** "Sign in with Google / LinkedIn / Apple / Facebook" buttons on the login template; OAuth flows complete end-to-end.

For each provider:
- Provider OAuth credentials (Google Cloud Console, LinkedIn Dev Portal, Apple Developer, Facebook for Developers) — these are out-of-band; document the steps in a runbook.
- Add to `INSTALLED_APPS`: `"allauth.socialaccount.providers.<name>"`.
- Add provider config to `SOCIALACCOUNT_PROVIDERS` setting (client ID/secret + scopes).
- Add the "Sign in with X" button to the login template via `{% provider_login_url 'google' %}` etc.

**Apple-specific gotcha:** Apple uses a JWT-signed key + team ID + service ID + key ID + private key contents. Setup is the most involved; allauth has docs but expect 1-2 hours of "wait, where do I find this in App Store Connect."

**Verify:** Google/LinkedIn/Facebook each: log in via the provider on a dev machine. Apple: log in via Sign in with Apple (requires Safari + a real Apple ID).

**Risk:** Each provider's OAuth setup involves real-world admin work in their dev portals. Operators need access to the org's Google/LinkedIn/Apple/Facebook accounts.

### Phase 6: Back-compat URL aliases (½ day)

**Goal:** Existing `/auth/login/`, `/auth/signup/`, etc. URLs in 40 downstream projects continue working without breaking bookmarks, emails, integrations.

Two options to evaluate:

- **Option A: HTTP 301 redirects.** `/auth/login/` → `/accounts/login/`. Simple, search-engine-friendly, URL changes visible to user. Bookmarks update on redirect.
- **Option B: URL aliases (same view, two URL paths).** `path("auth/login/", account_login, name="qux_auth:login_legacy")`. URL stays `/auth/login/`, no user-visible change. More forgiving for users with bookmarks.

Recommendation: **Option B** for high-traffic flows (login, signup, magic link); Option A for low-traffic (password reset, change password, set password). Per-URL judgment call. Document in MIGRATION.md.

**Verify:** Hit each old URL, confirm flow completes end-to-end. Update `qux/auth/urls/appurls.py` to map both old and new paths.

### Phase 7: CompleteProfileView signal-driven redirect (½ day)

**Goal:** First-time login still routes to `/auth/update-profile/` if `SHOW_COMPLETE_PROFILE_FORM=True` and user lacks first_name/last_name.

- `user_logged_in` signal handler that redirects to `CompleteProfileView` URL when conditions met. allauth respects redirect chaining via `LOGIN_REDIRECT_URL_HOOK` or signal-set session flag.
- `CompleteProfileView` itself can stay — it's a TemplateView with a form, no allauth interaction.

**Verify:** Existing test for the post-magic-link "complete profile" redirect still passes against the new wiring.

### Phase 8: Demolition + MIGRATION.md (½ day)

**Goal:** Delete the qux.auth views/forms/templates that allauth now owns; document the migration.

Delete:
- `QuxLoginView`, `QuxSignupView`, `QuxActivateView`, `QuxPasswordResetView` (+3 siblings), `QuxChangePasswordView`, `QuxSetPasswordView`, `MagicLinkRequestView`, `MagicLinkLoginView`.
- `BaseSignupForm`, `SignupForm`, `CustomAuthenticationForm`, `CustomPasswordResetForm`, `CustomSetPasswordForm`, `ChangePasswordForm`, `MagicLinkRequestForm`.
- `account_activation_token`, `magic_link_token` modules.
- `auth/views/shared.py` `is_blocked_domain` (moves to adapter); `get_or_create_user_for_email` (allauth handles get-or-create natively).

Keep:
- `CompleteProfileForm`, `CompleteProfileView` (post-first-login profile prompt).
- `CLIOTPRequestView`, `CLIOTPVerifyView` (CLI OTP API).
- Throttle classes for CLI OTP.
- `Profile` model (User profile data — separate from auth).

Update `MIGRATION.md` with:
- New URL paths (where bookmarks need updating; both old and new should work via aliases).
- Settings additions (`ACCOUNT_*`, `SOCIALACCOUNT_PROVIDERS`).
- Template override paths (where projects can customize).
- Signal-handler wiring (so projects with their own auth signals know about allauth's).
- Telemetry: catalog unchanged; firing site changed.

---

## Settings additions (rough shape)

```python
# settings.py — additions for allauth
INSTALLED_APPS = [
    # ...existing...
    "django.contrib.sites",  # allauth requires
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.linkedin_oauth2",
    "allauth.socialaccount.providers.apple",
    "allauth.socialaccount.providers.facebook",
]

MIDDLEWARE = [
    # ...existing...
    "allauth.account.middleware.AccountMiddleware",
]

SITE_ID = 1

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)

# Email-only auth (matches current qux behavior)
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_LOGIN_BY_CODE_ENABLED = True   # magic-link replacement
ACCOUNT_USERNAME_REQUIRED = False

# qux's bot defenses (via custom adapter + form)
ACCOUNT_ADAPTER = "qux.auth.adapters.QuxAccountAdapter"
ACCOUNT_FORMS = {
    "request_login_code": "qux.auth.forms.QuxRequestLoginCodeForm",
}

# Rate limits (replaces the bespoke cache-key code)
ACCOUNT_RATE_LIMITS = {
    "login_failed": "5/300s/ip",
    "login_by_code_request": "5/300s/key",
    "signup": "20/300s/ip",
    "reset_password": "5/300s/key",
}

LOGIN_REDIRECT_URL = "/"
ACCOUNT_LOGOUT_REDIRECT_URL = "/"

# Existing qux settings stay
BLOCKED_DOMAIN_FOR_MAGIC_LINK = ["aol.com", "hotmail.com"]   # consumed by adapter.clean_email
SHOW_COMPLETE_PROFILE_FORM = True
USE_MAGIC_LINK = True   # gates whether login-by-code is enabled

# Per-provider OAuth credentials (out-of-band setup)
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {"client_id": os.environ["GOOGLE_OAUTH_CLIENT_ID"],
                "secret": os.environ["GOOGLE_OAUTH_SECRET"], "key": ""},
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    },
    "linkedin_oauth2": {
        "APP": {"client_id": os.environ["LINKEDIN_OAUTH_CLIENT_ID"],
                "secret": os.environ["LINKEDIN_OAUTH_SECRET"], "key": ""},
        "SCOPE": ["r_liteprofile", "r_emailaddress"],
    },
    "apple": {
        "APP": {
            "client_id": os.environ["APPLE_SERVICE_ID"],
            "secret": os.environ["APPLE_KEY_ID"],
            "key": os.environ["APPLE_TEAM_ID"],
            "settings": {
                "certificate_key": os.environ["APPLE_PRIVATE_KEY"],
            },
        },
        "SCOPE": ["email", "name"],
    },
    "facebook": {
        "APP": {"client_id": os.environ["FACEBOOK_APP_ID"],
                "secret": os.environ["FACEBOOK_APP_SECRET"], "key": ""},
        "SCOPE": ["email"],
    },
}
```

---

## What this plan does NOT solve

- **CLI OTP migration:** `qux.auth.views.apiviews.CLIOTPRequestView` + `CLIOTPVerifyView` keep their bespoke implementation. These are no-browser flows; allauth doesn't have an analog. If we want to defer to a maintained library, look at `dj-rest-auth` — but that's a separate plan.
- **Existing user data migration:** if any production users have `username != email`, or if any have null emails, allauth's `email-as-username` assumption may not hold for them cleanly. Pre-migration audit needed: how many users have `username != email`? How many have `email IS NULL`? May need a one-time data migration to normalize before flipping the switch.
- **Existing magic-link tokens in flight:** users who clicked "send magic link" the moment we deploy will have an in-flight `magic_link_token` URL that no longer resolves. Either: deploy during low-traffic window, OR briefly run both flows (Phase 6 alias pattern handles this).
- **Template look-and-feel polish:** allauth's BS template overrides will be functional but probably need design polish to match the qjango look exactly. Defer to a UI session.

---

## Migration story for downstream

When this lands, projects need to:

1. **Add allauth deps** — `pip install qux[allauth]` or update requirements.
2. **Add the settings** documented in `MIGRATION.md` § Auth-Allauth.
3. **Run `manage.py migrate`** — allauth ships migrations for `EmailAddress`, `SocialApp`, `SocialAccount`, `SocialToken`.
4. **For each social provider they want enabled:** complete the provider's OAuth setup (out-of-band) and add credentials to env vars.
5. **Audit existing users for the email-as-username assumption** — script provided in `scripts/audit_user_email_uniqueness.py`.
6. **Test the auth flows in staging:** signup, login, password reset, magic link, social login per provider.
7. **Update any internal documentation** that referenced `/auth/login/` etc. — old URLs work via Phase 6 aliases but new URLs are canonical.

The CLI OTP flow at `/api/v1/auth/cli/...` is unchanged.

---

## Open questions to resolve before implementation

1. **Allauth version pin.** Need to confirm `ACCOUNT_LOGIN_BY_CODE_ENABLED` is in the version we pin (≥ 0.61 should work; verify).
2. **Email-as-username strict mode.** Are there existing users with non-email usernames? If yes, what's the migration strategy?
3. **Template override scope.** Override every allauth template, or accept allauth's defaults for the long-tail (e.g. email templates)? Recommendation: override the user-facing flow templates (login, signup, reset, magic-link request); accept allauth's defaults for low-traffic templates (email confirmation pages, etc.) — polish later.
4. **Social provider credentials.** Who has access to the Google/LinkedIn/Apple/Facebook developer accounts for the org? This is the prerequisite for Phase 5.
5. **MFA — in scope or not?** allauth supports it via the `[mfa]` extra. Could be added to this plan (Phase 9?) or deferred. Recommendation: defer; this plan is already a multi-day project.
6. **`BLOCKED_DOMAIN_FOR_MAGIC_LINK` semantics.** Currently blocks magic-link requests AND CLI OTP. After migration, the magic-link block lives in the allauth adapter; CLI OTP block lives in the qux.auth bespoke API view. Behavior identical, code lives in two places. OK or refactor to share?

---

## Estimate

| Phase | Effort | Risk |
|---|---|---|
| 1. Foundation (allauth installed, basic flows at /accounts/) | 1 day | low |
| 2. Templates (qjango BS5/BS4 overrides) | ½ day | low |
| 3. Magic link via login-by-code + bot adapter | ½ day | medium (allauth feature relatively new) |
| 4. Telemetry signal wiring | ½ day | low |
| 5. Social providers (4 providers) | 2 days (½ each) | high for Apple, low for others |
| 6. Back-compat URL aliases | ½ day | low |
| 7. CompleteProfileView signal redirect | ½ day | low |
| 8. Demolition + MIGRATION.md | ½ day | low |

**Total: 5-6 focused days.** Phasable — can land Phase 1+2 first as a foundation commit, then layer 3-8 incrementally.

---

## Decision needed before starting

Implementation of this plan is gated on the user confirming:

- (a) social-auth via allauth IS the priority (vs. e.g. extending the bespoke views with each provider individually — much worse but possible).
- (b) the email-as-username assumption is OK for existing users (or a data migration strategy is acceptable).
- (c) we accept the URL change to `/accounts/...` as canonical (with `/auth/...` aliases for back-compat).

If yes to all three: schedule the work as 5-6 focused days; do not interleave with other qux work.
