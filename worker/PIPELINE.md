# Voynich GPU Worker v0.2.0 — offline pipeline

The v0.1.0 core (`worker.py`) remains unchanged, so existing checkpoint code hashes stay compatible. Version 0.2.0 adds `pipeline.py` and a local, reviewed job queue. This is a development release, not a validated manuscript recognizer.

## Setup and acceptance

Follow [README.md](README.md) for the private PDF, Python virtual environment, Tk, Pillow, PyMuPDF and a compatible PyTorch build. Git must be installed for commit-pinned job import. Use a private local NTFS workspace on Windows (atomic queue submission uses hard links). No automatic installation or model download is performed. Linux CPU and virtual-display GUI tests passed; Windows, CUDA and actual RTX hardware remain untested.

```powershell
$P = ".\.venv\Scripts\python.exe"
& $P -m unittest -v test_worker test_pipeline test_gui
& $P worker.py doctor --device cuda
& $P cuda_smoke.py
```

## Queue and local workflow

All job inputs must be relative to a private workspace, and are bound to SHA-256 hashes. The queue supports `prepare` (guided regions), `propose` (full-page ink grid), `train` (two reviewer files and frozen physical-leaf split) and `predict` (completed, hash-matched checkpoint). It does not run arbitrary commands, upload data, or automatically trust new repository commits. `make` builds a job without submitting it; review the JSON first. Example commands assume your actual `voynich.pdf`, `review.csv` and verified `groups.json` are already in `C:\private\voynich`.

```powershell
$W = 'C:\private\voynich'
& $P pipeline.py make $W guided01 prepare guided01.json --input pdf=voynich.pdf --input review=review.csv --input groups=groups.json
& $P pipeline.py submit $W guided01.json
& $P pipeline.py status $W
& $P pipeline.py process $W
```

For the owner-pinned EXP-0038g source, verify the PDF hash is `d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c` before authoring a job. The `make` command records local bytes, not source authenticity. See README for the separate human annotation and physical-leaf split requirements. Example full-page proposal and training jobs:

```powershell
& $P pipeline.py make $W grid01 propose grid01.json --input pdf=voynich.pdf --input groups=groups.json
& $P pipeline.py submit $W grid01.json
& $P pipeline.py process $W
& $P worker.py annotate "$W\outputs\guided01\manifest.json" "$W\reviewer_a.json" reviewer_a
# Second independent reviewer: same manifest, separate output, no answers shared.
# Only after both annotations and the frozen split.json exist:
& $P pipeline.py make $W train01 train train01.json --input manifest=outputs/guided01/manifest.json --input left=reviewer_a.json --input right=reviewer_b.json --input split=split.json --options '{"device":"cuda","epochs":8,"batch":16,"seed":42}'
& $P pipeline.py submit $W train01.json
& $P pipeline.py process $W
& $P pipeline.py make $W pred01 predict pred01.json --input manifest=outputs/grid01/manifest.json --input checkpoint=outputs/train01/checkpoint.pt --input report=outputs/train01/report.json --options '{"device":"cuda","batch":16}'
& $P pipeline.py submit $W pred01.json
& $P pipeline.py process $W
& $P pipeline.py export $W train01 train01-share.json
```

Run `pipeline.py watch $W` to process locally submitted jobs in the foreground every 15 seconds (Ctrl+C stops it). No GPU or PC is remotely controlled by this release. `status` reads persisted PENDING/RUNNING/FAILED/COMPLETED records. The exclusive workspace lock prevents simultaneous processors; if a process is forcibly killed, verify it really stopped before manually removing `worker.lock`. A failed or interrupted job is never silently repeated: use `process $W --retry JOB_ID` for an unchanged job. Training resumes at epoch boundaries if the matching checkpoint exists. Incomplete prepare/propose/predict output directories require explicit inspection and moving aside before retry. A completed report with a stale journal must be reconciled manually; never rescore a heldout set just to repair metadata. Do not edit submitted jobs: use a new ID. All files stay local until explicitly shared.

## Reviewed Git handoff

After fetching the project's repository yourself, `pipeline.py import-git ROOT CLONE FULL_COMMIT_SHA worker/jobs/ID.json JOB_SHA256` imports exactly one explicitly approved JSON blob from your local clone. It verifies the blob SHA-256 and locally available input hashes. `process` or `watch` can then execute it. No automatic network fetch, push, remote polling, Git credentials or arbitrary shell commands. Upload only the reviewed `export` aggregate to a branch/PR; it excludes image pixels, per-region scores, file paths, model weights and reviewer identifiers. The journal and detailed local output are private. End-to-end remote submission and automatic return of reports remain future work, subject to explicit approval and authentication.

## Scientific boundaries

- Full-page proposals use a fixed overlapping 200-dpi tile grid and dark-pixel fraction, not a validated text detector; no claim of glyph coverage, precision or recall. Only pages in your explicitly verified group map are processed.
- Prediction labels are `script`, `non_script`, or `unknown`; softmax scores are uncalibrated and the fixed 0.2/0.8 thresholds are engineering defaults. Predictions are not independent test evidence.
- Training uses agreed binary labels from two reviewer files and a leaf-group holdout; this does not prove reviewer independence or correct physical mapping. Real controls must include ink-bearing drawings and other hard negatives. Keep all abstentions and failures.
- EXP-0038g remains NOT_MET (59/74); no change to thresholds or acceptance gates. No glyph classifier, semantic inference, or decipherment claim. Those require rights-cleared real reference data and separate preregistered experiments.

See [TEST_REPORT.md](TEST_REPORT.md) for the actual validation scope.
