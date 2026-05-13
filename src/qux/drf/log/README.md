# DRF API Logging (qux.drf.log)

Records DRF request/response metadata via Python's stdlib logging on the **`qux.drf`** channel. No celery, no broker, no DB INSERT per request unless you opt in.

## Architecture

`LoggingMixin` builds a payload dict from the request/response (path, method, status, user, duration, headers, body) and emits one structured record per request:

```python
logging.getLogger("qux.drf").log(
    level,                    # INFO on 2xx/3xx, WARNING on 4xx/5xx
    "request",
    extra={"event": "request", "path": ..., "method": ..., "status_code": ..., ...},
)
```

What happens to the record is entirely operator's choice via Django's `LOGGING` config — file, JSON to ELK/Datadog/Loki, syslog, the opt-in `APIRequestLogDBHandler` (DB persistence), or any combination.

## Quick start

```python
# In a DRF view
from qux.drf.log.mixins import LoggingMixin

class MyView(LoggingMixin, ViewSet):
    ...
```

Without any `LOGGING` configuration, records still emit — they just don't go anywhere visible (root logger). Wire a handler:

```python
# settings.py — minimal: log to a rotating file
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
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

## Recipe: keep DB-backed logs (feature parity with the old behavior)

`APIRequestLogDBHandler` writes each record to the `APIRequestLog` ORM model — opt-in handler that gives you the pre-2026 behavior end-to-end:

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "qux_drf_db": {"class": "qux.drf.log.handlers.APIRequestLogDBHandler"},
    },
    "loggers": {
        "qux.drf": {"handlers": ["qux_drf_db"], "level": "INFO", "propagate": False},
    },
}
```

Synchronous INSERT per request (~1–3 ms). For async dispatch wrap in `QueueHandler` + listener thread — stdlib pattern, no celery needed.

## Recipe: per-user filtering

The old `APILoggingRule` ORM model is no longer consulted by the mixin (it stays in the schema for historical querying). Per-user filtering is now a `logging.Filter`:

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

```python
LOGGING = {
    "filters": {
        "only_my_users": {
            "()": "myapp.log_filters.OnlyUsersFilter",
            "user_ids": [42, 99, 1337],
        },
    },
    "handlers": {
        "qux_drf_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/var/log/myapp/api-requests.log",
            "filters": ["only_my_users"],
        },
    },
    "loggers": {
        "qux.drf": {"handlers": ["qux_drf_file"], "level": "INFO", "propagate": False},
    },
}
```

Filter against any source — DB lookup, cache, env var, settings list. Decision lives entirely in the operator's logging config.

## Recipe: ship to Datadog / ELK / Loki

```python
LOGGING = {
    "formatters": {
        "json": {"()": "qux.telemetry.JsonFormatter"},  # see qux.telemetry
    },
    "handlers": {
        "qux_drf_stdout": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "loggers": {
        "qux.drf": {"handlers": ["qux_drf_stdout"], "level": "INFO", "propagate": False},
    },
}
```

Then ship stdout to your aggregator via the standard pipeline (Vector, Fluentd, Datadog agent). This is what mature shops actually do — DB-backed request logs don't scale past low volume.

## Settings (prefix: `DRF_TRACKING_`)

- `ENABLED` (bool, default `True`) — master switch
- `ALWAYS_LOG_ERRORS` (bool, default `True`)
- `MAX_SIZE` (int, default `4096`) — field size cap
- `MAX_BODY_BYTES` (int, default `4096`) — truncate `data`/`response`
- `STORE_RESPONSE_ON_ERRORS_ONLY` (bool, default `True`)
- `RETENTION_DAYS` (int, default `14`) — used by the prune management command

## Levels

| Outcome | Level |
|---|---|
| `status_code < 400` | `INFO` |
| `status_code >= 400` | `WARNING` |

Filter by level in your handler config (e.g. WARNING-only file for an "API errors" alert pipeline).

## What changed (May 2026)

- **Celery dependency dropped.** The mixin no longer dispatches via `@shared_task`; it calls `logger.info()` directly.
- **DB INSERT moved to opt-in.** `APIRequestLog` model stays in the schema and remains queryable for historical data; `APILoggingRule` model stays as well. Neither is written to by the mixin anymore. Add `APIRequestLogDBHandler` to your `LOGGING` config to restore DB writes.
- **Per-user rules → `logging.Filter`.** Operator-side, not DB-backed (unless your filter consults the DB).
- **Sink choice → operator.** qux.drf is the channel; what consumes it is your decision, not qux's prescription.

## Migration notes

- Tables are NOT dropped. Historical data stays queryable. Decide on your own cadence whether to keep the tables, drop them, or have a downstream Handler write to them.
- If you previously relied on the celery worker for log persistence, either wire `APIRequestLogDBHandler` (synchronous DB writes) OR pipe stdout to a log aggregator (recommended at any scale > a few req/s).
- `DRF_TRACKING_LOG_QUEUE` setting is removed (was celery-only).

## Retention

For projects keeping `APIRequestLog` table populated via `APIRequestLogDBHandler`:

```bash
python manage.py delete_drf_log --days_num 14
```

If `--days_num` omitted, `DRF_TRACKING_RETENTION_DAYS` is used.
