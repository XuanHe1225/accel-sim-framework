import hashlib
import io
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import tempfile
import unittest


class NVBitInstallTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tracer = self.root / "util/tracer_nvbit"
        self.tracer.mkdir(parents=True)
        source = Path(__file__).resolve().parents[1] / "util/tracer_nvbit"
        for name in ("install_nvbit.sh", "install_nvbit.py"):
            if (source / name).exists():
                shutil.copyfile(source / name, self.tracer / name)
        self.archive = self.root / "release.tar.bz2"
        with tarfile.open(self.archive, "w:bz2") as stream:
            payload = b"verified official core fixture"
            member = tarfile.TarInfo(f"nvbit_release_{platform.machine()}/core/libnvbit.a")
            member.size = len(payload)
            stream.addfile(member, io.BytesIO(payload))
        (self.root / "pnm-toolchain.json").write_text(json.dumps({"nvbit": {
            "version": "1.8", "sha256": {
                platform.machine(): hashlib.sha256(self.archive.read_bytes()).hexdigest()
            }
        }}))
        self.core = self.tracer / "nvbit_release/core/libnvbit.a"
        # The old installer uses wget and ignores --archive. Never access the
        # network in these tests; expose its failure handling with a bad fetch.
        fake_bin = self.root / "bin"
        fake_bin.mkdir()
        wget = fake_bin / "wget"
        wget.write_text('#!/bin/sh\nprintf corrupted > "${1##*/}"\n')
        wget.chmod(0o755)
        self.env = dict(os.environ, PATH=str(fake_bin) + os.pathsep + os.environ["PATH"])

    def install(self):
        return subprocess.run(["bash", str(self.tracer / "install_nvbit.sh"),
                               "--archive", str(self.archive)], cwd=self.root,
                              env=self.env, capture_output=True, text=True)

    def test_bad_download_preserves_installed_core(self):
        self.core.parent.mkdir(parents=True)
        self.core.write_bytes(b"previous installation")
        self.archive.write_bytes(b"corrupt download")
        result = self.install()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.core.read_bytes(), b"previous installation")

    def test_verified_archive_installs_and_can_be_verified_again(self):
        for _ in range(2):
            result = self.install()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(self.core.read_bytes(), b"verified official core fixture")

    def test_modified_core_is_rejected(self):
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.core.write_bytes(b"unverified local modification")
        self.assertNotEqual(self.install().returncode, 0)
        self.assertEqual(self.core.read_bytes(), b"unverified local modification")


if __name__ == "__main__":
    unittest.main()
