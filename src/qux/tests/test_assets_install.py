"""Tests for ``qux._assets.install`` — bundle unpacking + idempotency markers.

Uses a real zip in a tmp dir (not the production bundle paths) by patching
the module-level constants. The marker-file behavior is the load-bearing
contract we want pinned: skip on second call, force on ``--force``, surface
``FileNotFoundError`` on missing zip.
"""

from __future__ import annotations

import io
import os
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from qux._assets import install as install_mod
from qux._assets.manifest import Bundle


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
