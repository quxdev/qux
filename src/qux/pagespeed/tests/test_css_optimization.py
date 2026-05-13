"""PageSpeed: CSS loading optimizations.

Validates that:
- CSS files in <head> use minified variants when available
- No render-blocking @import url() chains in head CSS files
- @font-face declarations prefer WOFF2 format (30-50% smaller than OTF)
- Bootstrap Icons CSS is loaded non-blocking (not via @import in head CSS)
"""

from django.test import SimpleTestCase

from qux.pagespeed.checks import (
    check_css_imports,
    check_css_minified,
    check_font_format_woff2,
    read_project_file,
)
from qux.pagespeed.config import BASE_TEMPLATE, FONT_CSS_FILES, HEAD_CSS_FILES


class TestCSSMinification(SimpleTestCase):
    """CSS files loaded in base template should use minified variants."""

    def test_base_template_uses_minified_css(self):
        """Base template should load .min.css when a minified version exists."""
        findings = check_css_minified(BASE_TEMPLATE)
        self.assertEqual(
            len(findings),
            0,
            "Unminified CSS loaded in base template:\n" + "\n".join(f"  {f[2]}" for f in findings),
        )


class TestCSSImportChains(SimpleTestCase):
    """CSS files in <head> must not use @import (creates render-blocking chains)."""

    def test_no_import_in_head_css(self):
        """CSS files loaded in <head> must not use @import url().

        @import creates a waterfall: browser downloads the CSS, parses it,
        discovers the @import, then downloads the imported file — all before
        rendering. Move imports to <link> tags in the template instead.
        """
        findings = check_css_imports(HEAD_CSS_FILES)
        self.assertEqual(
            len(findings),
            0,
            "Render-blocking @import found in head CSS:\n"
            + "\n".join(f"  {f[0]}:{f[1]} — {f[2]}" for f in findings),
        )

    def test_bootstrap_icons_not_in_site_css(self):
        """Bootstrap Icons should not be @imported in site.css.

        It should be loaded as a non-blocking <link> in the template instead.
        """
        content = read_project_file("common/css/site.css")
        self.assertNotIn(
            "bootstrap-icons",
            content,
            "Bootstrap Icons @import found in site.css — "
            "should be a non-blocking <link> in the base template",
        )


class TestFontFormatWOFF2(SimpleTestCase):
    """@font-face declarations should prefer WOFF2 format."""

    def test_all_fonts_prefer_woff2(self):
        """Project-owned @font-face blocks should list WOFF2 first in src."""
        findings = check_font_format_woff2(FONT_CSS_FILES)
        self.assertEqual(
            len(findings),
            0,
            "Font format issues:\n" + "\n".join(f"  {f[0]}: {f[1]} — {f[2]}" for f in findings),
        )
