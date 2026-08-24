# qux/_assets

Vendored static asset bundles (Bootstrap, bootstrap-icons, select2, qux-fonts) shipped as zip files and unpacked into `src/qux/static/` at install time. Replaces the older "thousands of vendored static files in git" model.

## Layout

```
src/qux/_assets/
  bundles/          # the .zip archives (one per vendored library)
  manifest.py       # BUNDLES (what to unpack) + ALIASES (stable paths to mirror)
  install.py        # install_bundle / install_aliases / install_all + the CLI
```

Per-bundle marker files live at `src/qux/static/.qux-bundles/<bundle.zip>` (one empty file per successfully-unpacked bundle). Marker present **and** the bundle's files still on disk → idempotent skip. `--force` re-unpacks regardless.

The disk half of that check is not belt-and-braces. qux 0.8.2 shipped a wheel with no unpacked tree in it but a marker written by the first boot; every later boot logged `skip bootstrap-icons 1.10.5 (marker present)` while the files were absent, and nothing said so. `_is_unpacked()` now checks a sentinel — the lexicographically first file member of the zip, read from its central directory — so a marker that outlives its files triggers a re-unpack with a warning.

## Stable paths (ALIASES)

Downstream projects reference `qux/js/bootstrap/bootstrap.bundle.min.js`, not `bootstrap/5.2.3/js/bootstrap.bundle.min.js` — a version-independent path is part of qux's public surface, and a bundle bump must not touch downstream templates. `ALIASES` declares that layer: `source` (a directory inside an unpacked bundle) → `target` (the stable directory), optionally narrowed to specific `names`.

`install_aliases()` materializes them with `os.link` (falling back to `shutil.copy2`), so the mirror costs no extra bytes. It carries **no marker**: verifying ~30 paths is a stat each, and a mirror deleted by hand heals on the next boot instead of staying broken.

### Why not symlinks

Until 0.8.2 these stable paths were fourteen git-tracked symlinks pointing into `static/bootstrap/` and `static/bootstrap-icons/`. Those directories are gitignored build output, so in a clean checkout the links dangled and setuptools dropped them from the wheel without a word — while a dev machine with an already-unpacked tree built a wheel that contained real files. Every downstream project 404'd on Bootstrap's JS and every `bi bi-*` glyph. The mirror paths are gitignored now, and `qux.tests.test_static_references` fails if a static asset is ever tracked as a symlink again.

## When assets are missing

`missing_assets()` reports every gap — bundle zip absent from the package, bundle not unpacked, alias source directory missing, alias target not mirrored. `qux.checks` surfaces it as `qux.W001` on every `manage.py check` / `collectstatic` / `runserver`, and `qux-install-assets` exits 1 and prints the list. Loud on purpose: downstream projects using `ManifestStaticFilesStorage` get no unhashed fallback, so a silently-skipped unpack is a sitewide outage.

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

# 3. Update any ALIASES entry whose `source` names the old version
#    (e.g. bootstrap/5.2.3/js → bootstrap/5.3.0/js)

# 4. Delete the old zip
rm src/qux/_assets/bundles/bootstrap-5.2.3.zip

# 5. Force re-unpack so the new files land in src/qux/static/
qux-install-assets --force
```

Step 3 is enforced, not remembered: `qux.tests.test_static_references` fails when an alias `source` names a path no bundle zip contains, or a declared `name` the bundle does not have.

The unpacked tree under `src/qux/static/<lib>/` is gitignored — it's a build artifact, not source. Only the zips in `bundles/` are tracked.

## Why this shape

The previous vendoring model committed ~2,135 individual static files to the qux git history. Library version bumps were noisy (bootstrap-5.2.3 → 5.3.0 = thousands of file diffs). Switching to vendored zips cut tracked-file count by an order of magnitude and made bumps a single file replacement. Runtime cost is one zip extraction at first install plus a stat per aliased file on each boot — invisible in normal operation thanks to the marker-file idempotency.
