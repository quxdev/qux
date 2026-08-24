"""Unpack vendored asset bundles into src/qux/static/, then materialize the
stable-path mirrors the manifest declares.

Two steps, in order:

1. **Bundles.** Each zip in ``bundles/`` unpacks into src/qux/static/ under its
   own versioned tree. Idempotent via per-bundle marker files — but a marker is
   believed only when the bundle's files are actually on disk (see
   ``_is_unpacked``). A marker outliving its files is a real production failure
   mode: qux logged "skip bootstrap-icons (marker present)" on every boot while
   the files were gone.
2. **Aliases.** ``ALIASES`` declares version-independent paths (e.g.
   ``qux/js/bootstrap/``) mirrored from the versioned tree. These carry no
   marker: verifying ~30 paths per boot is cheap, and it means a partly deleted
   mirror heals on the next boot instead of staying broken.

Run via console script `qux-install-assets`, via `python -m qux._assets.install`,
or automatically by qux.apps.QuxConfig.ready on Django startup.
"""

from __future__ import annotations

import argparse
import contextlib
import logging
import os
import shutil
import sys
import zipfile
from pathlib import Path

from qux.telemetry import EVENTS, _context, emit, events

from .manifest import ALIASES, BUNDLES, Alias, Bundle

_log = logging.getLogger("qux")

_ASSETS_DIR = Path(__file__).resolve().parent
_BUNDLES_DIR = _ASSETS_DIR / "bundles"
_STATIC_DIR = _ASSETS_DIR.parent / "static"
_MARKERS_DIR = _STATIC_DIR / ".qux-bundles"  # one empty file per installed bundle


def _marker_for(bundle: Bundle) -> Path:
    return _MARKERS_DIR / bundle.filename


def _sentinel_for(bundle: Bundle) -> str | None:
    """One file member of the bundle zip, used as a witness that it is unpacked.

    Reads the zip's central directory (cheap — no decompression) and returns the
    lexicographically first non-directory member, so the witness is derived from
    the bundle instead of hardcoded per library. Returns None when the zip is
    absent or unreadable.

    Args:
        bundle: The manifest entry to inspect.

    Returns:
        A member path relative to src/qux/static/, or None.
    """
    src = _BUNDLES_DIR / bundle.filename
    try:
        with zipfile.ZipFile(src) as zf:
            names = sorted(n for n in zf.namelist() if not n.endswith("/"))
    except (OSError, zipfile.BadZipFile):
        return None
    return names[0] if names else None


def _is_unpacked(bundle: Bundle) -> bool:
    """True when the bundle's marker is present AND its files are still on disk.

    The marker alone is not trusted: deleting src/qux/static/<lib>/ (or shipping
    a wheel that never contained it) leaves a marker pointing at nothing, and a
    marker-only check then skips the unpack forever. When no sentinel can be
    derived — unreadable zip — the marker is trusted rather than re-unpacking on
    every call.

    Args:
        bundle: The manifest entry to check.

    Returns:
        True if the bundle needs no work.
    """
    if not _marker_for(bundle).exists():
        return False
    sentinel = _sentinel_for(bundle)
    if sentinel is None:
        return True
    return (_STATIC_DIR / sentinel).exists()


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

    if not force:
        if _is_unpacked(bundle):
            _log.info("skip %s %s (already unpacked)", bundle.name, bundle.version)
            return False
        if marker.exists():
            _log.warning(
                "qux: marker for %s %s present but its files are missing — re-unpacking",
                bundle.name,
                bundle.version,
            )

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


def _alias_pairs(alias: Alias) -> list[tuple[Path, Path]]:
    """Resolve one alias to concrete (source file, target file) pairs.

    Declared, not discovered: a name the manifest lists is returned whether or
    not the source file exists, so a mistyped or dropped name surfaces through
    ``missing_assets`` instead of vanishing without a word.

    Args:
        alias: The manifest entry to resolve.

    Returns:
        One pair per file the alias declares; empty only when the source
        directory itself is absent (its bundle is not unpacked yet).
    """
    source_dir = _STATIC_DIR / alias.source
    target_dir = _STATIC_DIR / alias.target
    if not source_dir.is_dir():
        return []

    if alias.names:
        sources = [source_dir / name for name in alias.names]
    else:
        sources = sorted(path for path in source_dir.iterdir() if path.is_file())

    return [(src, target_dir / src.name) for src in sources]


def _is_current(source: Path, target: Path) -> bool:
    """True when ``target`` already holds ``source``'s bytes.

    Existence alone is not enough. Mirror filenames do not carry a version
    (``bootstrap.bundle.min.js`` is the same name at 5.2.3 and 5.3.0), so a
    presence check would let a bumped bundle keep serving the previous
    library's bytes forever — silently, since the path resolves and
    ``collectstatic`` is happy. Identity is a hardlink to the same inode, or a
    copy that still matches on size and mtime (``shutil.copy2`` preserves both).

    Args:
        source: File inside the unpacked bundle tree.
        target: The mirror path.

    Returns:
        True when the mirror needs no work.
    """
    if not target.exists():
        return False
    try:
        if target.samefile(source):
            return True
        source_stat, target_stat = source.stat(), target.stat()
    except OSError:
        return False
    return (source_stat.st_size, source_stat.st_mtime) == (
        target_stat.st_size,
        target_stat.st_mtime,
    )


def _link_or_copy(source: Path, target: Path) -> None:
    """Materialize ``target`` from ``source``, preferring a hardlink.

    Hardlinks keep the mirror free of extra bytes; a copy is the fallback for
    filesystems (or cross-device layouts) that refuse them.

    Args:
        source: Existing file inside an unpacked bundle tree.
        target: Path to create; its parent is created and any existing file at
            the path is replaced.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        target.unlink()
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)


def install_aliases(*, force: bool = False) -> int:
    """Materialize every stable-path mirror the manifest declares.

    Deliberately marker-free: the check is a stat per declared path, so a mirror
    deleted by hand (or a `collectstatic --clear` reaching too far) is restored
    on the next boot rather than staying broken until someone passes --force.
    The same check refreshes a mirror left behind by a previous bundle version,
    which is what makes a downstream bundle bump a pin change and nothing else.

    Args:
        force: Rewrite every mirror, current or not.

    Returns:
        Count of files written.
    """
    written = 0
    for alias in ALIASES:
        for source, target in _alias_pairs(alias):
            if not source.is_file():
                _log.warning(
                    "qux: ALIASES declares %s but the bundle does not provide it",
                    source.relative_to(_STATIC_DIR),
                )
                continue
            if _is_current(source, target) and not force:
                continue
            _link_or_copy(source, target)
            written += 1
    if written:
        _log.info("mirrored %d file(s) into %s", written, _STATIC_DIR)
    return written


def missing_assets() -> list[str]:
    """Everything the manifest declares that the filesystem lacks.

    Covers every way the asset tree can be incomplete: a bundle zip missing from
    the package, a bundle not unpacked, an alias source directory absent, a
    declared source file the bundle does not provide, and a mirror that is
    missing or left over from a previous bundle version. Feeds the ``qux.W001``
    system check so a broken install is visible on every ``manage.py check``.

    Returns:
        Human-readable descriptions, one per missing thing; empty when the tree
        is complete.
    """
    missing: list[str] = []

    for bundle in BUNDLES:
        if not (_BUNDLES_DIR / bundle.filename).exists():
            missing.append(f"bundle zip not in package: {bundle.filename}")
        elif not _is_unpacked(bundle):
            missing.append(f"bundle not unpacked: {bundle.name} {bundle.version}")

    for alias in ALIASES:
        source_dir = _STATIC_DIR / alias.source
        if not source_dir.is_dir():
            missing.append(f"alias source missing: static/{alias.source}")
            continue
        for source, target in _alias_pairs(alias):
            if not source.is_file():
                missing.append(
                    f"alias source file missing: static/{source.relative_to(_STATIC_DIR)}"
                )
            elif not _is_current(source, target):
                missing.append(
                    f"alias target missing or stale: static/{target.relative_to(_STATIC_DIR)}"
                )

    return missing


def install_all(*, force: bool = False) -> int:
    """Unpack every bundle in the manifest, then materialize the aliases.

    Args:
        force: Re-unpack bundles and rewrite mirrors regardless of state.

    Returns:
        Count of bundles unpacked. Mirrored file count is logged, not returned —
        callers (and the tests) treat this as the bundle count.
    """
    count = 0
    for bundle in BUNDLES:
        if install_bundle(bundle, force=force):
            count += 1
    install_aliases(force=force)
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

    missing = missing_assets()
    if missing:
        print("qux-install-assets: incomplete asset tree:", file=sys.stderr)
        for item in missing:
            print(f"  - {item}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
