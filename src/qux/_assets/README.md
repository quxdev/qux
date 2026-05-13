# qux/_assets

Vendored static asset bundles (Bootstrap, bootstrap-icons, select2, qux-fonts) shipped as zip files and unpacked into `src/qux/static/` at install time. Replaces the older "thousands of vendored static files in git" model.

## Layout

```
src/qux/_assets/
  bundles/          # the .zip archives (one per vendored library)
  manifest.py       # BUNDLES list — name, filename, version per bundle
  install.py        # install_bundle / install_all + the qux-install-assets CLI
```

Per-bundle marker files live at `src/qux/static/.qux-bundles/<bundle.zip>` (one empty file per successfully-unpacked bundle). Marker present → idempotent skip. `--force` re-unpacks regardless.

## How it runs

Three entry points produce the same effect:

1. **Automatic on Django startup.** `qux.apps.QuxConfig.ready()` calls `install_all()`, so any project with `qux` in `INSTALLED_APPS` gets bundles unpacked the first time `runserver`/`gunicorn`/etc. boots.
2. **`qux-install-assets` console script.** Installed by pip; useful for "I just pulled new bundles and don't want to wait for ready()."
3. **`python -m qux._assets.install [--force] [-v]`.** Same thing, no console-script setup needed.

All three emit `qux.assets.unpacked` (success) or `qux.assets.unpack_failed` telemetry events on the `qux` logger channel.

## Bumping a vendored library

```bash
# 1. Drop the new zip in (top-level dir inside zip MUST match the lib name)
cp ~/Downloads/bootstrap-5.3.0.zip src/qux/_assets/bundles/

# 2. Update BUNDLES in manifest.py — change filename + version

# 3. Delete the old zip
rm src/qux/_assets/bundles/bootstrap-5.2.3.zip

# 4. Force re-unpack so the new files land in src/qux/static/
qux-install-assets --force
```

The unpacked tree under `src/qux/static/<lib>/` is gitignored — it's a build artifact, not source. Only the zips in `bundles/` are tracked.

## Why this shape

The previous vendoring model committed ~2,135 individual static files to the qux git history. Library version bumps were noisy (bootstrap-5.2.3 → 5.3.0 = thousands of file diffs). Switching to vendored zips cut tracked-file count by an order of magnitude and made bumps a single file replacement. Runtime cost is one zip extraction at first install — invisible in normal operation thanks to the marker-file idempotency.
