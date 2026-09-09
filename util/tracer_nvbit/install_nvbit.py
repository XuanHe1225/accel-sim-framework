"""Install or verify the official NVBit release pinned in pnm-toolchain.json.

Requires Python 3.12+ for tarfile's data filter. An existing installation is
verified in place, preserving built tools; a differing core is never overwritten.
"""

import argparse
import hashlib
import json
from pathlib import Path
import platform
import tarfile
import tempfile
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="Use a cached release archive")
    args = parser.parse_args()
    tracer = Path(__file__).resolve().parent
    pin = json.loads((tracer.parents[1] / "pnm-toolchain.json").read_text())["nvbit"]
    arch = platform.machine()
    if arch not in pin["sha256"]:
        raise SystemExit("Unsupported NVBit architecture: " + arch)
    version = pin["version"]
    installed = tracer / "nvbit_release"
    with tempfile.TemporaryDirectory(prefix=".nvbit-", dir=tracer) as temporary:
        stage = Path(temporary)
        archive = args.archive
        if archive is None:
            name = f"nvbit-Linux-{arch}-{version}.tar.bz2"
            archive = stage / name
            urllib.request.urlretrieve(
                f"https://github.com/NVlabs/NVBit/releases/download/v{version}/{name}", archive)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != pin["sha256"][arch]:
            raise SystemExit("NVBit release checksum mismatch")
        with tarfile.open(archive) as stream:
            stream.extractall(stage / "unpacked", filter="data")
        release = stage / f"unpacked/nvbit_release_{arch}"
        if not (release / "core/libnvbit.a").is_file():
            raise SystemExit("NVBit archive does not contain core/libnvbit.a")
        if installed.exists():
            for source in (release / "core").rglob("*"):
                if source.is_file():
                    target = installed / source.relative_to(release)
                    if not target.is_file() or target.read_bytes() != source.read_bytes():
                        raise SystemExit(f"Installed NVBit core differs from the pinned release: {target}")
        else:
            release.rename(installed)
    print(f"Verified NVBit v{version} ({arch}), SHA256 {pin['sha256'][arch]}")


if __name__ == "__main__":
    main()
