"""Manifest of vendored asset bundles.

Each entry maps a bundle filename (under src/qux/_assets/bundles/) to its
unpack target relative to src/qux/static/. Each bundle's zip MUST contain a
top-level directory matching the lib name (e.g. `bootstrap/5.2.3/...` inside
bootstrap-5.2.3.zip), so all bundles unpack into src/qux/static/ directly.

Bumping a vendored library is a three-step change:

  1. Drop a new zip into src/qux/_assets/bundles/ (top-level dir = lib name).
  2. Update the BUNDLES entry below (filename + version).
  3. Delete the old zip from src/qux/_assets/bundles/.

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
