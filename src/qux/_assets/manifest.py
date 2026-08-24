"""Manifest of vendored asset bundles.

Each entry maps a bundle filename (under src/qux/_assets/bundles/) to its
unpack target relative to src/qux/static/. Each bundle's zip MUST contain a
top-level directory matching the lib name (e.g. `bootstrap/5.2.3/...` inside
bootstrap-5.2.3.zip), so all bundles unpack into src/qux/static/ directly.

ALIASES declares a second, version-independent layer: stable paths under
src/qux/static/ (e.g. `qux/js/bootstrap/`) mirrored from the versioned tree an
unpacked bundle produces (e.g. `bootstrap/5.2.3/js/`). Downstream templates and
CSS reference the stable path, so a version bump touches this file only.

Those mirrors used to be git symlinks into the bundle tree. That was
unpackageable: the bundle tree is gitignored and unpacked at install time, so
in a clean checkout the links dangled and setuptools silently dropped them from
the wheel — shipping a stylesheet whose @import chain 404'd in every downstream
project. They are materialized at unpack time now (see
qux._assets.install.install_aliases), and the mirror paths are gitignored like
any other build output.

Bumping a vendored library is a four-step change:

  1. Drop a new zip into src/qux/_assets/bundles/ (top-level dir = lib name).
  2. Update the BUNDLES entry below (filename + version).
  3. Update any ALIASES entry whose `source` names the old version.
  4. Delete the old zip from src/qux/_assets/bundles/.

Step 3 is enforced: qux.tests.test_static_references fails when an alias source
names a path no bundle zip contains.

The unpacked tree under src/qux/static/<lib>/ is gitignored — it's a build
output created at install time by qux.apps.QuxConfig.ready() (or manually
via `qux-install-assets`), not source.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Bundle:
    """A vendored zip archive that unpacks into src/qux/static/."""

    name: str  # Human-readable name, used in log output.
    filename: str  # File in src/qux/_assets/bundles/.
    version: str  # Upstream version this zip corresponds to.


BUNDLES: tuple[Bundle, ...] = (
    Bundle(
        name="bootstrap-icons",
        filename="bootstrap-icons-1.10.5.zip",
        version="1.10.5",
    ),
    Bundle(
        name="bootstrap",
        filename="bootstrap-5.2.3.zip",
        version="5.2.3",
    ),
    # bootstrap-4.4.1.zip is shipped in the repo for projects that still
    # depend on Bootstrap 4 templates, but is NOT auto-unpacked at install.
    # To enable: add a Bundle entry mirroring the 5.2.3 one above.
    Bundle(
        name="select2",
        filename="select2-4.1.0-rc.0.zip",
        version="4.1.0-rc.0",
    ),
    Bundle(
        name="qux-fonts",
        filename="qux-fonts-1.0.zip",
        version="1.0",
    ),
)


@dataclass(frozen=True)
class Alias:
    """A stable, version-independent mirror of files from an unpacked bundle.

    ``source`` and ``target`` are both directories relative to src/qux/static/.
    ``source`` lives inside a bundle's unpacked tree (so it carries the upstream
    version); ``target`` is the path downstream code references. An empty
    ``names`` mirrors every file directly in ``source``; otherwise only the
    named files.
    """

    source: str  # Directory under static/, inside an unpacked bundle.
    target: str  # Stable directory under static/.
    names: tuple[str, ...] = ()  # Empty = mirror every file in `source`.


ALIASES: tuple[Alias, ...] = (
    # The whole js directory, matching what the 14 tracked symlinks covered.
    # Sourcemaps included: a missing .map makes ManifestStaticFilesStorage
    # complain on every downstream collectstatic.
    Alias(source="bootstrap/5.2.3/js", target="qux/js/bootstrap"),
    # Not the whole css directory — static/bootstrap/5.2.3/css is 5.4 MB.
    # bootstrap.min.css names its sourcemap as a bare sibling filename, so the
    # two travel together.
    Alias(
        source="bootstrap/5.2.3/css",
        target="qux/css/bootstrap",
        names=("bootstrap.min.css", "bootstrap.min.css.map"),
    ),
    # The icon CSS references its webfonts as ../../../fonts/bootstrap-icons.woff2.
    # That resolves to static/fonts/ from bootstrap-icons/1.10.5/font/ and from
    # qux/css/fonts/ alike, so the mirrored bytes need no rewriting —
    # static/fonts/ is what the qux-fonts bundle provides.
    Alias(
        source="bootstrap-icons/1.10.5/font",
        target="qux/css/fonts",
        names=("bootstrap-icons.css", "bootstrap-icons.min.css"),
    ),
)
