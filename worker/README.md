# Voynich GPU Worker 0.1.0

**Release 0.2.0:** The unchanged core is extended by the [offline pipeline guide](PIPELINE.md) and [test report](TEST_REPORT.md). Follow those for the current queue, inference and validation status.

Offline developer preview for EXP-0038g follow-up. It is a crop classifier and annotation tool, not a glyph recognizer or decipherment system. The original EXP-0038g readiness thresholds remain unchanged. No images, labels, model weights, or manuscript PDF are bundled or uploaded by the worker.

## Setup (Windows 11)

Use Python 3.11 or 3.12 with Tk support. No installer runs automatically. In PowerShell, in this directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install Pillow PyMuPDF
```

Choose the Windows/Pip CUDA build of PyTorch compatible with your RTX 5060 Ti and NVIDIA driver from https://pytorch.org/get-started/locally/ (use a Blackwell-compatible build; a CPU wheel will not use your GPU). Run the command supplied by PyTorch using the virtual environment's Python. Installation is a separate, owner-controlled step. For a CPU-only environment, use the CPU wheel instead.

```powershell
.\.venv\Scripts\python.exe worker.py doctor --device cuda
.\.venv\Scripts\python.exe -m unittest -v test_worker
.\.venv\Scripts\python.exe cuda_smoke.py
```

The doctor performs a small CUDA matrix multiplication, not merely device enumeration. `--device cuda` fails closed if CUDA cannot run; `--device auto` reports a reason and uses CPU if the initial CUDA probe fails. It does not silently restart failed GPU training on CPU. Use `--device cpu` to request CPU explicitly. If the GPU probe passes, run the supplied cuda_smoke.py for actual synthetic CUDA training; the unittest suite trains on CPU only.

## Local workflow

Use a private workspace outside Git. Start with the owner-held PDF, SHA-256-pinned to `d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c`. The review CSV format is compatible with EXP-0038f; required columns are `review_id,page,text_x,text_y`. Page numbers are 1-based PDF indices and centers normalized to the rendered page. A curator must add genuinely non-writing, ink-bearing controls; the existing 74 proposed writing regions alone are not a balanced or independent dataset. Avoid exposing the owner key or prior labels to reviewers.

Provide `groups.json` mapping every used PDF page number (string) to a curator-verified physical leaf or larger non-overlapping provenance group. Merge recto/verso and foldout panels into the same group where appropriate; if grouping is uncertain, group conservatively or exclude the region before freezing inputs. No assumption that a PDF page equals a physical folio. Examples use invented groups and must not be used as actual mapping.

```powershell
$P = ".\.venv\Scripts\python.exe"
& $P worker.py prepare C:\private\voynich.pdf d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c C:\private\review.csv C:\private\groups.json C:\private\dataset
& $P worker.py annotate C:\private\dataset\manifest.json C:\private\reviewer_a.json reviewer_a
& $P worker.py annotate C:\private\dataset\manifest.json C:\private\reviewer_b.json reviewer_b
```

GUI: 1 = script, 2 = non-script, 3 = unknown/mixed; arrow keys navigate. Each choice is saved immediately. Separate reviewers must not see one another's answers. Distinct reviewer IDs are a software check, not proof of human independence. The worker only learns from agreed script/non-script labels; missing, mixed and disputed annotations are counted as exclusions.

Freeze a physical-group `split.json` with `train` and `test` lists *before* training, with both classes in both subsets and no overlap. Use a genuinely unexposed holdout for confirmatory research. Exact image duplicates across subsets are rejected; near-duplicate and folio mapping validation remain curator responsibilities. Freeze training settings before seeing holdout outcomes.

```powershell
& $P worker.py train C:\private\dataset\manifest.json C:\private\reviewer_a.json C:\private\reviewer_b.json C:\private\split.json C:\private\run01 --device cuda --epochs 8 --batch 16 --seed 42
```

To resume after interruption, repeat the exact same command with `--resume`. Resume is at epoch boundaries; an incomplete epoch is recomputed. The model/optimizer checkpoint binds input hashes, code hash, device/build and fixed settings. Do not load untrusted checkpoints. Use separate run directories; do not run two writers concurrently. Completed runs refuse a second score in the same directory. Softmax outputs are not calibrated probabilities; the fixed 0.2/0.8 abstention thresholds are engineering defaults, not approved scientific acceptance gates. The held-out score counts abstentions against sensitivity/specificity/accuracy and also reports coverage and annotation exclusions.

## Local jobs and exports

`python worker.py run job.json` executes one explicitly selected local JSON job with action `prepare` or `train`, no arbitrary shell execution and no remote polling. See `example_job.json`; edit the paths first. Only run trusted, reviewed jobs; their file paths refer to your local computer. `report.json` is an aggregate report with hashes, device, counts and reproducibility settings; inspect before manually sharing it with the project. Keep `checkpoint.pt`, image crops and annotation files private. No automatic upload or Git credentials required. GPU validation, automatic task queue/remote synchronization, full-page text detection, glyph recognition and blind independent manuscript validation are not yet implemented or completed.

## Test record

CPU tests executed on Linux with Python, PyTorch 2.10.0+cpu, Pillow 12.3.0 and PyMuPDF 1.26.7: 4/4 unittest cases passed. Synthetic PDF preparation, hash rejection, split leakage rejection, disagreement exclusion, reviewer-ID guard, CPU training, interrupted checkpoint/resume equivalence, completed-run guard, CPU fallback and explicit CUDA failure were checked. The GUI was not interactively tested in this headless environment, nor was Windows or CUDA training. No manuscript performance result is claimed.
