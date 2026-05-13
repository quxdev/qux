"""
SEO scanner — fetches a website's sitemap, crawls all URLs, extracts and
validates SEO tags, and stores timestamped results in the database.

Usage::

    from qux.seo.scanner import scan_site
    audit = scan_site("example.com")
"""

import logging
import time
from urllib.parse import urlparse
from xml.etree import ElementTree

from django.conf import settings
from django.utils import timezone

import requests
from bs4 import BeautifulSoup

from .models import SEOAudit, SEOAuditURL

logger = logging.getLogger("qux")

# ---------------------------------------------------------------------------
# SEO extraction patterns
# ---------------------------------------------------------------------------

# SEO_PATTERNS = {
#     "title": r"<title>(.*?)</title>",
#     "meta_description": r'name="description"\s+content="([^"]*)"',
#     "canonical": r'rel="canonical"\s+href="([^"]*)"',
#     "og_url": r'property="og:url"\s+content="([^"]*)"',
#     "og_site_name": r'property="og:site_name"\s+content="([^"]*)"',
#     "og_title": r'property="og:title"\s+content="([^"]*)"',
#     "og_description": r'property="og:description"\s+content="([^"]*)"',
#     "og_image": r'property="og:image"\s+content="([^"]*)"',
#     "twitter_card": r'name="twitter:card"\s+content="([^"]*)"',
#     "twitter_title": r'name="twitter:title"\s+content="([^"]*)"',
#     "twitter_description": r'name="twitter:description"\s+content="([^"]*)"',
#     "twitter_image": r'name="twitter:image"\s+content="([^"]*)"',
# }

META_TAGS_MAP = {
    "description": "meta_description",
    "twitter:card": "twitter_card",
    "twitter:title": "twitter_title",
    "twitter:description": "twitter_description",
    "twitter:image": "twitter_image",
    "og:url": "og_url",
    "og:site_name": "og_site_name",
    "og:title": "og_title",
    "og:description": "og_description",
    "og:image": "og_image",
}

# Tags that must have non-empty values on every public page.
SEO_REQUIRED = [
    "title",
    "meta_description",
    "canonical",
    "og_url",
    "og_title",
    "og_description",
    "og_image",
]

REQUEST_TIMEOUT = 15  # seconds

# Polite-scanner defaults. Override via settings ``QUX_SEO_REQUEST_DELAY_MS``,
# ``QUX_SEO_USER_AGENT``, ``QUX_SEO_MAX_URLS``. Without these the scanner can
# fire thousands of back-to-back requests at the target — anti-abuse / WAF
# triggers, target's logs see DDoS-like burst, even on the operator's own
# production site.
DEFAULT_REQUEST_DELAY_MS = 250
DEFAULT_USER_AGENT = "qux-seo-scanner (+https://github.com/quxdev/qux)"
DEFAULT_MAX_URLS = 10000


def _request_delay_seconds() -> float:
    return (
        max(0, int(getattr(settings, "QUX_SEO_REQUEST_DELAY_MS", DEFAULT_REQUEST_DELAY_MS)))
        / 1000.0
    )


def _user_agent() -> str:
    return getattr(settings, "QUX_SEO_USER_AGENT", DEFAULT_USER_AGENT)


def _max_urls() -> int:
    return int(getattr(settings, "QUX_SEO_MAX_URLS", DEFAULT_MAX_URLS))


def _polite_get(url: str) -> requests.Response:
    """``requests.get`` wrapper that sets a clear User-Agent. Caller handles delay."""
    return requests.get(
        url,
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": _user_agent()},
    )


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------


# def extract_seo(html):
#     """Extract SEO tag values from rendered HTML into a dict."""
#     values = {}
#     for key, pattern in SEO_PATTERNS.items():
#         match = re.search(pattern, html, re.DOTALL)
#         values[key] = match.group(1).strip() if match else None
#     return values


def extract_seo(html):
    soup = BeautifulSoup(html, "html.parser")
    data = {
        "title": (soup.title.string.strip() if soup.title and soup.title.string else None),
        "canonical": (link := soup.find("link", rel="canonical")) and link.get("href"),
    }
    # Initialize all mapped keys to None so callers can rely on their presence
    for key in META_TAGS_MAP.values():
        data.setdefault(key, None)
    for tag in soup.find_all("meta"):
        content = tag.get("content")
        if not content:
            continue
        if (name := tag.get("name")) in META_TAGS_MAP or (
            name := tag.get("property")
        ) in META_TAGS_MAP:
            data[META_TAGS_MAP[name]] = content
    return data


def check_seo_quality(seo):
    """Check individual tag value quality. Returns list of (severity, msg)."""
    issues = []
    title = seo.get("title") or ""
    if title and len(title.strip("| ")) < 2:
        issues.append(("warning", f"title looks generic: '{title}'"))

    meta_desc = seo.get("meta_description") or ""
    if meta_desc and not 50 <= len(meta_desc) <= 160:
        issues.append(
            (
                "warning",
                f"meta description length {len(meta_desc)} chars (recommend 50-160)",
            )
        )

    for tag, key in [("og:image", "og_image"), ("twitter:image", "twitter_image")]:
        val = seo.get(key) or ""
        if val and val in ("/media/", "/media/None"):
            issues.append(("error", f"{tag} is invalid: '{val}'"))

    canonical = seo.get("canonical") or ""
    if canonical and not canonical.startswith(("http://", "https://")):
        issues.append(("warning", f"canonical is not an absolute URL: '{canonical}'"))
    return issues


def check_seo_consistency(seo, path):
    """Cross-validate SEO tags against each other. Returns list of (severity, msg)."""
    issues = []
    canonical = seo.get("canonical") or ""
    og_url = seo.get("og_url") or ""

    if canonical and not canonical.endswith(path):
        issues.append(("warning", f"canonical '{canonical}' does not end with '{path}'"))
    if og_url and canonical and og_url != canonical:
        issues.append(("warning", f"og:url '{og_url}' != canonical '{canonical}'"))

    pairs = [
        ("og_title", "title", "og:title not found within <title>"),
        ("og_description", "meta_description", "og:description != meta description"),
        ("twitter_title", "og_title", "twitter:title != og:title"),
        (
            "twitter_description",
            "og_description",
            "twitter:description != og:description",
        ),
        ("og_image", "twitter_image", "og:image != twitter:image"),
    ]
    for key_a, key_b, msg in pairs:
        val_a = seo.get(key_a) or ""
        val_b = seo.get(key_b) or ""
        if val_a and val_b and val_a != val_b and val_a not in val_b:
            issues.append(("warning", msg))
    return issues


def validate_seo(seo, path):
    """Validate SEO values for presence, quality, and cross-consistency.

    Returns a list of ``(severity, message)`` tuples where *severity* is
    ``"error"`` (required tag missing / invalid) or ``"warning"``
    (quality / consistency issue).
    """
    issues = []
    for tag in SEO_REQUIRED:
        if not seo.get(tag):
            issues.append(("error", f"missing or empty: {tag}"))
    issues.extend(check_seo_quality(seo))
    issues.extend(check_seo_consistency(seo, path))
    return issues


# ---------------------------------------------------------------------------
# Sitemap helpers
# ---------------------------------------------------------------------------


def urls_from_sitemap(xml_content):
    """Parse <loc> elements from a sitemap XML string/bytes.

    Handles both sitemap index files (containing other sitemaps) and
    regular sitemaps (containing page URLs).
    """
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    root = ElementTree.fromstring(xml_content)
    return [loc.text for loc in root.findall(".//sm:loc", ns)]


def fetch_sitemap_urls(domain, scheme="https"):
    """Fetch and parse all URLs from a domain's sitemap.xml.

    Follows sitemap index files one level deep.
    """
    sitemap_url = f"{scheme}://{domain}/sitemap.xml"
    logger.info("Fetching sitemap: %s", sitemap_url)

    resp = _polite_get(sitemap_url)
    resp.raise_for_status()

    urls = urls_from_sitemap(resp.content)
    delay = _request_delay_seconds()

    # Check if this is a sitemap index (URLs point to other sitemaps)
    all_page_urls = []
    for url in urls:
        if url.endswith(".xml"):
            if delay:
                time.sleep(delay)
            try:
                sub_resp = _polite_get(url)
                sub_resp.raise_for_status()
                all_page_urls.extend(urls_from_sitemap(sub_resp.content))
            except requests.RequestException:
                logger.warning("Failed to fetch sub-sitemap: %s", url)
        else:
            all_page_urls.append(url)

    return all_page_urls


# ---------------------------------------------------------------------------
# Core scanner
# ---------------------------------------------------------------------------


def audit_urls(domain, pages):
    """Audit a list of pre-fetched pages and store results.

    This is the core audit engine used by both :func:`scan_site` (which
    fetches via ``requests``) and test suites (which fetch via Django's
    test client).

    Args:
        domain: The domain being audited (stored on the ``SEOAudit``).
        pages: Iterable of ``(path, status_code, html)`` tuples.  *html*
            should be an empty string for non-200 responses.

    Returns:
        The completed ``SEOAudit`` instance with all ``SEOAuditURL``
        records saved.
    """
    pages = list(pages)
    audit = SEOAudit.objects.create(
        domain=domain,
        status="running",
        total_urls=len(pages),
    )

    canonicals_seen = {}
    total_errors = 0
    total_warnings = 0

    for path, status_code, html in pages:
        seo = extract_seo(html) if html else {}
        issues = validate_seo(seo, path) if seo else [("error", "page not reachable")]

        errors = [msg for sev, msg in issues if sev == "error"]
        warnings = [msg for sev, msg in issues if sev == "warning"]

        canonical = seo.get("canonical") or ""
        if canonical:
            canonicals_seen.setdefault(canonical, []).append(path)

        total_errors += len(errors)
        total_warnings += len(warnings)

        SEOAuditURL.objects.create(
            audit=audit,
            url=path,
            status_code=status_code,
            title=seo.get("title"),
            meta_description=seo.get("meta_description"),
            canonical=seo.get("canonical"),
            og_url=seo.get("og_url"),
            og_title=seo.get("og_title"),
            og_description=seo.get("og_description"),
            og_image=seo.get("og_image"),
            og_site_name=seo.get("og_site_name"),
            twitter_card=seo.get("twitter_card"),
            twitter_title=seo.get("twitter_title"),
            twitter_description=seo.get("twitter_description"),
            twitter_image=seo.get("twitter_image"),
            errors=errors,
            warnings=warnings,
        )

    # Flag duplicate canonicals
    for canonical, paths in canonicals_seen.items():
        if len(paths) > 1:
            dup_msg = f"duplicate canonical '{canonical}' shared by: {', '.join(paths)}"
            for path in paths:
                url_result = audit.results.filter(url=path).first()
                if url_result:
                    url_result.errors = url_result.errors + [dup_msg]
                    url_result.save(update_fields=["errors"])
                    total_errors += 1

    audit.total_errors = total_errors
    audit.total_warnings = total_warnings
    audit.status = "completed"
    audit.dtm_audited = timezone.now()
    audit.save(update_fields=["total_errors", "total_warnings", "status", "dtm_audited"])

    logger.info(
        "SEO audit complete for %s: %d URLs, %d errors, %d warnings",
        domain,
        audit.total_urls,
        audit.total_errors,
        audit.total_warnings,
    )

    return audit


def scan_site(domain, scheme="https"):
    """Run a full SEO audit on a website.

    Fetches ``/sitemap.xml``, discovers all page URLs, fetches each page
    via HTTP, and delegates to :func:`audit_urls` for extraction,
    validation, and storage.

    Args:
        domain: The domain to audit (e.g. ``"example.com"``).
        scheme: URL scheme, ``"https"`` (default) or ``"http"``.

    Returns:
        The ``SEOAudit`` instance with all results saved.
    """
    try:
        page_urls = fetch_sitemap_urls(domain, scheme=scheme)
    except requests.RequestException as exc:
        logger.error("Failed to fetch sitemap for %s: %s", domain, exc)
        return SEOAudit.objects.create(domain=domain, status="failed")

    cap = _max_urls()
    if len(page_urls) > cap:
        logger.warning(
            "Sitemap returned %d URLs; capping at QUX_SEO_MAX_URLS=%d to avoid hammering target.",
            len(page_urls),
            cap,
        )
        page_urls = page_urls[:cap]

    delay = _request_delay_seconds()
    pages = []
    for index, page_url in enumerate(page_urls):
        if index and delay:
            time.sleep(delay)

        parsed = urlparse(page_url)
        path = parsed.path or "/"

        try:
            resp = _polite_get(page_url)
            status_code = resp.status_code
            html = resp.text if status_code == 200 else ""
        except requests.RequestException as exc:
            logger.warning("Failed to fetch %s: %s", page_url, exc)
            status_code = None
            html = ""

        pages.append((path, status_code, html))

    return audit_urls(domain, pages)


def format_report(audit):
    """Format an SEOAudit into a human-readable report string."""
    duration = ""
    if audit.dtm_audited:
        elapsed = (audit.dtm_audited - audit.dtm_created).total_seconds()
        duration = f"  |  Duration: {elapsed:.1f}s"

    lines = [
        f"SEO Audit Report: {audit.domain}",
        f"Date: {audit.dtm_created:%Y-%m-%d %H:%M:%S}",
        "=" * 60,
        f"URLs scanned: {audit.total_urls}  |  "
        f"Errors: {audit.total_errors}  |  Warnings: {audit.total_warnings}"
        f"{duration}",
        "",
    ]

    for result in audit.results.all().order_by("url"):
        has_issues = result.errors or result.warnings
        if not has_issues:
            continue
        lines.append(f"  {result.url}")
        for msg in result.errors:
            lines.append(f"    [error  ] {msg}")
        for msg in result.warnings:
            lines.append(f"    [warning] {msg}")
        lines.append("")

    if audit.total_errors == 0 and audit.total_warnings == 0:
        lines.append("All pages pass SEO validation.")

    return "\n".join(lines) + "\n"
