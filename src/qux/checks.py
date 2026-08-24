"""Django system checks for qux.

Importing this module registers the checks; ``qux.apps.QuxConfig.ready`` does
that import. The one check here reports an incomplete static asset tree.

Why a check and not a log line: qux's assets are unpacked at runtime from
vendored zips, so "the files aren't there" is a state a downstream project can
actually reach — a wheel built without the bundles, a `collectstatic --clear`
that reached too far, a read-only site-packages that silently failed the
unpack. Downstream projects on ``ManifestStaticFilesStorage`` get no unhashed
fallback for a missing file, so that state is a sitewide 404, and it must be
visible without anyone reading boot logs.
"""

from __future__ import annotations

from django.core.checks import Warning as DjangoWarning
from django.core.checks import register

from qux._assets.install import missing_assets

W001_ID = "qux.W001"


@register()
def check_static_assets(**kwargs):
    """Report every static asset qux declares but cannot find on disk.

    Args:
        **kwargs: Django's check arguments (``app_configs``, ``databases``),
            all passed by keyword and none of them used — the asset tree is
            global, so no app or database filter narrows it.

    Returns:
        A single ``qux.W001`` warning listing what is missing, or an empty list.
    """
    missing = missing_assets()
    if not missing:
        return []

    listed = "\n  - ".join(missing)
    return [
        DjangoWarning(
            "qux static assets are missing — templates and stylesheets "
            f"referencing them will 404:\n  - {listed}",
            hint=(
                "Run `qux-install-assets` (or `python -m qux._assets.install`). "
                "If it keeps failing, the qux install directory is probably not "
                "writable; unpack the bundles at build time instead."
            ),
            id=W001_ID,
        )
    ]
