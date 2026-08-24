"""Tests for ``qux._assets.install`` — bundle unpacking + idempotency markers.

Uses a real zip in a tmp dir (not the production bundle paths) by patching
the module-level constants. The marker-file behavior is the load-bearing
contract we want pinned: skip on second call, force on ``--force``, surface
``FileNotFoundError`` on missing zip.
"""

from __future__ import annotations

import io
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from qux._assets import install as install_mod
from qux._assets.manifest import Alias, Bundle


def _make_zip(zip_path: Path, name: str = "demo") -> None:
    """Create a tiny zip with one nested file under a top-level dir matching ``name``."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(f"{name}/hello.txt", "hi")
    zip_path.write_bytes(buf.getvalue())


class TestInstallBundle(SimpleTestCase):
    def setUp(self) -> None:

        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        tmp = Path(self._tmp.name)
        self._bundles_dir = tmp / "bundles"
        self._static_dir = tmp / "static"
        self._markers_dir = self._static_dir / ".qux-bundles"
        self._bundles_dir.mkdir()
        # Patch module-level path constants so the test doesn't touch real qux/static.
        self._patches = [
            patch.object(install_mod, "_BUNDLES_DIR", self._bundles_dir),
            patch.object(install_mod, "_STATIC_DIR", self._static_dir),
            patch.object(install_mod, "_MARKERS_DIR", self._markers_dir),
        ]
        for p in self._patches:
            p.start()
        self.bundle = Bundle(name="demo", filename="demo.zip", version="1.0")
        _make_zip(self._bundles_dir / "demo.zip", name="demo")

    def tearDown(self) -> None:
        for p in self._patches:
            p.stop()

    def test_unpacks_first_call_and_writes_marker(self):
        unpacked = install_mod.install_bundle(self.bundle)
        self.assertTrue(unpacked)
        self.assertTrue((self._static_dir / "demo" / "hello.txt").exists())
        self.assertTrue((self._markers_dir / "demo.zip").exists())

    def test_skips_second_call_when_marker_present(self):
        install_mod.install_bundle(self.bundle)
        unpacked_again = install_mod.install_bundle(self.bundle)
        self.assertFalse(unpacked_again)

    def test_force_re_unpacks_even_with_marker(self):
        install_mod.install_bundle(self.bundle)
        unpacked = install_mod.install_bundle(self.bundle, force=True)
        self.assertTrue(unpacked)

    def test_missing_zip_raises_file_not_found(self):
        os.unlink(self._bundles_dir / "demo.zip")
        with self.assertRaises(FileNotFoundError):
            install_mod.install_bundle(self.bundle)

    def test_install_all_returns_count(self):
        # install_all walks the production manifest, not our test bundles.
        # Patch BUNDLES to point at our single test bundle for a focused check.
        with patch.object(install_mod, "BUNDLES", [self.bundle]):
            count = install_mod.install_all()
        self.assertEqual(count, 1)
        # Second call should be 0 (marker prevents re-unpack).
        with patch.object(install_mod, "BUNDLES", [self.bundle]):
            count_again = install_mod.install_all()
        self.assertEqual(count_again, 0)


class TestMain(SimpleTestCase):
    """``qux-install-assets`` console script entry point."""

    def setUp(self) -> None:

        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        tmp = Path(self._tmp.name)
        self._bundles_dir = tmp / "bundles"
        self._static_dir = tmp / "static"
        self._markers_dir = self._static_dir / ".qux-bundles"
        self._bundles_dir.mkdir()
        self._patches = [
            patch.object(install_mod, "_BUNDLES_DIR", self._bundles_dir),
            patch.object(install_mod, "_STATIC_DIR", self._static_dir),
            patch.object(install_mod, "_MARKERS_DIR", self._markers_dir),
            # The real ALIASES point into bundles this fixture does not have,
            # and main() now returns 1 on an incomplete asset tree.
            patch.object(install_mod, "ALIASES", ()),
        ]
        for p in self._patches:
            p.start()
        self.bundle = Bundle(name="demo", filename="demo.zip", version="1.0")
        _make_zip(self._bundles_dir / "demo.zip", name="demo")

    def tearDown(self) -> None:
        for p in self._patches:
            p.stop()

    def test_main_returns_zero_on_success(self):
        with (
            patch.object(install_mod, "BUNDLES", [self.bundle]),
            patch("sys.stdout", new=io.StringIO()) as out,
        ):
            rc = install_mod.main([])
        self.assertEqual(rc, 0)
        self.assertIn("unpacked 1 of 1 bundle(s)", out.getvalue())

    def test_main_returns_one_on_missing_bundle(self):
        os.unlink(self._bundles_dir / "demo.zip")
        with (
            patch.object(install_mod, "BUNDLES", [self.bundle]),
            patch("sys.stderr", new=io.StringIO()) as err,
        ):
            rc = install_mod.main([])
        self.assertEqual(rc, 1)
        self.assertIn("Bundle missing", err.getvalue())


class TestInstallAliases(SimpleTestCase):
    """``install_aliases`` — the stable-path mirrors that replaced git symlinks."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._static_dir = Path(self._tmp.name) / "static"
        source = self._static_dir / "lib" / "1.0" / "js"
        source.mkdir(parents=True)
        (source / "lib.js").write_text("lib")
        (source / "lib.min.js").write_text("lib-min")
        (source / "lib.min.js.map").write_text("{}")
        self._source = source
        self._patch = patch.object(install_mod, "_STATIC_DIR", self._static_dir)
        self._patch.start()
        self.addCleanup(self._patch.stop)

    def _with(self, *aliases):
        return patch.object(install_mod, "ALIASES", aliases)

    def test_mirrors_only_declared_names(self):
        alias = Alias(source="lib/1.0/js", target="stable/js", names=("lib.min.js",))
        with self._with(alias):
            written = install_mod.install_aliases()
        self.assertEqual(written, 1)
        self.assertTrue((self._static_dir / "stable" / "js" / "lib.min.js").exists())
        self.assertFalse((self._static_dir / "stable" / "js" / "lib.js").exists())

    def test_mirrors_whole_directory_when_names_empty(self):
        with self._with(Alias(source="lib/1.0/js", target="stable/js")):
            written = install_mod.install_aliases()
        self.assertEqual(written, 3)
        mirrored = sorted(p.name for p in (self._static_dir / "stable" / "js").iterdir())
        self.assertEqual(mirrored, ["lib.js", "lib.min.js", "lib.min.js.map"])

    def test_second_call_is_a_noop_and_force_rewrites(self):
        alias = Alias(source="lib/1.0/js", target="stable/js")
        with self._with(alias):
            install_mod.install_aliases()
            self.assertEqual(install_mod.install_aliases(), 0)
            self.assertEqual(install_mod.install_aliases(force=True), 3)

    def test_deleted_mirror_is_restored_without_force(self):
        alias = Alias(source="lib/1.0/js", target="stable/js")
        with self._with(alias):
            install_mod.install_aliases()
            target = self._static_dir / "stable" / "js" / "lib.min.js"
            target.unlink()
            written = install_mod.install_aliases()
        self.assertEqual(written, 1)
        self.assertTrue(target.exists())

    def test_stale_mirror_from_a_previous_bundle_version_is_refreshed(self):
        """A bumped bundle must not keep serving the old library's bytes.

        Mirror filenames carry no version, so a presence check would leave a
        downstream on the previous library forever after a bundle bump.
        """
        with self._with(Alias(source="lib/1.0/js", target="stable/js")):
            install_mod.install_aliases()
        target = self._static_dir / "stable" / "js" / "lib.min.js"
        self.assertEqual(target.read_text(), "lib-min")

        new_source = self._static_dir / "lib" / "2.0" / "js"
        new_source.mkdir(parents=True)
        (new_source / "lib.min.js").write_text("lib-min-2.0")

        with self._with(Alias(source="lib/2.0/js", target="stable/js")):
            written = install_mod.install_aliases()
            self.assertEqual(written, 1)
            self.assertEqual(target.read_text(), "lib-min-2.0")
            # And having refreshed it, it stays a no-op.
            self.assertEqual(install_mod.install_aliases(), 0)

    def test_declared_name_absent_from_the_bundle_is_reported_not_dropped(self):
        alias = Alias(source="lib/1.0/js", target="stable/js", names=("lib.min.js", "typo.min.js"))
        with self._with(alias), patch.object(install_mod, "BUNDLES", []):
            written = install_mod.install_aliases()
            missing = install_mod.missing_assets()

        self.assertEqual(written, 1)
        self.assertEqual(missing, ["alias source file missing: static/lib/1.0/js/typo.min.js"])

    def test_missing_source_directory_is_skipped_quietly(self):
        with self._with(Alias(source="absent/1.0/js", target="stable/js")):
            written = install_mod.install_aliases()
        self.assertEqual(written, 0)
        self.assertFalse((self._static_dir / "stable").exists())


class TestUnpackIntegrity(SimpleTestCase):
    """A marker must never outlive the files it claims are unpacked."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        tmp = Path(self._tmp.name)
        self._bundles_dir = tmp / "bundles"
        self._static_dir = tmp / "static"
        self._markers_dir = self._static_dir / ".qux-bundles"
        self._bundles_dir.mkdir()
        self._patches = [
            patch.object(install_mod, "_BUNDLES_DIR", self._bundles_dir),
            patch.object(install_mod, "_STATIC_DIR", self._static_dir),
            patch.object(install_mod, "_MARKERS_DIR", self._markers_dir),
        ]
        for p in self._patches:
            p.start()
            self.addCleanup(p.stop)
        self.bundle = Bundle(name="demo", filename="demo.zip", version="1.0")
        _make_zip(self._bundles_dir / "demo.zip", name="demo")

    def test_marker_without_unpacked_files_re_unpacks(self):
        """The production failure: `skip demo (marker present)` while files were gone."""
        install_mod.install_bundle(self.bundle)
        shutil.rmtree(self._static_dir / "demo")

        unpacked = install_mod.install_bundle(self.bundle)

        self.assertTrue(unpacked)
        self.assertTrue((self._static_dir / "demo" / "hello.txt").exists())

    def test_missing_assets_reports_un_unpacked_bundle(self):
        with patch.object(install_mod, "BUNDLES", [self.bundle]), self._no_aliases():
            missing = install_mod.missing_assets()
        self.assertEqual(missing, ["bundle not unpacked: demo 1.0"])

    def test_missing_assets_reports_absent_alias_source(self):
        alias = Alias(source="absent/js", target="stable/js")
        with (
            patch.object(install_mod, "BUNDLES", [self.bundle]),
            patch.object(install_mod, "ALIASES", (alias,)),
        ):
            install_mod.install_bundle(self.bundle)
            missing = install_mod.missing_assets()
        self.assertIn("alias source missing: static/absent/js", missing)

    def test_missing_assets_reports_unmirrored_alias_target(self):
        alias = Alias(source="demo", target="stable", names=("hello.txt",))
        with (
            patch.object(install_mod, "BUNDLES", [self.bundle]),
            patch.object(install_mod, "ALIASES", (alias,)),
        ):
            install_mod.install_bundle(self.bundle)
            self.assertIn(
                "alias target missing or stale: static/stable/hello.txt",
                install_mod.missing_assets(),
            )
            install_mod.install_aliases()
            self.assertEqual(install_mod.missing_assets(), [])

    def test_missing_assets_reports_absent_bundle_zip(self):
        os.unlink(self._bundles_dir / "demo.zip")
        with patch.object(install_mod, "BUNDLES", [self.bundle]), self._no_aliases():
            missing = install_mod.missing_assets()
        self.assertEqual(missing, ["bundle zip not in package: demo.zip"])

    def test_missing_assets_empty_once_installed(self):
        with patch.object(install_mod, "BUNDLES", [self.bundle]), self._no_aliases():
            install_mod.install_all()
            self.assertEqual(install_mod.missing_assets(), [])

    def _no_aliases(self):
        return patch.object(install_mod, "ALIASES", ())
