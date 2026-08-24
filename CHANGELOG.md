# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/). Versions before 0.8.3 predate this
file — their history is in `git log` and in [MIGRATION.md](MIGRATION.md), and is not
reconstructed here.

## [Unreleased]

## 0.8.3 - 2026-08-24

### Fixed
- **_assets**: stable static paths (`qux/js/bootstrap/`, `qux/css/fonts/bootstrap-icons*.css`) were tracked as git symlinks into the gitignored, install-time bundle tree. In a clean checkout those links dangle, so setuptools dropped them from the wheel without a word: every downstream project 404'd on `bootstrap.bundle.min.js` and on every `bi bi-*` glyph. The paths are now declared by `manifest.ALIASES` and materialized at unpack time by `install.install_aliases()`. Downstream projects need no template or settings change — bump the pin and redeploy.
- **_assets**: a bundle marker outliving its files made every boot log `skip <bundle> (marker present)` while the files were absent. `install_bundle` now verifies a sentinel member from the zip and re-unpacks with a warning when the marker lies.
- **drf/log**: ship `qux_api_log/css/qux_api_log.css`. The admin change-list template referenced it but qux never contained it, so the Chart.js canvas (`maintainAspectRatio: false`) laid out zero pixels tall.

### Added
- **checks**: `qux.W001` system check names every declared asset the install lacks — missing bundle zip, un-unpacked bundle, absent alias source, missing or stale mirror — on every `manage.py check`, `collectstatic`, and `runserver`.
- **templatetags**: `{% qux_static %}` takes `optional=True`, rendering nothing when the file is absent. Used for the theme hooks qux references but does not ship (`css/forms.css`, `css/listview.css`, the cover assets), which 404'd hard under `ManifestStaticFilesStorage`.
- **tests**: `qux.tests.test_static_references` gates the whole class of defect — every template and CSS reference must resolve against what a *fresh install* holds, every `ALIASES` entry must match a bundle member, no static asset may be tracked as a symlink, and every generated path must be both gitignored and excluded from package data.

### Changed
- **_assets**: bumping a vendored library is now a four-step change — the new third step updates any `ALIASES` entry naming the old version, enforced by the reference tests.
- **static**: `qux/css/qux.css` imports `bootstrap/bootstrap.min.css` (the stable path) instead of `../../bootstrap/5.2.3/…`. No bundle version literal remains outside `manifest.py`.
