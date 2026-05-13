"""Reusable PageSpeed check functions and utilities.

Provides template discovery, content scanning, regex patterns, and check
functions for common PageSpeed issues.  These are consumed by both the
test suite and the ``pagespeed`` management command.

Project-specific configuration (file paths, exceptions, allowlists) lives
in ``qux.pagespeed.config``.
"""

import glob
import os
import re

from django.apps import apps
from django.conf import settings

# ---------------------------------------------------------------------------
# Template discovery
# ---------------------------------------------------------------------------


def get_template_dirs():
    """Return template directories from Django settings + project apps.

    Only includes project-owned apps (whose path is under BASE_DIR) so
    third-party packages like ``django.contrib.admin`` are excluded.

    Note: only ``.html`` files are scanned — other template extensions
    (``.txt``, ``.xml``, ``.email``) are not rendered in browsers and
    therefore irrelevant to PageSpeed.
    """
    dirs = []
    for conf in settings.TEMPLATES:
        for d in conf.get("DIRS", []):
            dirs.append(os.path.relpath(d, settings.BASE_DIR))
    base_dir_str = str(settings.BASE_DIR)
    for app_config in apps.get_app_configs():
        if not app_config.path.startswith(base_dir_str):
            continue
        tpl_dir = os.path.join(app_config.path, "templates")
        if os.path.isdir(tpl_dir):
            dirs.append(os.path.relpath(tpl_dir, settings.BASE_DIR))
    return sorted(set(dirs))


# ---------------------------------------------------------------------------
# Content scanning
# ---------------------------------------------------------------------------


def scan_template_content(regex):
    """Walk all template dirs, match *regex* against full file content.

    Yields ``(relpath, line_no, match)`` for every match.  Handles tags
    that span multiple lines (e.g. ``<img\\n  src="...">``).
    """
    for tpl_dir in get_template_dirs():
        base = os.path.join(settings.BASE_DIR, tpl_dir)
        if not os.path.isdir(base):
            continue
        for root, _dirs, files in os.walk(base):
            for fname in files:
                if not fname.endswith(".html"):
                    continue
                filepath = os.path.join(root, fname)
                relpath = os.path.relpath(filepath, settings.BASE_DIR)
                with open(filepath, encoding="utf-8") as fh:
                    content = fh.read()
                for match in regex.finditer(content):
                    line_no = content[: match.start()].count("\n") + 1
                    yield relpath, line_no, match


def read_project_file(relpath):
    """Read a file relative to BASE_DIR and return its contents."""
    path = os.path.join(settings.BASE_DIR, relpath)
    with open(path, encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE | re.DOTALL)

SCRIPT_SRC_RE = re.compile(
    r"""<script\b([^>]*)src=(["'])(.*?)\2([^>]*)>""",
    re.IGNORECASE | re.DOTALL,
)

FONT_FACE_RE = re.compile(r"@font-face\s*\{[^}]+\}", re.DOTALL)

CSS_IMPORT_RE = re.compile(r"@import\s+url\(", re.IGNORECASE)

FONT_SRC_RE = re.compile(r"src:\s*([^;]+);", re.DOTALL)

HARDCODED_STATIC_RE = re.compile(
    r"""(?:src|href)=(["'])(/static/[^"']+)\1""",
    re.IGNORECASE | re.DOTALL,
)

HARDCODED_MEDIA_RE = re.compile(
    r"""(?:src|href)=(["'])(/media/[^"']+)\1""",
    re.IGNORECASE | re.DOTALL,
)

HARDCODED_CSS_STATIC_RE = re.compile(
    r"""url\(\s*(["']?)(/static/[^"')]+)\1\s*\)""",
    re.IGNORECASE,
)

HARDCODED_DOMAIN_STATIC_RE = re.compile(
    r"""https?://[a-zA-Z0-9.-]+\{%\s*static\b""",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Icon font discovery
# ---------------------------------------------------------------------------


def find_icon_font_css():
    """Locate bootstrap-icons CSS via glob (avoids hardcoding the version)."""
    pattern = os.path.join(
        settings.BASE_DIR,
        "qux/static/bootstrap-icons/*/font/bootstrap-icons.css",
    )
    matches = glob.glob(pattern)
    if matches:
        return os.path.relpath(matches[0], settings.BASE_DIR)
    return None


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------


def check_font_display(font_css_files, icon_font_css):
    """Return findings for @font-face blocks with incorrect font-display.

    Returns list of ``(css_file, font_name, message)`` tuples.
    """
    findings = []
    for css_file in font_css_files:
        path = os.path.join(settings.BASE_DIR, css_file)
        if not os.path.exists(path):
            findings.append((css_file, "N/A", "FILE NOT FOUND"))
            continue
        css = read_project_file(css_file)
        for block in FONT_FACE_RE.findall(css):
            family = re.search(r"font-family:\s*([^;]+)", block)
            name = family.group(1).strip() if family else "unknown"
            if "font-display" not in block:
                findings.append((css_file, name, "missing font-display"))
            elif "font-display: swap" not in block:
                findings.append((css_file, name, "should use font-display: swap"))

    if icon_font_css:
        path = os.path.join(settings.BASE_DIR, icon_font_css)
        if os.path.exists(path):
            css = read_project_file(icon_font_css)
            for block in FONT_FACE_RE.findall(css):
                if "font-display: block" not in block:
                    findings.append((icon_font_css, "icon-font", "should use font-display: block"))
    return findings


def check_lazy_loading(lazy_exceptions=None):
    """Return list of ``(relpath, line_no, tag)`` for images missing loading="lazy"."""
    exceptions = lazy_exceptions or set()
    missing = []
    for relpath, line_no, match in scan_template_content(IMG_TAG_RE):
        tag = match.group(0)
        if (relpath, line_no) in exceptions:
            continue
        if 'loading="lazy"' not in tag and "loading='lazy'" not in tag:
            missing.append((relpath, line_no, tag))
    return missing


def check_alt_attributes(alt_exceptions=None):
    """Return list of ``(relpath, line_no, tag)`` for images missing or empty alt."""
    exceptions = alt_exceptions or set()
    missing = []
    for relpath, line_no, match in scan_template_content(IMG_TAG_RE):
        tag = match.group(0)
        if (relpath, line_no) in exceptions:
            continue
        tag_lower = tag.lower()
        if "alt=" not in tag_lower or re.search(r"""alt=["']\s*["']""", tag_lower):
            missing.append((relpath, line_no, tag))
    return missing


def check_image_dimensions():
    """Return ``(total, missing_list)`` for images without width/height.

    *missing_list* contains ``(relpath, line_no, tag)`` tuples so callers
    can report exactly which templates need fixing.
    """
    total = 0
    missing = []
    for relpath, line_no, match in scan_template_content(IMG_TAG_RE):
        tag = match.group(0)
        total += 1
        tag_lower = tag.lower()
        has_width = "width=" in tag_lower or "width:" in tag_lower
        has_height = "height=" in tag_lower or "height:" in tag_lower
        if not (has_width and has_height):
            missing.append((relpath, line_no, tag))
    return total, missing


def check_script_loading(allowlist=None, skip_prefixes=None):
    """Return list of ``(relpath, line_no, src)`` for scripts missing async/defer."""
    allowlist = allowlist or set()
    skip_prefixes = skip_prefixes or ("qux/",)
    missing = []
    for relpath, line_no, match in scan_template_content(SCRIPT_SRC_RE):
        if any(relpath.startswith(p) for p in skip_prefixes):
            continue
        src = match.group(3)
        if any(pattern in src for pattern in allowlist):
            continue
        attrs = match.group(1) + match.group(4)
        if not re.search(r"\bdefer\b|\basync\b", attrs, re.IGNORECASE):
            missing.append((relpath, line_no, src))
    return missing


def check_resource_hints(base_template_relpath, viewport_search_paths):
    """Return list of finding strings for missing preconnect/dns-prefetch/viewport."""
    findings = []
    base_path = os.path.join(settings.BASE_DIR, base_template_relpath)
    if not os.path.exists(base_path):
        findings.append(f"{base_template_relpath}: FILE NOT FOUND")
        return findings

    html = read_project_file(base_template_relpath)

    if 'rel="preconnect"' not in html:
        findings.append('Missing <link rel="preconnect"> in base template')
    if not re.search(r'<link\s+rel="preconnect"\s+href="[^"]*googletagmanager\.com[^"]*"', html):
        findings.append("Missing preconnect to Google Tag Manager origin")
    if 'rel="dns-prefetch"' not in html:
        findings.append('Missing <link rel="dns-prefetch"> in base template')

    found_viewport = False
    for path in viewport_search_paths:
        full = os.path.join(settings.BASE_DIR, path) if not os.path.isabs(path) else path
        if os.path.exists(full):
            with open(full, encoding="utf-8") as fh:
                if "viewport" in fh.read():
                    found_viewport = True
                    break
    if not found_viewport:
        findings.append("No viewport meta tag found in template chain")

    return findings


def check_css_minified(template_relpath):
    """Return findings for CSS files loaded unminified in the base template.

    Checks that ``<link>`` tags loading ``.css`` files use ``.min.css``
    variants when available on disk.
    """
    findings = []
    content = read_project_file(template_relpath)
    link_re = re.compile(r"""<link[^>]+href=(["'])([^"']+\.css)\1""", re.IGNORECASE | re.DOTALL)
    for match in link_re.finditer(content):
        href = match.group(2)
        if "{%" in href or "{{" in href or href.startswith("http"):
            continue
        if ".min.css" in href:
            continue

    static_re = re.compile(r"""\{%\s*static\s+['"]([^'"]+\.css)['"]\s*%\}""", re.IGNORECASE)
    for match in static_re.finditer(content):
        css_path = match.group(1)
        if ".min.css" in css_path:
            continue
        min_path = css_path.replace(".css", ".min.css")
        for prefix_name, prefix_dir in settings.STATICFILES_DIRS:
            candidate = os.path.join(prefix_dir, css_path.replace(f"{prefix_name}/", "", 1))
            min_candidate = os.path.join(prefix_dir, min_path.replace(f"{prefix_name}/", "", 1))
            if os.path.exists(candidate) and os.path.exists(min_candidate):
                findings.append(
                    (
                        template_relpath,
                        css_path,
                        f"Unminified CSS loaded: {css_path} — use {min_path} instead",
                    )
                )
                break
    return findings


def check_css_imports(css_files):
    """Return findings for @import url() in CSS files loaded in <head>.

    CSS @import creates a render-blocking chain: the browser must download
    the CSS file, parse it, discover the @import, then download the imported
    file before rendering can begin.
    """
    findings = []
    for css_file in css_files:
        path = os.path.join(settings.BASE_DIR, css_file)
        if not os.path.exists(path):
            continue
        content = read_project_file(css_file)
        for match in CSS_IMPORT_RE.finditer(content):
            line_no = content[: match.start()].count("\n") + 1
            findings.append((css_file, line_no, "render-blocking @import url()"))
    return findings


def check_font_format_woff2(font_css_files):
    """Return findings for @font-face blocks that don't prefer WOFF2.

    WOFF2 is 30-50%% smaller than OTF/TTF.  Each @font-face should list
    WOFF2 as the first src format.
    """
    findings = []
    for css_file in font_css_files:
        path = os.path.join(settings.BASE_DIR, css_file)
        if not os.path.exists(path):
            continue
        css = read_project_file(css_file)
        for block in FONT_FACE_RE.findall(css):
            family = re.search(r"font-family:\s*([^;]+)", block)
            name = family.group(1).strip() if family else "unknown"
            src_match = FONT_SRC_RE.search(block)
            if not src_match:
                continue
            src_value = src_match.group(1)
            if "woff2" not in src_value:
                findings.append((css_file, name, "no WOFF2 format in src — add .woff2 file"))
            elif src_value.index("woff2") > src_value.index("url("):
                formats = re.findall(r"format\(['\"](\w+)['\"]\)", src_value)
                if formats and formats[0] != "woff2":
                    findings.append((css_file, name, "WOFF2 should be listed first in src"))
    return findings


def check_hardcoded_static_urls(exceptions=None):
    """Return ``(relpath, line_no, url)`` for hardcoded /static/ paths."""
    exceptions = exceptions or set()
    findings = []
    for relpath, line_no, match in scan_template_content(HARDCODED_STATIC_RE):
        if (relpath, line_no) in exceptions:
            continue
        findings.append((relpath, line_no, match.group(2)))
    for relpath, line_no, match in scan_template_content(HARDCODED_CSS_STATIC_RE):
        if (relpath, line_no) in exceptions:
            continue
        findings.append((relpath, line_no, match.group(2)))
    return findings


def check_hardcoded_media_urls(exceptions=None):
    """Return ``(relpath, line_no, url)`` for hardcoded /media/ paths."""
    exceptions = exceptions or set()
    findings = []
    for relpath, line_no, match in scan_template_content(HARDCODED_MEDIA_RE):
        if (relpath, line_no) in exceptions:
            continue
        findings.append((relpath, line_no, match.group(2)))
    return findings


def check_hardcoded_domain_in_static(exceptions=None):
    """Return ``(relpath, line_no, snippet)`` for hardcoded domains before {%% static %%}."""
    exceptions = exceptions or set()
    findings = []
    for relpath, line_no, match in scan_template_content(HARDCODED_DOMAIN_STATIC_RE):
        if (relpath, line_no) in exceptions:
            continue
        findings.append((relpath, line_no, match.group(0)))
    return findings


# ---------------------------------------------------------------------------
# Summary formatting
# ---------------------------------------------------------------------------


def format_summary(checks):
    """Build grouped summary lines from a list of ``(category, title, findings)`` tuples.

    Returns a list of strings (no trailing newline).
    """
    lines = []
    current_category = None
    for category, title, findings in checks:
        if category != current_category:
            lines.append(category)
            current_category = category
        count = len(findings)
        if count:
            lines.append(f"    [FAIL] {title} [!{count}]")
        else:
            lines.append(f"    [PASS] {title}")
    return lines
