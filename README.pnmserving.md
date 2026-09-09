# PNMServing Accel-Sim fork

This fork pins the GPGPU-Sim backend and the official NVBit release for the
PNMServing memory-access experiment. `pnm-toolchain.json` is the dependency
manifest. The backend resets the deadlock detector's progress snapshot when
per-kernel counters reset, and includes optional memory-event observation.
The upstream `SM80_A100` model and trace configuration remain unchanged.

NVBit v1.8 was selected independently from NVlabs' latest release on
2026-09-09. The installer verifies the official archive SHA256 and the
installed core; it does not follow a moving `latest` version at install time.
Updating NVBit requires a manifest change and tracer validation.

## A100 preparation

Use this branch's immutable framework commit on both machines. The setup
script clones the backend commit from the manifest and rejects a different
existing backend. Explicit `GPGPUSIM_REPO`/`GPGPUSIM_BRANCH` overrides are for
development; leave them unset for the PNMServing experiment.

Requirements: Python 3.12+, CUDA 12.8 toolkit, C++ compiler, make, ccache,
flex, bison, makedepend, bc, and zlib/OpenGL/zstd development libraries. Use
PNMServing's `experiments/a100_memory/prepare.py --tracer-only` for capture
tools on A100, or its full preparation for local simulator replay. Both
select this fork's immutable revisions and the same manifest.

The standalone NVBit installation command is:

```bash
bash util/tracer_nvbit/install_nvbit.sh
# An offline/cached archive is also checksum-verified:
bash util/tracer_nvbit/install_nvbit.sh --archive /path/to/nvbit-Linux-x86_64-1.8.tar.bz2
```

Build the tracer with `ARCH=all` to cover sm80 (A100) and sm86 (A6000). Use
`make -B` when changing ARCH because make does not track command-line flag
changes. Run the build through the experiment's ccache wrapper.

For the existing tracer/postprocessor, use `TRACE_LINEINFO=0`: the optional
line-number field currently breaks the upstream LDGSTS operand-pair filter.
Use `ACTIVE_FROM_START=1` and the discovered dynamic kernel IDs to select the
target kernels. The experiment runner implements these settings and audits
all processed cp.async global operands before replay.

## Verification

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

The tests check pinned-backend checkout, rejection of a mismatched checkout,
NVBit checksum failure without deleting an existing installation, repeat
installation, and installed-core validation. The
[three-kernel regression](tests/repeated-kernel/README.md) includes its trace
fixture and a replay command. It fails on upstream `91880c5` and passes with
the snapshot fix while keeping deadlock detection enabled.

Local checks use A6000 traces and the official A100 simulation model. Formal
A100 hardware measurements and hardware/model timing correlation remain
separate validation steps.
