# Repeated-kernel deadlock regression

The fixture contains three complete repeated GEMMs with two CTAs per kernel.
It was captured with official NVBit v1.8 on RTX A6000 (sm86), `ARCH=all` and
`TRACE_LINEINFO=0`, then processed by Accel-Sim at `d930ad6d`.
The smoke job used `M=128, N=128, K=4096`, `BM=64, BN=128, BK=32`, 128 threads,
two pipeline stages and the PNMServing canonical weight layout. Inputs were
synthetic; traces contain instructions and addresses, not tensor values.
`manifest.json` records the binary trace hashes and the validated copy totals.

This is a simulator regression using the unchanged `SM80_A100` configuration.
It does not compare A6000 hardware timing to A100 hardware timing.

From the framework root, after building the simulator:

```bash
python3 tests/repeated-kernel/run.py \
  --library gpu-simulator/gpgpu-sim/lib/gcc-13.3.0/cuda-12080/release/libcudart.so \
  --output /tmp/repeated-kernel-check
```

Select the library path for your compiler/toolkit. The output directory must
be new; the runner retains its log and JSON status on failure. No GPU is
needed for replay. Deadlock detection remains enabled, and the test requires
all three kernels to finish with the expected instruction counts.

The upstream backend `91880c5` completes two kernels (99,070 and 98,088
cycles), then reports a deadlock at cycle 50,000 of the third kernel even
though a writeback occurred one cycle earlier. `update_stats()` reset the
instruction counter but retained the previous kernel's progress snapshot.
After resetting that snapshot in the same function, all three kernels
complete (99,070, 98,088 and 98,088 cycles in the checked local build).

Set `PNMSERVING_MEMORY_EVENTS` to a file/FIFO to repeat with observation enabled.
Compare cycles and initialized counters against the disabled run; the
upstream uninitialized `n_ref_event` printout must be excluded.
