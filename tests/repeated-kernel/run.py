#!/usr/bin/env python3
"""Replay three GEMMs without resetting the simulator between kernels."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--library", type=Path, required=True,
                        help="Built GPGPU-Sim libcudart.so")
    args = parser.parse_args()
    fixture = Path(__file__).resolve().parent
    framework = fixture.parents[1]
    backend = framework / "gpu-simulator/gpgpu-sim"
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((fixture / "manifest.json").read_text())
    for name, digest in manifest["sha256"].items():
        source = fixture / name
        if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            raise ValueError("fixture checksum mismatch: " + name)
        (output / name).symlink_to(source)
    command = [
        str(framework / "gpu-simulator/bin/release/accel-sim.out"),
        "-config", str(backend / "configs/tested-cfgs/SM80_A100/gpgpusim.config"),
        "-config", str(framework / "gpu-simulator/configs/tested-cfgs/SM80_A100/trace.config"),
        "-trace", str(output / "kernelslist.g"),
    ]
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = str(args.library.resolve().parent) + os.pathsep + env.get("LD_LIBRARY_PATH", "")
    with (output / "simulation.log").open("w") as log:
        result = subprocess.run(command, cwd=output, env=env, stdout=log,
                                stderr=subprocess.STDOUT, check=False)
    log = (output / "simulation.log").read_text()
    cycles = [int(x) for x in re.findall(r"^gpu_sim_cycle\s*=\s*(\d+)", log, re.M)]
    instructions = [int(x) for x in re.findall(r"^gpu_sim_insn\s*=\s*(\d+)", log, re.M)]
    kernels = re.findall(r"^kernel_launch_uid\s*=\s*(\d+)", log, re.M)
    passed = (
        result.returncode == 0
        and "GPGPU-Sim: *** simulation thread exiting ***" in log
        and "deadlock detected" not in log
        and re.search(r"^-gpgpu_deadlock_detect\s+1\s", log, re.M) is not None
        and len(set(kernels)) == len(kernels) == len(cycles) == 3
        and all(cycle > 50000 for cycle in cycles)
        and instructions == [3738368] * 3
    )
    report = {
        "passed": passed, "returncode": result.returncode,
        "kernel_cycles": cycles, "kernel_instructions": instructions,
        "command": command,
        "framework_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=framework, text=True).strip(),
        "backend_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=backend, text=True).strip(),
    }
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
