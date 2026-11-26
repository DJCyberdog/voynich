# v0.7.0 — local technical end-to-end validation

The local validation harness connects the existing guided crop, binary classifier, glyph prototype model, pixel-only projection, and native IVTFF alignment modules. It separately supports held-out full-page proposal evaluation. This is a technical integration milestone; scientific validation of actual manuscript recognition is **BLOCKED** pending independent reference annotations and physical locus mapping. No new remote job type, publication route, experiment thresholds, or interpretation of the manuscript. EXP-0038g remains NOT_MET; K-0001 remains deferred.

## Freeze a validation plan

Create a private JSON file outside the repository, with schema 1, scope `synthetic` or `manuscript`, an `inputs` object, and settings `device` (explicit `cpu` or `cuda`), `epochs` (1–50), `batch` (1–64), `seed` (uint32). Each input entry is `{ "path": "relative/path", "sha256": "actual SHA-256" }`. Paths are relative to the plan's directory and may not escape it. The twelve required inputs are:

| Input key | Required local artifact |
|---|---|
| pdf | Owner-held pinned PDF |
| review_csv | Guided crop center coordinates, not labels |
| groups | Verified PDF-page to physical-leaf/group map |
| manifest | Guided crop manifest from worker.py prepare, with original crops |
| script_left, script_right | Two separately prepared script/non-script review files |
| glyph_left, glyph_right | Two separately prepared glyph-box/label reviews |
| alphabet | Native `Eva-` or `STA1` inventory; all classes have agreed training and test support |
| split | Frozen nonoverlapping physical-leaf train/test groups |
| mapping | Frozen physical locus map for all held-out regions (format below) |
| transcription | Pinned matching native IVTFF file |

The optional thirteenth input `page_reference` is a separately annotated, exhaustive normalized reference-box file for exactly the held-out pages, per REGIONS.md. Choose the target unit (e.g. complete line) before annotation. Without it, full-page localization is explicitly blocked. Example mapping schema (illustrative, not actual manuscript ground truth):

```json
{
  "manifest_sha256": "<actual guided manifest SHA-256>",
  "source_sha256": "<actual transcription SHA-256>",
  "scheme": "Eva-",
  "regions": {
    "opaque-region-id": {
      "page": 6, "group": "f2", "locus": "f2r.1",
      "subtype": "@P0", "mapping_status": "confirmed",
      "scope": "complete_locus", "mapper": "reviewer-id"
    }
  }
}
```

Include all held-out regions, including non-script and unresolved regions. Do not use transcription similarity to establish the physical map. A confirmed complete locus is a reviewer assertion, not software-established truth. All data and labels must be fixed before running; do not expose test results while annotating training data, and do not reuse the test set for tuning. Curators must verify recto/verso, foldouts, reviewer independence, near duplicates, crop completeness and provenance. The worker detects exact crop duplication and exact normalized glyph duplication across splits, not all near duplicates. The full-page reference must be prepared independently, not generated from proposal windows.

## Run

```powershell
$P = '.\.venv\Scripts\python.exe'
& $P validation.py run C:\private\validation-plan.json C:\private\validation-run01
```

The destination must not exist. Input hashes, split, mapping, annotation agreement and page/group consistency are checked. The original guided crops are regenerated from the PDF and compared by exact manifest hash, which also binds each crop; rendering-library differences can prevent replay. Training uses the frozen training split only. The binary and glyph reference-box test scores are separate diagnostics. The glyph predictor then uses automatic projection on held-out pixels, not human test-box geometry or reference transcription to select glyphs. Gated comparison suppresses candidates if the binary model did not accept the region as script; ungated comparison is diagnostic only. Both use the same frozen eligible denominator (agreed script, confirmed complete mapping, supported reference notation) including failed gates, empty candidates, unknown glyphs and mismatches. Noneligible and unresolved rows are not promoted to exact matches; mapping exclusions are counted. No test threshold is optimized or scientific pass asserted. The optional localization track measures proposal precision/recall at fixed IoU thresholds on the held-out pages, separately from the guided crop chain. There is no automatic full-page proposal-to-locus assignment.

The run writes a plan snapshot, stage artifacts, input/code hashes, report, and completion receipt. On interruption or exception, the incomplete run remains without a completed receipt; inspect it rather than scoring the same held-out data repeatedly. All detailed artifacts remain private. No automatic upload, remote execution, or model promotion. This is a trusted local workflow, not a security boundary against concurrent edits by another local process.

## Real-source engineering probe (no annotations required)

```powershell
& $P validation.py probe C:\private\voynich.pdf d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c C:\private\probe-groups.json C:\private\probe01 --pages 6 176
```

`probe-groups.json`: `{ "6": "f2", "176": "f99" }`. PDF indices 6 and 176 carry the printed labels 2r and 99r in the pinned 214-page PDF. The probe checks the actual source hash and extracts overlapping 200-dpi multiscale ink candidates, then runs pixel projection. It does not identify writing, does not mask the PDF's printed headings/footers, and cannot establish distinct glyph counts. The aggregate `validation_probe_audit.json` records the actual owner-source run. No PDF, crops or transcription bytes are committed. The same counts were reproduced in separate runs, including the optional real-source test.

## Actual validation record — 2026-11-25

Linux CPU, Python 3.13.5, Xvfb, PyTorch 2.10.0+cpu, PyMuPDF 1.26.7, NumPy 2.3.5, Pillow 12.3.0. `python -m unittest discover -v` under Xvfb with `VOYNICH_TRANSCRIPT_DIR`, `EVA_REFERENCE_PDF`, `VOYNICH_MANUSCRIPT_PDF` pointing to the private original files: **50/50 tests passed** (44 prior, 6 new). The real PDF probe screened 12,782 windows, retained 5,467 overlapping candidates and generated 16,690 projection runs. No ground truth; no recognition accuracy. The synthetic full-chain fixture (four held-out regions; two eligible script loci) actually abstained on all four binary regions with three epochs, yielded one correct of four reference-box glyphs, five unknown of six projection candidates, zero of two exact gated loci and zero of two exact ungated loci. These outcomes verify accounting, not model quality; no tuning was done. Optional synthetic page-reference evaluation, tamper rejection, duplicate-locus rejection and split/mapping guards also passed. Windows, RTX/CUDA, live GitHub API, manuscript holdout accuracy, and actual independent labels remain unaccepted. The next concrete gate is creation and independent review of the real reference cohort and freeze of a physical-leaf holdout before scientific scoring.
