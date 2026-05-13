# `qux.telemetry`

Structured event emission on the `qux` logger channel. Single-channel design: everything qux emits — telemetry events, internal debug/info, lifecycle, asset unpack messages — goes through `logging.getLogger("qux")`. Operators wire one handler and get every signal qux produces.

## What `qux.telemetry` is for

**Product visibility, not user surveillance.** Event payloads carry what happened, the outcome, and generic categorical dims. They do NOT carry user identifiers, emails, IPs, user-agent strings, or duration measurements. The product team can answer "is feature X being used? is feature Y failing? are requests correlating?" without surveilling users. (Latency belongs in access logs, not event telemetry.)

## Per-project setup

`/var/log/<app>/qux.log` is the recommended sink. Copy this `LOGGING` block into your Django settings:

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "qux_json": {"()": "qux.telemetry.JsonFormatter"},
    },
    "handlers": {
        "qux_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/var/log/myapp/qux.log",
            "maxBytes": 50_000_000,
            "backupCount": 10,
            "formatter": "qux_json",
        },
    },
    "loggers": {
        # qux emits everything on this single channel.
        "qux": {"handlers": ["qux_file"], "level": "INFO", "propagate": False},
    },
}

MIDDLEWARE = [
    # MUST be first so events from later middleware/signals carry request_id.
    "qux.telemetry.middleware.QuxRequestIdMiddleware",
    # ... your other middleware
]
```

That's it. One logger, one handler.

## What's emitted (the catalog)

Every event is also a string constant on `qux.telemetry.EVENTS`. Use the constants in dashboards/alerts to get import-time typo failure instead of "wait, why are no alerts firing."

```python
from qux.telemetry import EVENTS
EVENTS.AUTH_LOGIN_SUCCESS  # "qux.auth.login_success"
```

| Event name | Payload | Emitted from |
|---|---|---|
| `qux.startup` | `version`, `boot_id`, `worker_pid` | `QuxConfig.ready()` (HTTP servers only) |
| `qux.assets.unpacked` | `ok`, `bundle`, `version`, `boot_id` | `_assets/install.install_bundle` |
| `qux.assets.unpack_failed` | `ok=False`, `bundle`, `error_class`, `boot_id` | same |
| `qux.migration.applied` | `app`, `qux_name`, `boot_id` | `post_migrate` (filtered to qux apps) |
| `qux.config.loaded` | `bootstrap`, `use_magic_link`, `boot_id` | `QuxConfig.ready()` — once per boot |
| `qux.auth.login_success` | `ok=True` | `user_logged_in` signal |
| `qux.auth.login_failed` | `ok=False`, `reason` | `QuxLoginView.form_invalid` |
| `qux.auth.signup` | `ok=True` | `QuxSignupView.post` (success branch) |
| `qux.auth.magic_link.requested` | `ok=True` | `MagicLinkRequestView.post` (success branch) |
| `qux.auth.magic_link.refused` | `ok=False`, `reason` | `MagicLinkRequestView.post` (refusal branches) |
| `qux.auth.magic_link.consumed` | `ok=True` | `MagicLinkLoginView.get` |
| `qux.auth.cli_otp.issued` | `ok=True`, `ttl_seconds` | `apiviews.CLIOTPRequestView.post` |
| `qux.auth.cli_otp.consumed` | `ok=True` | `apiviews.CLIOTPVerifyView.post` |
| `qux.auth.password_reset.requested` | `ok=True` | `QuxPasswordResetView.form_valid` |
| `qux.auth.password_reset.completed` | `ok=True` | `QuxSetPasswordView.post` |
| `qux.token.created` | `ok=True` | `CustomTokenCreateView.form_valid` |
| `qux.token.deleted` | `ok=True` | `CustomTokenDeleteView.form_valid` |

### `reason` enum values

- `qux.auth.login_failed.reason`: `bad_credentials`, `inactive`, `locked`, `unknown`. Django's default authentication form does NOT distinguish bad-password from unknown-user (deliberate: avoids leaking which accounts exist). Both bucket into `bad_credentials`.
- `qux.auth.magic_link.refused.reason`: `rate_limit`, `blocked_domain`, `bot_check`.
- `qux.assets.unpack_failed.error_class`: the exception class name (`FileNotFoundError`, `BadZipFile`, etc.).

### Catalog evolution policy

The catalog is **additive over time**: new events may be added; new `reason` enum values may appear within existing events. Renames or removals are deliberate breaking changes documented in `CHANGELOG.md` under a `## Telemetry catalog` heading — read it before bumping qux versions.

Pinning alerts to specific `reason` values (e.g. `reason == "rate_limit"`) is **at-your-own-risk** — the alert silently misses traffic if a new reason value is introduced. Better: alert on the parent event regardless of reason, then drill in via `jq` when investigating.

## Correlation: `request_id`, `trace_id`, `span_id`, `boot_id`

Events emitted during an HTTP request automatically carry:

- **`request_id`** — fresh `uuid4().hex` (32 chars) per request, set by `QuxRequestIdMiddleware`. Anonymous, ephemeral. Lets you grep all events for a single request.
- **`trace_id` + `span_id`** — parsed from the W3C `traceparent` header if upstream sent one. Qux does NOT start traces; it propagates context for sites that already use OTel/Datadog APM/Jaeger.

Lifecycle events (`qux.startup`, `qux.assets.*`, `qux.migration.applied`, `qux.config.loaded`) carry **`boot_id`** — a `uuid4().hex` set once per process at `QuxConfig.ready()`. Lets you `grep <boot_id>` to pull every lifecycle event from a single deploy.

`qux.startup` ALSO carries **`worker_pid`** (`os.getpid()`). Pre-fork servers (gunicorn `--workers=4`) emit one startup event per worker process, so a single deploy produces N startups. Dedupe by counting unique `boot_id` values OR aggregate per-worker by `worker_pid`.

## Querying the log file

```bash
# Event counts in the current log file
jq -r 'select(.event) | .event' /var/log/myapp/qux.log | sort | uniq -c | sort -rn

# Login failures grouped by reason
jq -r 'select(.event == "qux.auth.login_failed") | .reason' /var/log/myapp/qux.log | sort | uniq -c

# Events in a specific request (paste request_id from an error)
jq -c "select(.request_id == \"$REQ\")" /var/log/myapp/qux.log

# All events from a single deploy boot
jq -c "select(.boot_id == \"$BOOT\")" /var/log/myapp/qux.log

# Failures only (across all events)
jq -c 'select(.ok == false)' /var/log/myapp/qux.log

# Events in last N hours
jq -c --arg cutoff "$(date -u -v-24H +%FT%T)" 'select(.ts > $cutoff)' /var/log/myapp/qux.log
```

## Adding `user_id` to your own pipeline

Qux itself never adds user identifiers and exposes no setting to do so — that decision lives entirely with the operator's logging config, not with qux. If your project wants `user_id` attached to qux records:

```python
import logging
from threading import local

_REQ = local()  # set by your own middleware: _REQ.user_id = request.user.pk

class AddUserIdFilter(logging.Filter):
    def filter(self, record):
        record.user_id = getattr(_REQ, "user_id", None)
        return True

LOGGING["filters"] = {"add_user_id": {"()": "myapp.logging.AddUserIdFilter"}}
LOGGING["handlers"]["qux_file"]["filters"] = ["add_user_id"]
```

## Sampling

Not provided by qux. If you need to sample down a high-volume event, add a `logging.Filter` that selects/drops records based on `extra={"event": ...}`. Standard Python logging mechanism; no qux-specific knob.

## Reserved-name handling

Some natural payload names clash with `logging.LogRecord` standard attrs. `events.emit` resolves them at emit time (not deep inside `logger.handle()`):

- **Auto-renamed**: `name` → `qux_name`, `message` → `qux_message`, `module` → `qux_module`, `filename` → `qux_filename`. Documented in the catalog so operators query the renamed key.
- **Rejected with `ValueError`**: any other reserved attr (`pathname`, `levelname`, `funcName`, etc.). The exception names what to fix.

Dim names must match `^[a-z_][a-z0-9_]*$` — lowercase + underscores only. Event NAMES use dots (`qux.auth.login_failed`); dim NAMES do not, because some observability backends treat dotted dims as nested objects and others as flat keys.

## Patterns / conventions

- **Never decorate `dispatch`** with `@qux_event` — auth gating runs inside `dispatch` and the decorator would emit `ok=True` even for 302-to-login. Decorate `form_valid` / `get` / `post` instead.
- Qux's events are emitted via inline `events.emit(...)` calls (or named helpers in `events.py`). The `qux_event` decorator exists internally for "function returned cleanly = ok / raised = failed" cases like `Email.send`.
- **No public decorator API for downstream**. If your project wants its own structured events, use stdlib `logging` directly. Qux's `qux_event` is intentionally not exported from `qux.telemetry.__init__`.
