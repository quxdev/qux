# DRF API Logging (qux.drf.log)

This module records DRF request/response metadata with minimal performance impact and footprint.

## Features

- Async persistence via Celery
- Per-user allow/deny with caching (default: logging enabled for all users)
- Sampling of 2xx; always log errors
- Data minimization: redaction, truncation, error-only response bodies
- Retention via management command

## Settings (prefix: `DRF_TRACKING_`)

- `ENABLED` (bool, default `True`): Master switch
- `ALWAYS_LOG_ERRORS` (bool, default `True`)
- `MAX_SIZE` (int, default `4096`): Field size cap for dict payloads
- `MAX_BODY_BYTES` (int, default `4096`): Truncate `data`/`response`
- `STORE_RESPONSE_ON_ERRORS_ONLY` (bool, default `True`)
- `RETENTION_DAYS` (int, default `14`)
- `TASK_QUEUE` (str, default `"vulcan"`): Celery queue for persistence

## Per-user control

Use `APILoggingRule` in Django admin. Rules are cached; saves/Deletes invalidate cache.

Semantics: `enabled=True` means logging is on for the user; `enabled=False` disables it. With no rule, logging is enabled (subject to sampling).

Automation:
- New users automatically get a default rule (`enabled=True`).
- Backfill existing users: `python manage.py backfill_api_logging_rules`

## Usage

- Add `LoggingMixin` (or keep `VulcanLoggingMixin`) to DRF views.
- Ensure Celery worker runs with the configured queue.

## Retention

Purge logs daily via cron or Celery beat:

```bash
python manage.py delete_drf_log --days_num 14
```

If `--days_num` omitted, `RETENTION_DAYS` is used.

## Notes

- For large binary uploads, set `DECODE_REQUEST_BODY=False`.
- Sampling is deterministic per-path to smooth variance.

