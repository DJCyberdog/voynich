# VRS-094 A — inference, install profiles and preflight

2026-11-25. S-tier parent b5187b350dbbdc56e480771dbb5d65d4c798cfd7. Initial A implementation 613d6203eb9d209e3cd8c11c9c9b937a14026d88. Owner desktop remains mandatory native performance target. Status: local technical PASS for implemented interfaces; full native and distribution acceptance OPEN.

| Gate | Evidence | Remaining |
|---|---|---|
| A1 adaptive CPU parallelism | Bounded thread pool, region-grouped decode, configured Torch thread budget, order/cardinality tests | Native throughput/tuning |
| A2 inference batching | Resource-based RAM/VRAM ceiling, two-chunk host budget, fixed model/features/thresholds | Measured model peak calibration and representative GPU parity |
| A3 CPU/GPU overlap | Bounded producer/consumer prefetch, admission before preparation, no fallback on failure | Actual CUDA overlap and coordinator/checkpoint integration |
| A4 benchmark | Paired synthetic CPU trials at 512 and 4096 candidates; exact row/exclusion parity | Representative manuscript-scale and owner CUDA benchmark |
| A5 install profiles | Separate pinned top-level review/compute/CPU/CUDA requirements; isolated review tests without ML packages | Clean install from original wheels, transitive dependency lock/hashes, native packaging |
| A6 preflight | CPU/RAM/storage/capability checks, AVX2, Windows build, GUI resolution, dependency versions, explicit UNKNOWN | Windows SSD mapping, native OS/GPU tests and representative performance |

## Implementation

New opt-in adapter vrs_inference.py retains the original glyphs.py/worker.py, model SHA binding, features, classifier and fixed thresholds. Uses region grouping and NumPy stack, with at most one prefetched chunk. Results are accumulated in RAM and written at completion; this is not streaming or resumable whole-manuscript processing. Resource estimates are provisional rather than OS-enforced bounds. No automatic scientific experiments or model training; UNADJUDICATED status. Legacy CLI unchanged.

Expanded preflight vrs_preflight.py checks AVX2 on Linux or Windows via the relevant platform API; Windows 11 build, display where requested, Linux direct block-device rotational flag, and pinned package versions. Ambiguous, virtual or Windows storage mapping remains UNKNOWN. Benchmark proof deliberately UNKNOWN, so a successful probe alone cannot yield certified support. Run python vrs_preflight.py WORKSPACE --profile review|cpu|cuda [--gui]. Native Windows implementation is not executed in this environment. Actual Linux CPU host was correctly marked NOT_MET (4 allowed logical CPUs, 4 GiB effective RAM, about 32 GB disk free); AVX2 and pinned CPU dependency versions passed. This does not lower the product requirements.

## Executed evidence

Linux CPU/Xvfb, Python 3.13.5, Torch 2.10.0+cpu, NumPy 2.3.5, Pillow 12.3.0, PyMuPDF 1.26.7, psutil 7.2.2. OMP/MKL threads 2. All private pinned fixtures available locally; not committed.

- Initial A tests: 6 new, 111 integrated PASS, zero skips (24.016s).
- Follow-up preflight: 6 new, 117 integrated PASS, zero skips (21.197s). Log SHA256 83ebb77227b741769b702f12fc32ac55b93171851a687eb7820ee0cf0f7778b9.
- Review-only isolated venv --without-pip, no system-site-packages; copied already-installed Pillow 12.3.0 and psutil 7.2.2 and their metadata/shared libraries. Confirmed Torch, NumPy and fitz absent via find_spec. Tk/Pillow review imports and hardware snapshot passed; 15 review/GUI/tray tests PASS under Xvfb (0.641s). Log SHA256 2ca25c84f2ad6314d18675bfba3c92f6667bf81ec6ebeffd19d30da77bee153f. Original wheel download unavailable (pip reported no matching distribution in this environment). No clean wheel install claim.
- Synthetic benchmark, alternating legacy/adaptive order, warm-up, three trials each, identical generated images and model. 512 candidates: median 6936.62 -> 9768.37/s (+40.8%). 4096 candidates: median 8032.55 -> 16720.41/s (+108.2%). Exact prediction row and exclusion parity for all compared runs. Whole process max RSS 275156 KiB for combined 4096 benchmark, not per-mode peak. Benchmark JSON SHA256 20ae4f3c51c59535404dff9b77bf0047c77a5ae15401236dcc66a02ba6506438. Synthetic timing does not extrapolate to full manuscript or RTX 5060 Ti.

Commands: xvfb-run -a python -m unittest discover -v (private fixture env vars set); OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 python vrs_benchmark.py --device cpu --regions 512 --repeats 3.

Tested Git blobs: vrs_inference.py e64e9cfb2edd7fb1a44ef417e6483a9bf05ec852; test_vrs_inference.py c5aa5dc13c260e508804be3020a0a2581c01cfab; vrs_benchmark.py 47c1443b61ccec0e05e64ff936cd220442fffe97; vrs_preflight.py a75fda1ece5a1475b4f79e14e0b7fa9b621b7cef; test_vrs_preflight.py 90a217148b265abfd0239268f79eeba1b5d3bf53.

No native GPU performance claim, no experiment, no scope expansion, no publication, no merge. A-tier local evidence substantially complete, native target and distribution evidence still open. B-tier work and VRS-095 integration can proceed without repeating identical CPU regression-only cycles.
