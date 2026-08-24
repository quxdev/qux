# Handover — qux ships static references it does not package

**Repo to work in:** `/Users/pushpendratripathi/Workspace/1e9advisors/qux` (adjust to your checkout; upstream `github.com/quxdev/qux`)
**Target release:** `0.8.3`
**Downstream projects must need zero changes.** That constraint drove every decision below.
**Investigated from:** the `zeus` project, which hit the bug in production on 2026-08-17. All findings below were verified there and in the qux tree; nothing is assumed.

---

## 1. What is broken

qux 0.8.2's wheel contains a stylesheet, `qux/static/qux/css/qux.css`, whose import chain reaches
`qux/css/fonts/bootstrap-icons.min.css` — a file the wheel does not contain. Same for all twelve
`qux/js/bootstrap/*` paths, including `bootstrap.bundle.min.js`, which qux's own `qux.html` loads.

Every downstream project therefore 404s on bootstrap's JS and on every `bi bi-*` icon glyph. In zeus
this took out sitewide dropdowns and the mobile navbar toggle.

### Root cause

Fourteen paths were tracked in git as **symlinks into the bundle tree**:

```
src/qux/static/qux/css/fonts/bootstrap-icons.css      -> ../../../bootstrap-icons/1.10.5/font/bootstrap-icons.css
src/qux/static/qux/css/fonts/bootstrap-icons.min.css  -> ../../../bootstrap-icons/1.10.5/font/bootstrap-icons.min.css
src/qux/static/qux/js/bootstrap/bootstrap.bundle.js       -> ../../../bootstrap/5.2.3/js/bootstrap.bundle.js
src/qux/static/qux/js/bootstrap/bootstrap.bundle.js.map   -> …
src/qux/static/qux/js/bootstrap/bootstrap.bundle.min.js   -> …
src/qux/static/qux/js/bootstrap/bootstrap.bundle.min.js.map
src/qux/static/qux/js/bootstrap/bootstrap.esm.js          (+ .map)
src/qux/static/qux/js/bootstrap/bootstrap.esm.min.js      (+ .map)
src/qux/static/qux/js/bootstrap/bootstrap.js              (+ .map)
src/qux/static/qux/js/bootstrap/bootstrap.min.js          (+ .map)
```

`src/qux/static/bootstrap/` and `src/qux/static/bootstrap-icons/` are gitignored **and** listed in
`[tool.setuptools.exclude-package-data]`, by design: they are unpacked from
`src/qux/_assets/bundles/*.zip` at install time. So the symlink targets never exist when the wheel is
built from a clean checkout, the links are dangling, and setuptools drops them without a word.

Two consequences worth stating explicitly:

1. **Nothing in the packaging config is wrong.** The symlinks contradict a correct config.
2. **The wheel was non-deterministic.** Built on a dev machine whose tree was already unpacked, the
   links resolve and setuptools copies real files in. Built in CI from a clean clone, they vanish.
   That is why this shipped unnoticed for months, and why dev checkouts could never reproduce it.

### Reproduce before changing anything

```bash
cd <qux>
git ls-files -s src/qux/static | awk '$1=="120000"{print $4}'   # the 14 symlinks, mode 120000

T=$(mktemp -d); git archive HEAD | tar -x -C "$T"               # what a release build sees
ls -la "$T/src/qux/static/qux/css/fonts/"                        # links present…
[ -e "$T/src/qux/static/qux/css/fonts/bootstrap-icons.min.css" ] || echo DANGLING

# And in any installed 0.8.2 venv — the wheel's own file list proves the drop:
grep -c "qux/static/qux/css/fonts/" <site-packages>/qux-0.8.2.dist-info/RECORD   # 4, not 6
grep -c "qux/static/qux/js/bootstrap/" <site-packages>/qux-0.8.2.dist-info/RECORD # 0
```

### Why it surfaced only now

Downstream projects that had run `collectstatic` back when qux ≤ 0.7 shipped these as real files kept
serving stale copies out of `STATIC_ROOT` — plain `collectstatic` never deletes. The 0.8.x upgrade
removed the source; the stale copies masked it. In zeus, switching to `ManifestStaticFilesStorage`
turned every such reference into a hashed URL for a file that was never written (hard 404, no
unhashed fallback), and a later `collectstatic --clear` deleted the stale copies outright.

**Do not assume a downstream 404 means the downstream is at fault.** In this incident every
downstream reference was legitimate.

---

## 2. Also dangling, found while fixing the above

These are independent of the symlinks. The guard test in §5 finds them; fix them in the same release.

| Reference | Emitted by | Ever in qux git history? |
|---|---|---|
| `qux_api_log/css/qux_api_log.css` | `drf/log/templates/admin/qux_drf_log/apirequestlog/change_list.html` | **no** |
| `css/forms.css` | `auth/templates/{signup,bs5/signup,password_reset_done}.html`, `token/templates/{,bs5/}token_{create,update,delete}.html` — 9 files | **no** |
| `css/listview.css` | `token/templates/token_list.html` | **no** |
| `qux/css/qux_cover.css` | `templates/covers/fixed.html` | **no** |
| `qux/js/qux/qux_cover.js` | `templates/covers/fixed_with_navbar.html` | **no** |

Verify with `git log --all -- '*forms.css' '*qux_cover*' '*qux_api_log*'` → empty.

Treat them as two different kinds:

- `qux_api_log.css` is **qux's own admin UI**. The template renders Chart.js with
  `maintainAspectRatio: false`, so the canvas takes its height from the container; with no stylesheet
  the chart lays out zero pixels tall. qux must ship it.
- The other four are **project-supplied theme hooks** (`css/…` is each project's own prefix; qux
  cannot supply them). They must stop 404ing for projects that don't provide them, without qux
  inventing design.

---

## 3. Constraints (do not trade these away)

1. Downstream projects fix themselves by **bumping the pin alone** — no template or settings edits.
2. The wheel must never depend on install-time artifacts existing at build time.
3. Vendor bytes stay tracked **once**, as the zips. The unpacked tree remains gitignored generated
   output (`_assets/README.md`, `exclude-package-data`).
4. Assets must exist by `django.setup()` — that is when `collectstatic` walks the finders.
5. Failures must be **loud**. Downstreams on `ManifestStaticFilesStorage` have no fallback, so a
   silently-skipped unpack is a sitewide outage.
6. A bundle version bump must not require editing many references.
7. Must work for wheel installs, editable installs, and `qux-install-assets`.
8. Multi-version bundles stay possible (`bootstrap-4.4.1.zip` ships, opt-in, not auto-unpacked).

One fact that kills a whole family of "fix it in packaging hooks" answers: **`pip install
git+https://…` builds a wheel and installs that**, so `setup.py`'s `install` / `develop` /
`editable_wheel` cmdclass never fires on that path. `QuxConfig.ready()` is the only mechanism that
runs there.

---

## 4. Chosen design, and what was rejected

**Chosen: keep the stable-path layer, materialize it where the bundle tree actually exists.**

The symlinks' *intent* was right — a version-independent path is a good downstream API. Only the
mechanism was unpackageable. So declare the mapping in the manifest and generate it at unpack time.

| Rejected | Why |
|---|---|
| Rebuild zips so bundles unpack straight to the legacy paths | breaks versioned refs incl. `qux.css`, kills constraint 8, binary churn |
| Track real vendor files at the legacy paths | +2.6 MB duplicating zip content, drift risk, violates constraint 3 |
| Custom staticfiles finder in qux | needs `STATICFILES_FINDERS` edited downstream (violates 1); mutating settings in `ready()` is fragile |
| Alias table inside the `qux_static` tag | only covers `{% qux_static %}`; downstreams use plain `{% static %}`, and CSS `@import` cannot call tags |
| URL-level redirect | prod static is served by Apache/nginx, and `{% static %}` resolves before any request exists |
| Unpack at **build** time, ship the unpacked tree | defensible (no runtime writes, survives read-only site-packages) but wheel 5 MB → 19 MB, and editable installs still need the runtime path. Pure packaging change, no downstream contract impact — **can be layered later without redoing any of this** |

---

## 5. What to implement

### 5.1 `src/qux/_assets/manifest.py` — declare the stable paths

Add an `Alias` dataclass and an `ALIASES` tuple after `BUNDLES`:

- fields: `source` (directory under `static/`, inside an unpacked bundle), `target` (stable directory
  under `static/`), `names: tuple[str, ...] = ()` where empty means mirror every file in `source`.
- entries:
  - `Alias(source="bootstrap/5.2.3/js", target="qux/js/bootstrap")` — whole directory, matching what
    the 14 symlinks covered (maps included; a missing `.map` makes `ManifestStaticFilesStorage`
    complain on every downstream `collectstatic`).
  - `Alias(source="bootstrap/5.2.3/css", target="qux/css/bootstrap", names=("bootstrap.min.css", "bootstrap.min.css.map"))`
    — not the whole directory: `static/bootstrap/5.2.3/css` is 5.4 MB.
  - `Alias(source="bootstrap-icons/1.10.5/font", target="qux/css/fonts", names=("bootstrap-icons.css", "bootstrap-icons.min.css"))`.
- Update the module docstring: bumping a library is now a **four**-step change (drop zip → update
  `BUNDLES` → update any `ALIASES.source` naming the old version → delete old zip).

Path arithmetic that makes this work, worth not breaking: the icon CSS references its webfonts as
`../../../fonts/bootstrap-icons.woff2`. From `bootstrap-icons/1.10.5/font/` and from
`qux/css/fonts/` that resolves identically — to `static/fonts/`, which the `qux-fonts` bundle
provides. `bootstrap.min.css` names its sourcemap as a bare sibling filename, hence pairing it.

### 5.2 `src/qux/_assets/install.py` — materialize, and stop trusting the marker alone

Keep every existing public name and behaviour (`_BUNDLES_DIR`, `_STATIC_DIR`, `_MARKERS_DIR`,
`_marker_for`, `install_bundle` → bool, `install_all` → count of bundles unpacked, `main` printing
`unpacked N of M bundle(s)`); `test_assets_install.py` patches those module globals.

Add:

- `_sentinel_for(bundle) -> str | None` — the lexicographically first file member of the bundle zip,
  read from the central directory (cheap). Derives the witness from the bundle instead of hardcoding
  one per library.
- `_is_unpacked(bundle) -> bool` — marker present **and** sentinel present on disk. When the zip is
  unreadable, trust the marker rather than loop forever.
- `install_bundle` uses `_is_unpacked`; when a marker exists but its files are gone, log a warning and
  re-unpack. **This is the second half of the production failure**: prod logged
  `skip bootstrap-icons 1.10.5 (marker present)` on every boot while the files were absent.
- `_alias_pairs(alias) -> list[tuple[Path, Path]]` — resolves one alias to concrete (source, target)
  file pairs; empty when the source directory is absent (bundle not unpacked yet).
- `_link_or_copy(source, target)` — `os.link`, falling back to `shutil.copy2` on `OSError`. Hardlinks
  keep the mirror free of extra bytes.
- `install_aliases(*, force=False) -> int` — walks `ALIASES`, skips targets that already exist unless
  forced, returns files written. **No marker**: verifying ~30 paths per boot is cheap, and it means a
  partially deleted tree heals on the next boot instead of staying broken.
- `missing_assets() -> list[str]` — everything the manifest declares and disk lacks: missing bundle
  zips, un-unpacked bundles, absent alias source directories, absent alias targets. Feeds §5.4.
- `install_all` calls `install_aliases(force=force)` after the bundle loop; still returns the bundle
  count. `main` returns 1 and prints to stderr when `missing_assets()` is non-empty.

### 5.3 Delete the symlinks, gitignore what replaces them

```bash
git rm src/qux/static/qux/css/fonts/bootstrap-icons.css \
       src/qux/static/qux/css/fonts/bootstrap-icons.min.css \
       src/qux/static/qux/js/bootstrap/bootstrap.*
```

`.gitignore`, beside the existing bundle-output block, with a comment saying *why* (tracking them is
the bug this replaced):

```
src/qux/static/qux/js/bootstrap/
src/qux/static/qux/css/bootstrap/
src/qux/static/qux/css/fonts/bootstrap-icons.css
src/qux/static/qux/css/fonts/bootstrap-icons.min.css
```

Removal from the index is required, not cosmetic: a tracked path is never ignored, so leaving them
staged would make git report the generated files as type changes.

### 5.4 `src/qux/checks.py` (new) + `apps.py` — make failure loud

A registered check returning one `Warning` (`id="qux.W001"`) that lists `missing_assets()`, with a
hint naming `qux-install-assets`. Warning, not Error: missing assets should be visible on every
`manage.py check` / `collectstatic` / `runserver` without aborting unrelated commands like `migrate`.

Wire it from `QuxConfig.ready()` via a `_register_checks()` that does
`import_module("qux.checks")` inside `try/except Exception` and logs on failure — `ready()` is
best-effort throughout, and importing is what registers. (Use `import_module`, not
`from qux import checks`; the latter trips pylint's `unused-import`.) Update the numbered
responsibilities list in the module docstring.

### 5.5 `src/qux/templatetags/qux.py` — optional assets

Add `optional: bool = False` to `qux_static`. After the existing `.min` swap, `if optional and not
staticfiles_find(path): return ""`. Give the function a Google-style docstring; explain in the
`optional` entry that qux ships no such file and that a 404 is fatal under
`ManifestStaticFilesStorage`.

### 5.6 Templates

- The 9 `css/forms.css` links and the 1 `css/listview.css` link: replace
  `<link rel="stylesheet" href="{% static 'css/forms.css' %}">` with
  `{% qux_static 'css/forms.css' lazy=False optional=True %}`. `lazy=False` preserves the current
  render-blocking `<link>`. Ensure each touched template's `{% load %}` includes `qux`.
- `covers/fixed.html` and `covers/fixed_with_navbar.html`: add `optional=True` to their existing
  `qux_static` calls.
- `qux.html:112` (`{% qux_static 'qux/js/bootstrap/bootstrap.bundle.js' %}`) needs **no change** — the
  alias restores that path. `_blank.html` is a symlink to `qux.html`; leave it.

### 5.7 Ship the admin stylesheet

`src/qux/drf/log/static/qux_api_log/css/qux_api_log.css`, sizing only:
`#api-log-chart` margin, `#api-log-chart .api-log-chart-canvas { position: relative; height: 260px }`,
`#api-log-chart canvas { width/height: 100% !important }`. Comment why (Chart.js with
`maintainAspectRatio: false` takes height from the container). `qux.drf.log` is an installed app, so
`AppDirectoriesFinder` serves it; `package-data`'s `**/static/**/*` already covers it.

### 5.8 One version invariant worth taking

Repoint `src/qux/static/qux/css/qux.css` line 1 from
`@import url("../../bootstrap/5.2.3/css/bootstrap.min.css")` to
`@import url("bootstrap/bootstrap.min.css")` (the new alias). After this, **no bundle version literal
exists outside `manifest.py`** — verify with
`grep -rn "5\.2\.3" src/qux --exclude-dir=static` (README prose aside).

### 5.9 Docs and version

- `src/qux/_assets/README.md`: document `ALIASES` and `install_aliases`, the sentinel integrity check,
  the four-step bump, and the symlink history (why the mirrors are gitignored and must stay so).
- `VERSION` → `0.8.3`. qux has no CHANGELOG file; don't invent one in this change.

---

## 6. Tests

### 6.1 Extend `src/qux/tests/test_assets_install.py`

- `TestInstallAliases` — patches `_STATIC_DIR` and `ALIASES` against a fake `lib/1.0/js` tree:
  mirrors only declared `names`; mirrors a whole directory when `names` is empty; second call is a
  no-op while `force=True` replaces; **a deleted mirror is restored without `force`**; a missing
  source directory is skipped quietly.
- `TestUnpackIntegrity` — `test_marker_without_unpacked_files_re_unpacks` (pins the production
  failure), plus `missing_assets()` reporting an un-unpacked bundle, an absent alias source, and
  returning `[]` once installed.
- **`TestMain` must also patch `ALIASES` to `()`.** Its fixture is a single fake bundle; leaving the
  real declarations in scope leaks them in, and `main()` now fails on unmaterialized mirrors.

### 6.2 New `src/qux/tests/test_static_references.py` — the gate

Resolve references the way a browser and `collectstatic` do, against what a **fresh install** holds —
never against whatever this working tree happens to have unpacked. Available set =
(files under every `static/` dir in the package) ∪ (all bundle zip members) ∪ (alias targets computed
from the manifest).

Tests:

1. every `{% static %}` / `{% qux_static %}` literal in qux templates resolves — skipping calls whose
   arguments contain `optional=True`, which are hooks qux never promised to ship;
2. every `url()` / `@import` in qux's **own** CSS resolves (exclude bundle top-level directories and
   alias targets — upstream's internal refs are upstream's business);
3. every `ALIASES.source` matches at least one bundle zip member, and every declared `names` entry
   exists in its bundle — *this is what catches a bump that skipped step 3*;
4. `git ls-files -s src/qux/static` reports no mode-`120000` entries; `skipTest` when not a git
   checkout.

Four traps that cost time here:

- **App-level static roots.** `src/qux/drf/log/static/` is served too. Collect every directory named
  `static` under the package, not just `src/qux/static`.
- **Django rewrites `url()` inside CSS comments.** A commented-out `@import` still produces a
  "referenced but not found" warning at `collectstatic`. Don't write one in a comment, and expect the
  test to flag them.
- **Stale bytecode.** After editing `manifest.py` by script, `__pycache__` can serve the old
  `ALIASES`. `find src -name __pycache__ -exec rm -rf {} +` before trusting a run.
- **zsh does not word-split unquoted `$VAR`.** Use arrays when passing file lists to black/pylint.

---

## 7. Verification protocol

Run all of it; each step catches something the others don't.

```bash
# 1. Suite — 686 tests at the time of writing, 3 skipped.
python runtests.py            # or: make test

# 2. Prove the gate fails on the regression it exists for.
sed -i '' 's|source="bootstrap/5.2.3/js"|source="bootstrap/5.3.0/js"|' src/qux/_assets/manifest.py
find src -name __pycache__ -type d -exec rm -rf {} +
PYTHONPATH=src python -m django test qux.tests.test_static_references --settings=qux.tests.settings
#   expect: FAIL test_every_alias_source_exists_in_a_bundle → "no bundle unpacks bootstrap/5.3.0/js"
git checkout src/qux/_assets/manifest.py && find src -name __pycache__ -type d -exec rm -rf {} +

# 3. Lint / format / architecture.
isort --profile black <changed files>; black <changed files>
make lint          # pylint; expect ~9.1/10, remaining warnings pre-existing patterns
make arch          # lint-imports; expect 2 contracts kept

# 4. Build a wheel from a RELEASE-SHAPED tree (tracked + new files only, nothing gitignored).
B=$(mktemp -d); git ls-files --cached --others --exclude-standard | while read -r f; do
  [ -f "$f" ] && mkdir -p "$B/$(dirname "$f")" && cp "$f" "$B/$f"; done
find "$B" -type l | wc -l                       # expect 0 symlinks
python -m pip wheel --no-deps --no-build-isolation -w /tmp/w "$B"
#   expect ~5.0 MB, unchanged; contains _assets/bundles/*.zip, checks.py,
#   drf/log/static/…; contains NO qux/static/qux/js/bootstrap/ and NO
#   qux/static/qux/css/bootstrap/ entries (they are generated at install)

# 5. Simulate a fresh install + first boot.
F=$(mktemp -d); (cd "$F" && unzip -q /tmp/w/qux-0.8.3-*.whl)
[ -e "$F/qux/static/qux/css/fonts/bootstrap-icons.min.css" ] && echo UNEXPECTED   # absent pre-boot
PYTHONPATH="$F" python -m qux._assets.install -v                                  # "mirrored 16 file(s)"
#   then all of these must exist:
#     qux/static/qux/css/fonts/bootstrap-icons.min.css
#     qux/static/qux/js/bootstrap/bootstrap.bundle.min.js
#     qux/static/qux/css/bootstrap/bootstrap.min.css
#     qux/static/fonts/bootstrap-icons.woff2
```

### The claim that actually matters — a downstream, unchanged

Point a downstream project's `collectstatic` at the fresh qux via `PYTHONPATH` (shadowing its
installed copy) with `DEBUG=False`, `STATIC_ROOT` set to a temp dir, and `--clear`. Change **nothing**
in the downstream. Against zeus this produced:

```
qux/js/bootstrap/bootstrap.bundle.min.js -> /static/qux/js/bootstrap/bootstrap.bundle.min.119fc8956785.js  exists=True
qux/css/fonts/bootstrap-icons.min.css    -> /static/qux/css/fonts/bootstrap-icons.min.fdaf20fb326b.css     exists=True
qux/css/qux.css                          -> /static/qux/css/qux.16159c5adde5.css                            exists=True
dangling references: (only the downstream's own two commented-out inter.css @imports)
```

The `bootstrap.bundle.min.119fc8956785.js` hash matched what zeus's production `STATIC_ROOT` already
held, confirming the same bytes.

---

## 8. Release and downstream rollout

- Conventional commit; racecar convention wants a `Bump version to 0.8.3.` footer. Consider splitting:
  the packaging fix (symlinks → generated aliases + integrity + checks + tests) is one concern; the
  optional-asset tag with its 12 template edits is another; the admin stylesheet a third.
- Tag `v0.8.3` and push — downstreams pin by tag (`git+https://github.com/quxdev/qux.git@v0.8.3`).
- Downstream instruction is exactly one line: bump the pin. No template or settings edits. Redeploy
  (`collectstatic`) picks the assets up because `ready()` materializes them before the finders run.
- Advise downstreams to run `manage.py check` after upgrading: `qux.W001` now names anything missing.

### Unrelated downstream items (zeus's own, do not fix in qux)

- `apps/{bosassets,gridqueue}/static/*/css/app.css` each open with a commented-out
  `@import url('fonts/inter.css')`. Django rewrites URLs inside CSS comments, so both warn on every
  `collectstatic`. One-line deletions, zeus's call.
- zeus's `ObfuscatedStaticFilesStorage.stored_name()` hands out a hashed URL for a file that was never
  saved when a manifest entry is missing. Independent latent bug, separately fixable there.

---

## 9. Reference material in this handover directory

- `qux-static-fix.tracked.patch` — `git diff HEAD` of a complete working implementation, including
  the symlink deletions.
- `qux-static-fix.newfiles.tar` — the three additions git had not yet tracked
  (`src/qux/checks.py`, `src/qux/tests/test_static_references.py`,
  `src/qux/drf/log/static/qux_api_log/css/qux_api_log.css`).

Both are **reference, not a drop-in**: they were produced against qux at `9575ac7` and verified there
(686 tests, wheel build, fresh-install simulation, downstream `collectstatic`). Read them if a spec
above is ambiguous; prefer implementing from §5 so the qux history carries your own work.
