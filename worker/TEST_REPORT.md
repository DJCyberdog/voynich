# v0.2.0 validation — 2026-11-25

Environment: Linux, Python 3.13.5, PyTorch 2.10.0+cpu, Pillow 12.3.0, PyMuPDF 1.26.7. Existing dependencies only. No Windows or RTX access. GUI test used a virtual X display (Xvfb).

Command: `xvfb-run -a python -m unittest -v test_worker test_pipeline test_gui`

Result: **11/11 PASS** on synthetic PDF fixtures. Four core tests, six pipeline tests, one real Tk GUI test. Checks include source/crop hashes, independent-reviewer-ID guard, group leakage and disagreement exclusions, checkpoint/resume equal losses and counts, explicit CPU fallback, deterministic full-page proposal output, queue job authoring and status, duplicate IDs, local Git import and wrong hash rejection, malformed job isolation, foreground poller stop, queue retry, workspace escape and unknown options rejection, exclusive lock, end-to-end queue training/inference/export and tampered result rejection, GUI button invocation/save/reopen/resume/reviewer guard.

Additional command `python cuda_smoke.py`: exited 1 with `CUDA required: CUDA unavailable`, as expected in CPU-only environment. This is a fail-closed check, not a successful CUDA run. No real manuscript data, true classification accuracy, glyph recognition or scientific acceptance tests were executed. Remote GitHub sync was not tested or implemented; only local Git import and reviewed aggregate export are implemented.

The unchanged core/test files retain their original Git blobs. New pipeline blob `ba640d28eaef8f57ef2eeb70a9852e87f00abf05`, pipeline tests `7f7c1f8ade75076fe509ef861b2d53e262effdac`, GUI test `df95231b89bbb38b44dc9c99c0d52a330d03fc6f`.
