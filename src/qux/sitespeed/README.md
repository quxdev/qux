# `qux.sitespeed` — infrastructure delivery audit

HTTP/2, TLS, DNS, compression, security headers, CDN cache, cookie flags, and certificate metrics for a single URL endpoint. Sister to `qux.pagespeed` (which audits the rendered HTML), this audits the network/transport layer.

## Module

- **`endpoint.py`** — defines `Endpoint(url, timeout=10, parse_html=True)`. Collects everything in one go via `httpx`; exposes `.status()` (PASS/WARN/FAIL) and `.data` (dict of all metrics).

## Use

Programmatic:

```python
from qux.sitespeed.endpoint import Endpoint

site = Endpoint("https://example.com", timeout=10, parse_html=True)
print(site.status())   # "PASS" / "WARN" / "FAIL"
print(site.data)       # dict: tls_version, hsts_max_age, h2, etc.
```

Management command:

```bash
python manage.py sitespeed --url https://example.com --cdn https://cdn.example.com
python manage.py sitespeed --url https://example.com --cdn https://cdn.example.com --json
python manage.py sitespeed --url https://example.com --cdn https://cdn.example.com --compact
```

The `--cdn` URL is audited with `parse_html=False` (just the headers + TLS, no body parse).

## Security headers checked

`Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`, `Referrer-Policy`, `Permissions-Policy` — and any others enumerated at the top of `endpoint.py`.

## When to use

- Pre-deploy smoke check that staging has TLS / HSTS / compression configured.
- Periodic audit (cron) to catch CDN cache header regressions.
- One-shot during incident triage to compare prod vs staging delivery characteristics.
