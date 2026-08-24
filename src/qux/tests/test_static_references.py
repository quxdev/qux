"""Gate: every static asset qux references must be one qux actually ships.

qux 0.8.2 shipped a stylesheet whose ``@import`` chain reached files the wheel
did not contain (they were tracked git symlinks into the gitignored, unpacked
bundle tree, so setuptools dropped them from a clean-checkout build). Every
downstream project 404'd on bootstrap's JS and on every ``bi bi-*`` glyph. These
tests exist so that cannot recur silently.

The available set is computed the way a **fresh install** looks, never from
whatever this working tree happens to have unpacked:

    files tracked under any static/ dir in the package
  ∪ every member of every bundle zip
  ∪ every alias target the manifest declares

Anything under an unpacked bundle's top-level directory, or under an alias
target directory, is deliberately excluded from the on-disk scan — on a
developer box those are present, on a clean build they are not, and it is
precisely that difference that hid the original bug.
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
import zipfile
from pathlib import Path

from django.test import SimpleTestCase

import qux
from qux._assets.manifest import ALIASES, BUNDLES

_PACKAGE_DIR = Path(qux.__file__).resolve().parent
_BUNDLES_DIR = _PACKAGE_DIR / "_assets" / "bundles"
_REPO_ROOT = _PACKAGE_DIR.parent.parent

# {% static 'x' %} / {% qux_static 'x' lazy=False %} with a literal first arg.
_TAG_RE = re.compile(r"\{%\s*(qux_static|static)\s+(['\"])(?P<path>[^'\"]+)\2(?P<rest>[^%]*)%\}")
# url(...) and @import "..." inside CSS. Comments are NOT stripped: Django's
# CSS post-processor rewrites url() inside comments too, so a commented-out
# reference to a missing file still warns at collectstatic.
_CSS_REF_RE = re.compile(
    r"""url\(\s*(['"]?)(?P<u>[^'")]+)\1\s*\)|@import\s+(['"])(?P<i>[^'"]+)\3"""
)

_EXTERNAL = ("http://", "https://", "//", "data:", "#")


def _static_dirs() -> list[Path]:
    """Every directory named ``static`` inside the package.

    App-level roots count: ``qux/drf/log/static/`` is served by
    ``AppDirectoriesFinder`` exactly like the top-level one.
    """
    return sorted(p for p in _PACKAGE_DIR.rglob("static") if p.is_dir())


def _bundle_members() -> set[str]:
    """Every file member of every bundle zip, as a path relative to static/."""
    members: set[str] = set()
    for bundle in BUNDLES:
        path = _BUNDLES_DIR / bundle.filename
        if not path.exists():
            continue
        with zipfile.ZipFile(path) as zf:
            members.update(name for name in zf.namelist() if not name.endswith("/"))
    return members


def _bundle_top_dirs() -> set[str]:
    """First path component of every bundle member — the unpacked-tree roots."""
    return {name.split("/", 1)[0] for name in _bundle_members() if "/" in name}


def _alias_targets(members: set[str]) -> set[str]:
    """Paths install_aliases() will materialize, computed from the zips.

    Args:
        members: Bundle zip members, relative to static/.

    Returns:
        Target paths relative to static/.
    """
    targets: set[str] = set()
    for alias in ALIASES:
        if alias.names:
            names = list(alias.names)
        else:
            prefix = f"{alias.source}/"
            names = [
                name[len(prefix) :]
                for name in members
                if name.startswith(prefix) and "/" not in name[len(prefix) :]
            ]
        targets.update(f"{alias.target}/{name}" for name in names)
    return targets


def _own_static_files() -> list[tuple[Path, str]]:
    """qux's own static files: on disk, minus everything generated at install.

    Excluded: unpacked bundle trees, and the individual alias targets (by exact
    path, not by directory — ``qux/css/fonts/`` holds two mirrored files
    alongside four of qux's own stylesheets).

    Returns:
        (absolute path, path relative to its static root) pairs.
    """
    members = _bundle_members()
    skip_roots = _bundle_top_dirs()
    generated = _alias_targets(members)
    found: list[tuple[Path, str]] = []
    for root in _static_dirs():
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if rel.split("/", 1)[0] in skip_roots or rel in generated:
                continue
            if rel.startswith(".qux-bundles/"):
                continue
            found.append((path, rel))
    return found


def _available() -> set[str]:
    """Everything a fresh install can serve, relative to a static root."""
    members = _bundle_members()
    return {rel for _, rel in _own_static_files()} | members | _alias_targets(members)


def _template_files() -> list[Path]:
    """Every .html under any templates/ dir in the package."""
    return sorted(
        path
        for templates in _PACKAGE_DIR.rglob("templates")
        if templates.is_dir()
        for path in templates.rglob("*.html")
    )


def _normalize(ref: str) -> str | None:
    """Strip query/fragment from a reference; None for external or absolute URLs."""
    ref = ref.strip()
    if not ref or ref.startswith(_EXTERNAL) or ref.startswith("/"):
        return None
    return ref.split("?", 1)[0].split("#", 1)[0]


class TestTemplateStaticReferences(SimpleTestCase):
    """Every literal {% static %} / {% qux_static %} path must be shippable."""

    def test_every_template_static_reference_resolves(self):
        available = _available()
        dangling = []
        for template in _template_files():
            text = template.read_text(encoding="utf-8", errors="ignore")
            for match in _TAG_RE.finditer(text):
                # optional=True means "a project theme hook qux never promised
                # to ship" — the tag renders nothing when it is absent.
                if "optional=True" in match.group("rest"):
                    continue
                ref = _normalize(match.group("path"))
                if ref and ref not in available:
                    rel = template.relative_to(_PACKAGE_DIR)
                    dangling.append(f"{rel}: {ref}")
        self.assertEqual(dangling, [], f"templates reference unshipped static files: {dangling}")


class TestCssStaticReferences(SimpleTestCase):
    """Every url()/@import in qux's own CSS must resolve within the static tree."""

    def test_every_css_reference_resolves(self):
        available = _available()
        dangling = []
        for path, rel in _own_static_files():
            if path.suffix.lower() != ".css":
                continue
            base = Path(rel).parent
            text = path.read_text(encoding="utf-8", errors="ignore")
            for match in _CSS_REF_RE.finditer(text):
                ref = _normalize(match.group("u") or match.group("i") or "")
                if not ref:
                    continue
                resolved = (base / ref).as_posix()
                # Path.as_posix() keeps "..", so normalize them away.
                parts: list[str] = []
                for part in resolved.split("/"):
                    if part == "..":
                        if parts:
                            parts.pop()
                    elif part not in (".", ""):
                        parts.append(part)
                resolved = "/".join(parts)
                if resolved not in available:
                    dangling.append(f"{rel}: {ref}")
        self.assertEqual(dangling, [], f"CSS references unshipped static files: {dangling}")


class TestAliasesMatchBundles(SimpleTestCase):
    """A bundle bump that forgets to update ALIASES fails here."""

    def test_every_alias_source_exists_in_a_bundle(self):
        members = _bundle_members()
        for alias in ALIASES:
            prefix = f"{alias.source}/"
            self.assertTrue(
                any(name.startswith(prefix) for name in members),
                f"no bundle unpacks {alias.source} — ALIASES is stale for a bumped bundle",
            )

    def test_every_declared_alias_name_exists_in_its_bundle(self):
        members = _bundle_members()
        for alias in ALIASES:
            for name in alias.names:
                self.assertIn(
                    f"{alias.source}/{name}",
                    members,
                    f"{alias.source}/{name} is declared in ALIASES but no bundle contains it",
                )


class TestNoTrackedSymlinks(SimpleTestCase):
    """Static assets must never be tracked as symlinks — that is the 0.8.2 bug."""

    def test_no_symlinks_tracked_under_static(self):
        try:
            out = subprocess.run(
                ["git", "ls-files", "-s", "src/qux"],
                cwd=_REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("not a git checkout")
        links = [
            line.split("\t", 1)[1]
            for line in out.splitlines()
            if line.startswith("120000") and "/static/" in line
        ]
        self.assertEqual(
            links,
            [],
            "static assets tracked as symlinks — they dangle in a clean build and "
            f"setuptools drops them from the wheel: {links}",
        )


class TestGeneratedPathsStayOutOfTheRepoAndTheWheel(SimpleTestCase):
    """The manifest, .gitignore, and pyproject must agree on what is generated.

    "These paths are generated at install time" is stated in three places:
    ``ALIASES`` (which produces them), ``.gitignore`` (which keeps them out of
    git), and ``[tool.setuptools.exclude-package-data]`` (which keeps them out
    of the wheel). Nothing in setuptools or git binds those three together, so
    adding an alias and forgetting one of the others yields either a tracked
    generated file — the 0.8.2 bug — or a wheel whose contents depend on which
    machine built it, which is what hid that bug for months. These tests are the
    binding.
    """

    def _targets(self) -> list[str]:
        """Alias target paths relative to a static root, from the manifest."""
        return sorted(_alias_targets(_bundle_members()))

    def test_every_alias_target_is_gitignored(self):
        try:
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=_REPO_ROOT,
                capture_output=True,
                check=True,
            )
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("not a git checkout")

        tracked = []
        for target in self._targets():
            path = f"src/qux/static/{target}"
            result = subprocess.run(
                ["git", "check-ignore", "-q", path],
                cwd=_REPO_ROOT,
                capture_output=True,
                check=False,
            )
            if result.returncode != 0:
                tracked.append(path)
        self.assertEqual(
            tracked,
            [],
            "generated by ALIASES but not gitignored — add them to .gitignore "
            f"beside the bundle-output block: {tracked}",
        )

    @staticmethod
    def _exclude_package_data_patterns(text: str) -> list[str]:
        """The ``[tool.setuptools.exclude-package-data]`` "qux" patterns.

        Scanned rather than parsed with ``tomllib``, which is 3.11+ while qux
        supports 3.10. The block is qux's own and its shape is stable, so a
        line scan buys the coverage without narrowing the supported versions.

        Args:
            text: Contents of pyproject.toml.

        Returns:
            The declared patterns, in file order.
        """
        patterns: list[str] = []
        in_table = False
        in_list = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("["):
                in_table = stripped == "[tool.setuptools.exclude-package-data]"
                in_list = False
                continue
            if not in_table:
                continue
            if not in_list:
                if re.match(r'^"?qux"?\s*=\s*\[', stripped):
                    in_list = True
                continue
            if stripped.startswith("]"):
                break
            found = re.match(r'^"([^"]+)"', stripped)
            if found:
                patterns.append(found.group(1))
        return patterns

    def test_every_alias_target_is_excluded_from_package_data(self):
        pyproject = _REPO_ROOT / "pyproject.toml"
        if not pyproject.exists():
            self.skipTest("not a source checkout")
        patterns = self._exclude_package_data_patterns(pyproject.read_text(encoding="utf-8"))
        self.assertTrue(patterns, "no [tool.setuptools.exclude-package-data] patterns found")

        unexcluded = [
            f"static/{target}"
            for target in self._targets()
            if not any(fnmatch.fnmatch(f"static/{target}", pattern) for pattern in patterns)
        ]
        self.assertEqual(
            unexcluded,
            [],
            "generated by ALIASES but not excluded from package data — a wheel "
            "built on a machine that has them would differ from one built from a "
            f"clean checkout: {unexcluded}",
        )
