"""Project-specific PageSpeed configuration.

Constants and wiring that tie the reusable check functions in
``qux.pagespeed.checks`` to this project's template and CSS layout.
Adjust paths and exceptions here when the project structure changes.
"""

from qux.pagespeed.checks import (
    check_alt_attributes,
    check_css_imports,
    check_css_minified,
    check_font_display,
    check_font_format_woff2,
    check_hardcoded_domain_in_static,
    check_hardcoded_media_urls,
    check_hardcoded_static_urls,
    check_image_dimensions,
    check_lazy_loading,
    check_resource_hints,
    check_script_loading,
    find_icon_font_css,
)

# CSS files that declare custom @font-face rules (project-owned)
FONT_CSS_FILES = [
    "common/css/typography.css",
    "qux/static/qux/css/fonts/roboto.css",
    "qux/static/qux/css/fonts/inter.css",
    "qux/static/qux/css/fonts/courier.css",
    "qux/static/qux/css/fonts/metropolis.css",
]

ICON_FONT_CSS = find_icon_font_css()

# Templates where lazy loading is intentionally omitted (above-the-fold
# hero images, sponsor carousels loaded via JS, etc.).
LAZY_LOADING_EXCEPTIONS = {
    ("apps/gizmo/templates/initiatives/initiatives_home.html", 102),
    (
        "apps/gizmo/templates/initiatives/frwrd_blck_futrs/includes/hero_section.html",
        5,
    ),
    (
        "apps/gizmo/templates/initiatives/frwrd_blck_futrs/includes/hero_section.html",
        20,
    ),
    ("apps/gizmo/templates/common/sponsors.html", 23),
    ("qux/templates/_navbar.html", 6),
}

# Images where alt cannot be detected by the regex (e.g. ``>`` inside a
# Django template tag prematurely closes the ``<img>`` match).
ALT_ATTRIBUTE_EXCEPTIONS = {
    ("apps/gizmo/templates/landing.html", 436),
}

# Scripts where lack of defer/async is acceptable.
SCRIPT_ALLOWLIST = set()

# Template paths under qux/ that we cannot modify
QUX_TEMPLATE_PREFIX = "qux/"

BASE_TEMPLATE = "templates/_blank.html"
VIEWPORT_SEARCH_PATHS = [
    BASE_TEMPLATE,
    "qux/templates/_blank.html",
    "qux/seo/templates/_seo.html",
    "templates/base.html",
]

# CSS files loaded in the base template <head> that should not use @import
HEAD_CSS_FILES = [
    "common/css/site.css",
    "common/css/typography.css",
]


def run_all_checks():
    """Run every PageSpeed check and return a list of ``(category, title, findings)`` tuples."""
    _dim_total, dim_findings = check_image_dimensions()
    return [
        (
            "FONTS",
            "@font-face must declare font-display",
            check_font_display(FONT_CSS_FILES, ICON_FONT_CSS),
        ),
        (
            "FONTS",
            "@font-face should prefer WOFF2 format",
            check_font_format_woff2(FONT_CSS_FILES),
        ),
        ("URLS", "hardcoded /static/ paths", check_hardcoded_static_urls()),
        ("URLS", "hardcoded /media/ paths", check_hardcoded_media_urls()),
        (
            "URLS",
            "hardcoded domain before {% static %}",
            check_hardcoded_domain_in_static(),
        ),
        (
            "IMAGES",
            'missing loading="lazy"',
            check_lazy_loading(LAZY_LOADING_EXCEPTIONS),
        ),
        (
            "IMAGES",
            "missing or empty alt attribute",
            check_alt_attributes(ALT_ATTRIBUTE_EXCEPTIONS),
        ),
        ("IMAGES", "missing explicit width/height (CLS)", dim_findings),
        ("SCRIPTS", "missing async or defer", check_script_loading(SCRIPT_ALLOWLIST)),
        (
            "CSS",
            "unminified CSS in base template",
            check_css_minified(BASE_TEMPLATE),
        ),
        (
            "CSS",
            "render-blocking @import in head CSS",
            check_css_imports(HEAD_CSS_FILES),
        ),
        (
            "RESOURCE HINTS",
            "preconnect, dns-prefetch, viewport",
            check_resource_hints(BASE_TEMPLATE, VIEWPORT_SEARCH_PATHS),
        ),
    ]
