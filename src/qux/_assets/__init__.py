"""Vendor-asset bundles + install-time unpacking.

Third-party static libraries (bootstrap-icons, bootstrap, select2) are stored
as single zip files under src/qux/_assets/bundles/ to keep the repo file count
manageable and lib bumps reviewable. They unpack into src/qux/static/ at
install time via setup.py cmdclass overrides for `develop` and `install`.

If your editable install used PEP 660 (modern setuptools default) and the
cmdclass hook didn't fire, run:

    python -m qux._assets.install

or use the console script:

    qux-install-assets

Both are idempotent.
"""
