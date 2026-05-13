# `qux.seo` — SEO scaffolding for Django views

Per-page metadata + per-site auditing. Exposes a mixin for views to set canonical/title/description, and models to track audit runs.

## Models

- **`SEOSite`** — `OneToOneField(Site)` extension; per-domain default metadata (default title, description, OG image).
- **`SEOPage`** — per-URL overrides; matched on path.
- **`SEOAudit`** — one row per audit run.
- **`SEOAuditURL`** — per-URL row inside an audit run; stores findings.
- **`SEOModel`** — abstract base used by `SEOSite`/`SEOPage` (subclass of `qux.models.QuxModel`).

## Mixin

```python
from qux.seo.mixin import SEOMixin

class HomeView(SEOMixin, TemplateView):
    template_name = "home.html"
    canonical_url = "/"
    seo_title = "Welcome to Foo"
```

The mixin populates the template context with `seo` (a dict of resolved title, description, canonical URL, OG fields). Templates use it via `{% include 'seo/_meta.html' %}` in `<head>`.

## Scanner

`scanner.py` provides the audit logic — fetches a URL with `requests`, parses with `beautifulsoup4`, extracts `<title>`, `<meta>`, headings, images-without-alt, broken links. Used by the audit run flow.

## Management commands

None. Audits are kicked off programmatically (or via `manage.py shell`).

## When to use

- Use `SEOMixin` on every public-facing TemplateView.
- Use `SEOPage` to override metadata for individual URLs without a code change.
- Use the audit model + scanner when you want a recurring SEO health check.
