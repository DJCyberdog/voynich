# VRS-094 B — resource overrides, presets and adaptive feature caching

2026-11-25. Parent 802898603f74efc02664afd94bacaa7e508256bf (PR #97); implementation ac9d84596ebeb695071999e29ab4d0afcfc71e77.

Status: **TECH_PASS for the four B-tier local interfaces and their CPU inference integration.** Native owner CUDA/Windows and larger-hardware throughput are not established. General minimum requirements unchanged; the owner desktop remains the primary performance target. Performance is the default.

| ID | Implementation | Local evidence |
|---|---|---|
| B1 | Explicit operational ceilings on CPU worker budget, host RAM, VRAM, disk, feature cache and inference batch items. Limits can only tighten the automatic resource plan; invalid/impossible values rejected. Exact final report size also checked against disk budget. | Limits and failure tests, including a single-thread execution path and restoration of Torch thread settings. |
| B2 | Silent (alias for Quiet), Balanced and Performance presets integrated into the opt-in adaptive inference path. | All three presets preserve exact legacy prediction rows with CPU and batch restrictions. |
| B3 | Thread-safe per-run LRU feature cache keyed by verified crop SHA-256 and box. Cache only repeated source hashes; disabled for unique sources. Immutable float32 byte payloads; no label/decision propagation, persistent cache, private uploads or cross-run reuse. Cache reduces monotonically under RAM pressure; if the minimum demand cannot fit, block without a final output. | Eviction, resize, concurrency, duplicate-source cache hits, pressure and exact-row parity tests. |
| B4 | Adaptive worker and batch ceilings grow with usable host/device resources rather than owner-specific hard caps. | Synthetic target and higher-capacity resource snapshots; no native high-end throughput claim. |

## Configuration

From worker directory use existing adaptive predict command and optionally append `--preset silent|balanced|performance --limits /private/resource-limits.json`. Quiet remains a backward-compatible alias. JSON keys are optional nonnegative integer byte budgets or positive integer worker/batch ceilings; unknown fields rejected. Cache bytes 0 disables cache. Example local restriction only (not recommended owner Performance settings):

```json
{"cpu_workers": 6, "ram_bytes": 8589934592, "vram_bytes": 8589934592, "disk_bytes": 10737418240, "cache_bytes": 67108864, "batch_items": 64}
```

No overrides are needed for default adaptive Performance. Effective preset, worker/Torch thread count, batch, requested limits and cache stats are recorded in local operational output. Limits are cooperative admission/planning ceilings, not OS-enforced process caps or exact device allocation limits; initial manifest/model reading and final rows/serialization still require memory, library overhead can vary, and trusted local inputs must be immutable. Torch thread settings are process-global and restored under an adapter-local lock; unrelated concurrent Torch operations in the same process are unsupported. Only the opt-in inference adapter uses this policy; autonomous stage/checkpoint integration is still VRS-095. Silent limits resource use but does not control fans, voltage or power. No scientific settings, training protocol or acceptance policy changed.

## Executed tests and benchmark

Linux CPU/Xvfb, Python 3.13.5, Torch 2.10.0+cpu, OMP/MKL threads 2, all original pinned private fixtures locally available. Eight new tests plus existing suite: **125/125 PASS**, zero skips/failures, 21.369 s. Command: `xvfb-run -a python -m unittest discover -v` with private fixture environment configured. Log SHA-256 6f78f6bdb7983402e8c616433cbaebfd720b301515bfe03b1de58226f05f4b0a. An initial cache eviction accounting bug was exposed by tests, fixed and retested.

Existing synthetic benchmark: `OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 python vrs_benchmark.py --device cpu --regions 512 --repeats 3`. 4096 candidate rows, warmup and alternating paired trials, exact legacy prediction-row/exclusion parity. Median legacy 8365.05 candidates/s, adaptive B 38149.52 candidates/s (4.56x). Crucial limitation: generated benchmark repeats only four distinct region images, so each timed adaptive run had 4064 cache hits / 32 misses, 147456 accounted cache bytes. This deliberately favorable repeated-input workload is not a representative real-manuscript benchmark or a measured improvement over A on the same run. Actual unique-crop workloads cannot assume this speedup; no scientific or GPU claim. Benchmark JSON SHA-256 28b31fec299a733b26c462c20b8c5ce1591aaf19b20da8289db373b20020bb5e.

Illustrative synthetic resource-planning workload (same assumptions as S-tier, 1 GiB host base, 32 MiB/item, 2 GiB VRAM base, 64 MiB/item, 20 GiB disk, 10000 items): mocked owner 12 allowed threads/13 GiB available RAM/14 GiB free VRAM, Silent 4 CPU slots/40 items, Balanced 8/92, Performance 10/134. Mock high-capacity 32 threads, 128 GiB total RAM/110 available, 48 GiB VRAM/45 free: Performance 28/572. These are not actual execution throughput or measured GPU memory capacities. B planner includes two host chunks plus cache; earlier S single-chunk figures are not directly comparable.

Verified exact tested blobs: vrs_resources.py 28bec97aa6124d84dd01d9c24fbbc019520d7feb; test_vrs_resources.py 08b00fe3bdbc23c8ba17367a5f81856071e4a1be; vrs_inference.py 76ffb06d9d12aabec9f095e39bffc43e07278341.

No new research EXP, scope expansion, automated publication, research automation change or merge. C-tier extended diagnostics and profiling are optional. Native S/A gates, clean installs, production streaming/checkpoint and coordinator integration remain open. Next core milestone VRS-095, unless owner requests C-tier.
