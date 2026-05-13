"""Minimal setup.py shim.

All packaging metadata lives in pyproject.toml. The only reason this file
exists is to register cmdclass overrides for `develop` and `install` so that
qux's vendored static asset bundles auto-unpack at install time.

Modern editable installs (PEP 660, setuptools >= 64) bypass the `develop`
cmdclass and use `editable_wheel` instead — we override that too. If a future
build backend bypasses every hook, users can always re-trigger manually:

    qux-install-assets

(provided by the [project.scripts] entry in pyproject.toml).
"""
from __future__ import annotations

import sys
from pathlib import Path

from setuptools import setup
from setuptools.command.develop import develop
from setuptools.command.install import install

# Make qux._assets importable from the source tree for the cmdclass hooks.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))


def _install_assets_quietly() -> None:
    """Run qux._assets.install.install_all and never raise into setuptools."""
    try:
        from qux._assets.install import install_all  # noqa: WPS433  (import inside func)
    except ImportError as exc:  # pragma: no cover
        print(f"qux setup.py: could not import qux._assets ({exc}); "
              "skipping asset unpack. Run `qux-install-assets` manually.",
              file=sys.stderr)
        return
    try:
        install_all()
    except Exception as exc:  # noqa: BLE001 — packaging hooks must not block install
        print(f"qux setup.py: asset unpack failed ({exc}); "
              "run `qux-install-assets` to retry.", file=sys.stderr)


class _DevelopWithAssets(develop):
    def run(self) -> None:  # type: ignore[override]
        super().run()
        _install_assets_quietly()


class _InstallWithAssets(install):
    def run(self) -> None:  # type: ignore[override]
        super().run()
        _install_assets_quietly()


_cmdclass = {
    "develop": _DevelopWithAssets,
    "install": _InstallWithAssets,
}

# editable_wheel is the PEP 660 backend command used by modern `pip install -e`.
# It exists in setuptools >= 64. Wrap it if available so the asset unpack still
# fires on modern editable installs.
try:
    from setuptools.command.editable_wheel import editable_wheel
except ImportError:  # pragma: no cover
    pass
else:

    class _EditableWheelWithAssets(editable_wheel):  # type: ignore[misc]
        def run(self) -> None:  # type: ignore[override]
            super().run()
            _install_assets_quietly()

    _cmdclass["editable_wheel"] = _EditableWheelWithAssets


setup(cmdclass=_cmdclass)
