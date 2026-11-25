# v0.4.0 — local multiscale region proposals

This development release adds `regions.py` without changing the v0.1 model, v0.2 queue, v0.3 bridge or EXP-0038g. It is opt-in and local only; no remote job type or automatic publication was added. Existing checkpoints remain compatible. Dependencies: NumPy (already used in the research environment), PyMuPDF and Pillow. No installation is performed by the worker.

## Generate candidates

Use the locally held PDF, the expected source SHA-256 and a verified page-to-physical-leaf group map as described in README.md. Example PowerShell (replace paths with actual local paths):

```powershell
$P = '.\.venv\Scripts\python.exe'
& $P regions.py propose C:\private\voynich.pdf d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c C:\private\groups.json C:\private\regions01 --pages 176 177 --max-regions 30000
```

Omit `--pages` to process every page in the explicit group map (maximum 213 pages per invocation, not a claim of physical folio count). The 200 dpi algorithm uses three fixed page-relative window scales, approximately half-window stride, includes the terminal edges, and filters by dark-pixel fraction with an integral image. Exact duplicate windows are removed; overlapping windows are retained. These are ink candidates, not detected writing. All source/output pixels remain local. On exceeding the candidate budget, the run stops without a complete manifest; use a fresh output directory or explicitly select smaller page batches. The original v0.2 proposal command remains available. The existing classifier can consume a nonempty v0.4 manifest via `pipeline.py predict` jobs; its accuracy is not established.

## Evaluate region localization

A separate reviewer must annotate all text boxes on each selected reference page, including pages with no text (empty list). Freeze the target unit (e.g. words versus lines), selection and independent physical-leaf holdout before scoring. The reference uses normalized `[x0,y0,x1,y1]` coordinates, top-left origin, relative to the same rendered page. Example schema (illustrative values only):

```json
{"source_sha256":"<actual PDF SHA256>","groups_sha256":"<actual group-map SHA256>","reviewer":"reviewer01","exhaustive":true,"pages":{"176":[[0.1,0.2,0.3,0.24]],"177":[]}}
```

```powershell
& $P regions.py evaluate C:\private\regions01\manifest.json C:\private\reference.json C:\private\evaluation01.json
```

The evaluator checks source/group identity, crop hashes, page coverage, duplicate IDs and valid reference boxes. It reports proposal recall (any overlapping proposal) and one-to-one localization precision/recall at fixed IoU thresholds 0.3, 0.5 and 0.7, with maximum-cardinality matching. It counts duplicate detections against one-to-one precision, and emits null for undefined ratios. All page-level results stay local. The v0.2 manifest lacks processed-page dimensions; direct comparison with the old detector requires an explicit provenance-preserving adapter, not supplied here. No threshold is a scientific acceptance gate. Reviewer independence/exhaustiveness cannot be verified by software. An unmatched proposal is not necessarily a drawing. Glyph recognition and semantic validation are outside this release.

## Validation

`xvfb-run -a python -m unittest -v test_worker test_pipeline test_gui test_bridge test_regions`: 22/22 passed on Linux CPU with synthetic PDFs and simulated GitHub API. Four new tests check edge coverage, repeatable proposals and budget exhaustion, one-to-one matching including reassignment, and reference/metric validation. The metric fixture deliberately uses a known proposal box to test arithmetic, not manuscript accuracy. No Windows, RTX, live API, real manuscript inference, independent annotation, or full-page recognition accuracy has been accepted. The original 59/74 NOT_MET remains unchanged.
