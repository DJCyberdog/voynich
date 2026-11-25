# VRS-094 C — expanded hardware diagnostics and performance profiling

2026-11-25. Parent 06f963b6977d7c709a440390cf03cee4af33bfc5 (PR #98); implementation 500b3fb42c23a63e4eec64d87762e59f753d00ef.

B-tier verified complete for local implementation and regression; its previously documented native and coordinator gaps remain unchanged. C-tier: TECH_PASS locally, not native certification.

| ID | Implementation | Evidence |
|---|---|---|
| C1 | Extended preflight: CPU frequency, swap usage, Windows drive-to-physical-disk mapping through read-only PowerShell storage queries. Only unique exact mappings to known SSD/HDD media are recognized; ambiguous, virtual, network, missing tools and errors remain UNKNOWN. | Actual Linux CPU diagnostic, mock Windows cases (SSD, HDD, unspecified, multiple values, timeout, network path); review diagnostics without importing Torch. Native Windows remains untested. |
| C2 | Optional single-run profiling of validation, planning, admission, model setup, preparation, inference and serialization. Thread-safe phase counts/sums/maxima, instrumented call errors, process CPU time, sampled RSS, system available RAM and sampled CUDA allocator metrics. | Threading, failure, cleanup, mock CUDA allocator, unique-input benchmark parity and phase-integration tests. Native GPU metrics untested. |

Usage from worker directory:
- `python vrs_diagnostics.py hardware . --profile cpu` (review/cpu/cuda; optional --gui). Exit 1 NOT_MET, 2 UNVERIFIED, 0 PASS. Throughput deliberately remains UNKNOWN from diagnostics alone.
- `python vrs_diagnostics.py profile MANIFEST REVIEW ALPHABET MODEL REPORT OUTPUT --device cpu --interval 0.05` (existing opt-in inference, output must be absent). Aggregate profile JSON on stdout, prediction report locally on disk. Failure profile has FAILED status without exception text.
- `OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 python vrs_benchmark.py --device cpu --regions 512 --repeats 3 --unique --profile`

Sampling is not exact peak accounting. The profiler samples process RSS and system available RAM, not the effective cgroup budget; the resource admission planner continues to handle its own limits. CUDA allocator samples are taken after inference calls, not kernel timing, utilization or total device memory; no forced sync/reset. Phase sums may overlap across threads and must not be interpreted as a partition of wall-clock time. Validation/planning/model setup/serialization record completed spans; wrapped admission/preparation/inference additionally count call failures. Profiling adds overhead. No private paths, images, labels or exception messages in profile report; diagnostics are local only and may contain backend diagnostic messages. No change to scientific features, model, thresholds, existing research evidence, autonomous scope or reporting.

## Executed evidence

Linux CPU/Xvfb, Python 3.13.5, Torch 2.10.0+cpu, OMP/MKL threads 2; private original fixtures restored locally. 6 new tests PASS (2.227 s); complete regression 131/131 PASS, 0 failures/skips (22.396 s). Log SHA256 5c69383d182c452f4a254402808faae18467b104b305b9124c6a0edaa12692ad. Actual CPU diagnostic returned NOT_MET on constrained test host, AVX2/dependencies PASS, storage UNKNOWN, throughput UNKNOWN; no minimum profile certification. Diagnostic JSON SHA256 d053c7769f26c0d319514adbe676e667d722e430846c074e848f6d7a3019c66c.

Paired warmup and alternating benchmark trials, 512 distinct generated region images, 4096 candidate rows, 3 trials per mode. Median legacy 7782.41 rows/s vs profiled adaptive 11506.89 rows/s (+47.9%). Exact row/exclusion parity, all adaptive cache counts zero. Sampled process RSS max across profiled trials 282116096 bytes (~269 MiB). Example first adaptive trial wall 0.356s; preparation summed 0.237s, inference summed 0.191s, validation 0.059s; overlapping phase times, not additive. No CUDA hardware or measured GPU utilization. Synthetic generated images and model are engineering fixtures, not a representative manuscript or scientific accuracy benchmark. Benchmark JSON SHA256 34211ae5ec26feb11245827e298650286a863814a7fd2d1a30daf24c5150e7aa.

Verified tested Git blobs: vrs_diagnostics.py 8f94ce3054ab4969a5bfd62cf4d207fa0b976604; test_vrs_diagnostics.py 19c56824920f3ab7065dd8b639bd206a2b6b4d8e; vrs_inference.py 18d150f804965fa9d3663311599965f752ebe311; vrs_benchmark.py 5691191640c52850b34ce14973909bf43bb8fee1.

Native Windows/CUDA, clean distribution installation, representative manuscript-scale performance and autonomous integration remain open. C-tier local work complete. Owner now requests sequential tier work, so assess D next, retaining the prior owner-first requirement and clearly distinguishing optional multi-GPU/workstation capabilities from mandatory native acceptance. No merge, automated reporting or research automation changes.
