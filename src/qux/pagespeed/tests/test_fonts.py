"""PageSpeed: every @font-face must declare font-display: swap.

Prevents Flash of Invisible Text (FOIT) by showing fallback fonts while
custom fonts load.  Google Lighthouse flags any @font-face block that is
missing ``font-display: swap`` (or another non-default value).

Bootstrap Icons intentionally uses ``font-display: block`` to avoid
rendering gibberish while the icon font loads — that is the correct
choice for icon fonts and is excluded from the swap requirement.
"""

from django.test import SimpleTestCase

from qux.pagespeed.checks import FONT_FACE_RE, check_font_display, read_project_file
from qux.pagespeed.config import FONT_CSS_FILES, ICON_FONT_CSS


class TestFontDisplaySwap(SimpleTestCase):
    """Every project-owned @font-face must use font-display: swap."""

    def test_all_font_face_blocks_have_swap(self):
        """Project-owned @font-face blocks must use font-display: swap."""
        findings = check_font_display(FONT_CSS_FILES, icon_font_css=None)
        self.assertEqual(
            len(findings),
            0,
            f"{len(findings)} font-display issue(s). "
            "Run: python manage.py pagespeed --detailed",
        )

    def test_icon_font_uses_block(self):
        """Bootstrap Icons should use font-display: block (not swap)."""
        self.assertIsNotNone(ICON_FONT_CSS, "bootstrap-icons.css not found via glob")
        css = read_project_file(ICON_FONT_CSS)
        blocks = FONT_FACE_RE.findall(css)
        self.assertTrue(blocks, "No @font-face found in bootstrap-icons.css")
        for block in blocks:
            self.assertIn(
                "font-display: block",
                block,
                "Bootstrap Icons should use font-display: block for icon fonts",
            )

    def test_no_font_face_without_font_display(self):
        """No @font-face block should omit font-display entirely."""
        all_files = list(FONT_CSS_FILES)
        if ICON_FONT_CSS:
            all_files.append(ICON_FONT_CSS)
        for css_file in all_files:
            css = read_project_file(css_file)
            for block in FONT_FACE_RE.findall(css):
                self.assertIn(
                    "font-display",
                    block,
                    f"@font-face missing font-display property in {css_file}",
                )
