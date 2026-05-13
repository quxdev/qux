"""Unpack vendored asset bundles into src/qux/static/.

Idempotent via per-bundle marker files: skips bundles whose marker is
present. Run via console script `qux-install-assets`, via
`python -m qux._assets.install`, or automatically by qux.apps.QuxConfig.ready
on Django startup.
"""

from __future__ import annotations

import argparse
import contextlib
import logging
import sys
import zipfile
from pathlib import Path

from qux.telemetry import EVENTS, _context, emit, events

from .manifest import BUNDLES, Bundle

_log = logging.getLogger("qux")

_ASSETS_DIR = Path(__file__).resolve().parent
_BUNDLES_DIR = _ASSETS_DIR / "bundles"
_STATIC_DIR = _ASSETS_DIR.parent / "static"
_MARKERS_DIR = _STATIC_DIR / ".qux-bundles"  # one empty file per installed bundle


def _marker_for(bundle: Bundle) -> Path:
    return _MARKERS_DIR / bundle.filename


def install_bundle(bundle: Bundle, *, force: bool = False) -> bool:
    """Unpack one bundle into src/qux/static/. Returns True if it actually
    unpacked, False if the marker file said it's already done.

    Each zip is expected to contain a top-level directory matching the lib
    (e.g. `bootstrap/5.2.3/...`), so extraction lands in
    `src/qux/static/<lib>/<rest>` directly.
    """
    src = _BUNDLES_DIR / bundle.filename
    marker = _marker_for(bundle)

    if not src.exists():
        _emit_unpack_failed(bundle, error_class="FileNotFoundError")
        raise FileNotFoundError(f"Bundle missing: {src}")

    if marker.exists() and not force:
        _log.info("skip %s %s (marker present)", bundle.name, bundle.version)
        return False

    try:
        _STATIC_DIR.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(src) as zf:
            zf.extractall(_STATIC_DIR)

        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
    except BaseException as exc:
        _emit_unpack_failed(bundle, error_class=type(exc).__name__)
        raise

    _log.info("unpacked %s %s → %s", bundle.name, bundle.version, _STATIC_DIR)
    _emit_unpacked(bundle)
    return True


def _emit_unpacked(bundle: Bundle) -> None:
    """Emit qux.assets.unpacked (best-effort; never raises)."""
    with contextlib.suppress(Exception):
        emit(
            EVENTS.ASSETS_UNPACKED,
            ok=True,
            bundle=bundle.name,
            version=bundle.version,
            boot_id=_context.boot_id.get() or "unknown",
        )


def _emit_unpack_failed(bundle: Bundle, *, error_class: str) -> None:
    """Emit qux.assets.unpack_failed (best-effort; never raises)."""
    with contextlib.suppress(Exception):
        events.assets_unpack_failed(
            bundle=bundle.name,
            error_class=error_class,
            boot_id_value=_context.boot_id.get() or "unknown",
        )


def install_all(*, force: bool = False) -> int:
    """Unpack every bundle in the manifest. Returns count of bundles unpacked."""
    count = 0
    for bundle in BUNDLES:
        if install_bundle(bundle, force=force):
            count += 1
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="qux-install-assets",
        description="Unpack qux's vendored static asset bundles.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-unpack every bundle, ignoring marker files.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Log to stderr at INFO level.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(message)s",
    )

    try:
        count = install_all(force=args.force)
    except (FileNotFoundError, zipfile.BadZipFile) as exc:
        print(f"qux-install-assets: {exc}", file=sys.stderr)
        return 1

    print(f"qux: unpacked {count} of {len(BUNDLES)} bundle(s) into {_STATIC_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
