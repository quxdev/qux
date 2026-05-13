# `qux.pagespeed` — front-end performance checks

Reusable check functions + config for Google PageSpeed-style auditing of a Django project's templates and static assets. Consumed by both the qux test suite and the `pagespeed` management command.

## Modules

- **`checks.py`** — pure functions, no DB. Scans template directories and static files for common performance issues:
  - `check_font_display` — flag webfonts missing `font-display: swap` / `optional`.
  - `check_lazy_loading` — flag `<img>` tags missing `loading="lazy"`.
  - `check_alt_attributes` — flag `<img>` missing `alt`.
  - `check_image_dimensions` — flag `<img>` missing width/height.
  - `check_script_loading` — flag `<script>` without `async` / `defer` (with allowlist).
  - `check_resource_hints` — flag missing `<link rel="preload">` for above-the-fold critical assets.
- **`config.py`** — project-specific allowlists / exceptions / file paths. Override per-project.

## Use

Programmatic:

```python
from qux.pagespeed.checks import check_lazy_loading

issues = check_lazy_loading(lazy_exceptions=["<img class='no-lazy'"])
```

Management command (when wired):

```bash
python manage.py pagespeed
```

## Tests

`tests/` covers each check function with fixture HTML.

## When to use

- Run as part of CI to keep the front-end honest as templates evolve.
- Use the per-check exception arguments to whitelist intentional violations (e.g. logo images that shouldn't lazy-load).
