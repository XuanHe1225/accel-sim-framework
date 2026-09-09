import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class BackendPinTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.framework = self.root / "framework"
        simulator = self.framework / "gpu-simulator"
        (simulator / "extern/pybind11").mkdir(parents=True)
        source = Path(__file__).resolve().parents[1] / "gpu-simulator/setup_environment.sh"
        shutil.copyfile(source, simulator / source.name)
        self.repo = self.root / "backend-source"
        subprocess.run(["git", "init", "-q", "-b", "codex/test", str(self.repo)], check=True)
        self.git("config", "user.name", "codex-bot")
        self.git("config", "user.email", "codex-bot@local")
        (self.repo / "setup_environment").write_text(
            'export GPGPUSIM_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\n'
            'export GPGPUSIM_SETUP_ENVIRONMENT_WAS_RUN=1\n')
        self.git("add", "setup_environment")
        self.git("commit", "-qm", "First backend")
        self.pin = self.git("rev-parse", "HEAD")
        (self.repo / "later").write_text("Later unselected revision\n")
        self.git("add", "later")
        self.git("commit", "-qm", "Later backend")
        (self.framework / "pnm-toolchain.json").write_text(json.dumps({"backend": {
            "repository": str(self.repo), "revision": self.pin
        }}))
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith(("GPGPUSIM_", "ACCELSIM_"))}
        self.env["CUDA_INSTALL_PATH"] = str(self.root)
        self.env.pop("PS1", None)

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], text=True).strip()

    def setup(self):
        return subprocess.run(["bash", "-c", 'source "$1"', "test-setup",
                               str(self.framework / "gpu-simulator/setup_environment.sh")],
                              env=self.env, capture_output=True, text=True)

    def test_existing_different_backend_is_rejected_without_modification(self):
        self.env["GPGPUSIM_ROOT"] = str(self.repo)
        self.env["GPGPUSIM_SETUP_ENVIRONMENT_WAS_RUN"] = "1"
        before = self.git("rev-parse", "HEAD")
        result = self.setup()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD"), before)

    def test_clean_setup_clones_pinned_commit_instead_of_branch_tip(self):
        result = self.setup()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        checkout = self.framework / "gpu-simulator/gpgpu-sim"
        actual = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
        self.assertEqual(actual, self.pin)
        self.assertFalse((checkout / "later").exists())


if __name__ == "__main__":
    unittest.main()
