# VRS-094 E — optional alternative GPU backend qualification

2026-11-25. Parent fcc5aac4f02709e1f6fc5c703f8c289dde3bbfed; implementation 9bef2e6271cefb3450b41f8fcb605d60a84bdb08. Owner primary target remains i5-11400F / RTX 5060 Ti / Windows 11. No new mandatory dependency, automatic installation, research experiment, training, publication or merge.

| Gate | Implementation | Native status |
|---|---|---|
| E1 ROCm | Explicit HIP build/device validation, real classifier-operator probe, global free/total memory and bounded local qualification with CPU mirror. | BLOCKED: no compatible AMD hardware/build, no clean wheel install. Linux candidate profile defined; Windows ROCm profile must be chosen from AMD's actual supported OS/GPU/driver/Python matrix, not reused blindly. |
| E2 Intel XPU | Explicit torch.xpu selection, real operator probe, synchronize, global free/total memory requirement and bounded local qualification. | BLOCKED: no Intel XPU hardware/runtime or clean wheel install. Missing telemetry blocks execution. |
| E3 DirectML | Explicit native Windows privateuseone device resolution and small classifier-operator probe; separate probe-only package profile. | BLOCKED for workload execution: no reliable free-memory admission implemented; native operator support, fallback behavior and package compatibility unverified. Do not claim a usable production backend. |

All three are opt-in qualification capabilities, not automatically eligible for manuscript processing. The existing adaptive CPU/NVIDIA CUDA path and default Performance configuration remain; the new CUDA probe now explicitly rejects HIP builds, which PyTorch exposes through the same torch.cuda namespace. Original worker.py/glyphs.py intentionally unchanged for model provenance; legacy CLI may still refer to HIP via CUDA terminology.

## Commands

From worker/ in a suitable explicitly provisioned local environment:
- `python vrs_backends.py probe rocm --index 0`
- `python vrs_backends.py probe xpu --index 0`
- `python vrs_backends.py probe directml --index 0`
- `python vrs_backends.py qualify MANIFEST REVIEW ALPHABET MODEL REPORT OUTPUT --backend rocm --index 0` (or xpu).

Probe validates the actual existing classifier on a small deterministic fixture, device identity, and for ROCm/XPU synchronization and memory counters. PROBE_PASS does not establish production or native acceptance. Every qualification batch compares exact label index, distance and margin against the unchanged CPU classifier and blocks on disagreement, nonfinite results, observed operator fallback warnings or unavailable resources. Warning monitoring cannot prove absence of all internal runtime fallback. CPU mirror adds computation overhead; no acceleration or equivalent throughput claim. DirectML qualify deliberately fails closed, even if its tiny probe passes. Bounded estimates reuse existing planner/admission contracts, no cache/prefetch/training; source data must remain immutable and qualification CLI should run in its own process. Resource limits are advisory; manifest/model loading and report accumulation are not OS-enforced. Output staged locally and published via no-replace hard link (filesystem must support it). No coordinator, training or multi-GPU alternative-backend integration.

## Candidate package profiles (not certified installations)

Separate local environments only; no installation into a functioning CUDA environment. Existing requirements-compute.txt provides common dependencies for ROCm/XPU; their backend-specific requirements files are installed separately using the named official index. Linux ROCm candidate torch 2.10.0 / ROCm 7.1, Intel XPU torch 2.10.0 / xpu index. Windows ROCm candidate wheel must be selected after verifying vendor compatibility; no Windows lock supplied. DirectML candidate torch-directml 0.2.5.dev240914 in isolated Python 3.12 environment, probe-only; dependencies intentionally not merged into current PyTorch 2.10 environment. Package files pin top-level packages only; full hashes, transitive locks, source verification and clean offline installs belong to distribution acceptance. No package downloads performed.

Official references checked 2026-11-25:
- https://docs.pytorch.org/docs/stable/notes/hip.html
- https://pytorch.org/get-started/previous-versions/ (2.10.0 ROCm Linux candidate)
- https://docs.pytorch.org/docs/stable/notes/get_start_xpu.html
- https://docs.pytorch.org/docs/stable/xpu.html
- https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/windows/windows_compatibility.html
- https://learn.microsoft.com/en-us/windows/ai/directml/pytorch-windows
- https://pypi.org/project/torch-directml/

## Executed evidence

Linux CPU/Xvfb, Python 3.13.5, torch 2.10.0+cpu, original v0.8.1 archive and private pinned fixtures restored. The unchanged glyphs.py and resource planner were checked against parent Git blobs (3d817d2c8781e50a0479980d232d25fccac493f4 and 28bec97aa6124d84dd01d9c24fbbc019520d7feb). The original hardware file was verified against b79664361a02056422c09b50072e4af4d5a66a6c before the HIP guard edit.

- Seven new tests PASS (0.049 s): identity, invalid device, DirectML probe-only, memory failure, real CPU classifier parity/mismatch/fallback warning, probe status, real image decode/qualification using simulated accelerator transport and memory. Actual prediction rows match legacy eight-row fixture, pressure/parity failures leave no output, thread setting restored.
- Recovered baseline + new tests: 68/68 PASS, zero skips or failures (20.637 s), original 61 baseline tests plus 7 new. This is not the entire D-tier parent suite. Previously documented 138/138 is historical; no 145-test integrated result claimed. Full current branch regression remains open; no successful CI run claimed.
- Actual local probes: ROCm BLOCKED (no HIP build), XPU BLOCKED (no available device), DirectML BLOCKED (Linux rather than native Windows). No actual GPU execution.
- Log SHA256 new tests 6726c985aaf57e1f8060dbf383d89e7272a0684131348ee7bc7f8270e3e3abb1; baseline+E regression ea0e4e451e2c6c43076762b72230f74dfe35b599ba15f86b0dfd0080e5c3ee70.
- Exact tested source blobs: vrs_backends.py 49bc2ba4db0b747214e5efb29fbd01fad224a6ca; test_vrs_backends.py 24020031f979a1c0d695164998b15bb0321691ba; vrs_hardware.py e7f04c73297cf0499b240972f385031f1c75a06a.

E1/E2 implementation local qualification PASS, native acceptance BLOCKED. E3 partial, production admission BLOCKED. E-tier is the final defined tier but not a full production acceptance PASS. Optional alternative backends must not block owner CUDA-first work. Continue VRS-095 core implementation while retaining explicit outstanding native/distribution/integration gates; no repeating identical CPU-only test cycles as substitute for native hardware.
