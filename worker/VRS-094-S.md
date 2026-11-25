# VRS-094-S — Hardware diagnostics and resource planning

2026-11-25. Owner target: Windows 11 x64, i5-11400F (6 cores/12 threads), RTX 5060 Ti (16 GiB VRAM), 16 GiB RAM. Default compute preset Performance. No notebook-specific optimization. Higher-capacity profiles may benefit from larger budgets; no mandatory high-end benchmark.

## Status by S-tier gate

| Gate | Implementation | Evidence / outstanding |
|---|---|---|
| S1 hardware/resource detection | PASS | Actual Linux CPU affinity, physical/logical counts, RAM/free disk and visible cgroup v2 limits. Review-only import tested with Torch blocked. Native Windows detection still unverified. |
| S2 RTX CUDA compatibility | IMPLEMENTED / BLOCKED native | Actual-device allocation, matrix multiply, result check, synchronization, architecture/build diagnostics and free/total VRAM probe. Negative probe on CPU host correctly refused explicit CUDA; success/failure behavior tested with mocks, no RTX hardware tested. |
| S3 adaptive RAM/VRAM planning | PASS local | Measured headroom and caller-supplied per-workload base/item/disk byte estimates produce bounded budgets, worker count and operational inference batch ceiling. Synthetic owner/high-capacity tests; not measured model memory/throughput. |
| S4 OOM/swap protection | PASS API / integration pending | Preflight and fresh-memory admission refuse insufficient resources; allocation exceptions normalize to ResourceBlocked without retry/backend switch. Advisory cooperative API, not process-wide OS enforcement, no guarantee against external memory contention, incorrect estimates or OS termination. Coordinator and stage producers must call it at safe boundaries, manage cumulative allocations and persist checkpoints. No live pipeline OOM/power-loss test. |
| S5 Performance default | PASS | Default preset allocates 90% of headroom after reserve (not 90% CPU/GPU utilization guarantee). Optional Balanced/Quiet; reserves 2 GiB or 1/8 total RAM, 1 GiB or 1/16 VRAM, 5 GiB disk. These are engineering starting parameters, not benchmarked defaults. |

## Run the diagnostic

From the worker directory in an existing Python environment, install the optional diagnostic dependency (`python -m pip install -r requirements-hardware.txt`). Compute CUDA probe uses an explicitly installed compatible PyTorch build and driver; no automatic installs or network calls by this module. The full CPU/CUDA install profiles remain A-tier. Run `python vrs_hardware.py . --backend review` for lightweight inspection or `python vrs_hardware.py . --backend cuda` for a native compute test. Exit 1 if explicitly requested CUDA cannot execute. Automatic selection may fall back before a run, never after backend binding. `--workload` takes a trusted local JSON estimate with ram_base, ram_item, vram_base, vram_item, disk (bytes) and items. No guessed per-model estimates or scientific setting changes. Operational batch ceiling must not silently change training parameters or alter accepted scientific outputs.

## Executed evidence

Linux CPU/Xvfb, Python 3.13.5, Torch 2.10.0+cpu, psutil 7.2.2. Actual host diagnostic showed 4 allowed logical CPUs, 4 GiB effective RAM limit and no CUDA. New hardware tests: 10/10 PASS (0.912 s). Complete integrated test suite: 105/105 PASS (21.954 s), zero skips/failures, including original locally recovered pinned private fixtures. Log SHA-256: 68c7d699aff9f9c769a299e37decf6ed4a3a03f3c8bcba560131f1b8e135bdaf. No private inputs committed. Source blob b79664361a02056422c09b50072e4af4d5a66a6c; test blob 1bc0f729faa93ccb5652a9d28741cdf390b39d55 verified against local tested bytes.

Illustrative synthetic workload only: 1 GiB host base + 32 MiB/item, 2 GiB GPU base + 64 MiB/item, 20 GiB disk, 10,000 items. Mocked owner profile (13 GiB available RAM, 14 GiB free VRAM) yields 10 workers / batch ceiling 155; larger mock (32 threads, 128 GiB RAM/110 free, 48 GiB VRAM/45 free) yields 28 workers / 572. These are calculated ceilings, not actual VRS batch sizes or throughput claims.

No changes to legacy worker source, research scope, experiments, existing automation, model calibration or publication. Native owner hardware evidence and actual coordinator integration remain open; S-tier full acceptance is not claimed. A-tier can proceed with producer estimates, performance benchmarks and install profiles independently. Owner merge gate retained.
