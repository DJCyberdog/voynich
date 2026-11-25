# v0.5.0 — local glyph recognition baseline

This local-only development milestone adds glyph candidate segmentation, a Tk box/label editor, a trainable prototype classifier and held-out evaluation. Existing worker, region detector, queue and GitHub bridge are unchanged. No new remote job action, upload route or experiment result. The glyph module is deliberately separate from K-0001 (owner-deferred full inventory validation).

## Input and annotation

Use a nonempty, hash-verified crop manifest from the existing worker or region module. Select single-line writing regions, not whole pages or mixed text/drawings. The vertical ink projection proposes one rectangle per contiguous run of occupied columns (grayscale threshold 160). It may split a disconnected glyph or merge connected/touching glyphs and does not identify ligatures, allographs or stroke boundaries. It is a baseline, not a validated glyph detector.

Create a local `alphabet.json` with a named, versioned convention and 2–256 distinct classes. Example **synthetic-only** inventory: `{"convention":"synthetic-only-v1","labels":["X","Y"]}`. Do not use that inventory on the manuscript. EVA or STA1 requires an explicitly curated class list and unit definition; EVA text tokens are not automatically physical glyphs. The worker never silently maps one convention into another.

From the worker directory, using the already configured environment:

```powershell
$P = '.\.venv\Scripts\python.exe'
& $P glyph_review.py C:\private\dataset\manifest.json C:\private\alphabet.json C:\private\review-a.json reviewer_a
& $P glyph_review.py C:\private\dataset\manifest.json C:\private\alphabet.json C:\private\review-b.json reviewer_b
```

Each reviewer works separately without the other's labels or model predictions. Select a box in the list and drag to replace it, or select New box and drag to add one. Apply label assigns a class; edited geometry resets the label to `unknown`. Delete box removes a candidate. Accept line, Reject and Uncertain record the region state. Empty or horizontally overlapping boxes cannot be accepted as single lines; retain uncertainty rather than forcing boundaries. Edits save locally and reset the line to unreviewed until explicitly accepted. Reopening resumes at the first unreviewed crop. Alternatively use `glyphs.py propose MANIFEST OUTPUT REVIEWER ALPHABET` to produce a blank JSON review template; boxes are integer crop-local coordinates `[x0,y0,x1,y1]`, upper bounds exclusive.

Every review is pinned to the exact crop manifest and alphabet file. The training loader requires two distinct reviewer IDs and exact agreement on complete accepted rows (including box list order); this deliberately strict engineering rule may exclude many usable regions and is not evidence of human independence. All rejected/disputed regions and agreed unknown labels are counted separately. No glyph interpretation is manufactured from a projection.

## Train and evaluate

Freeze the physical-leaf split before scoring, using the existing `split.json` with train/test group arrays. All groups must be covered, no shared physical group or page, and every inventory class needs agreed support in both partitions. Exact normalized image duplicates across splits are rejected. Curators must still eliminate near-duplicates and repeated overlapping crops within a split, verify physical leaf grouping, and preserve genuinely unexposed holdouts. A small supported inventory is not a claim of complete manuscript coverage.

```powershell
& $P glyphs.py train C:\private\dataset\manifest.json C:\private\review-a.json C:\private\review-b.json C:\private\alphabet.json C:\private\split.json C:\private\glyph-run01 --device cpu
```

The baseline pads grayscale glyph crops to 32x32, averages each class on train data only and scores mean squared distance to prototypes via PyTorch (CPU or CUDA). A prediction is accepted only if nearest distance <= 0.12 and second-best margin >= 0.005. These fixed engineering defaults are not calibrated probabilities or scientific thresholds. Rejections are `unknown`, count against held-out accuracy, and contribute to coverage. The confusion matrix includes unknown predictions. `glyph_model.json` and `glyph_report.json` contain private model/provenance and per-glyph output. They are not shared automatically. Existing output is never overwritten. This small reference model is not a CNN or a trained Voynich recognizer.

## Predict on other reviewed regions

```powershell
& $P glyphs.py predict C:\private\new\manifest.json C:\private\new-review.json C:\private\alphabet.json C:\private\glyph-run01\glyph_model.json C:\private\glyph-run01\glyph_report.json C:\private\predictions.json --device cuda
```

Prediction uses only reviewed single-line boxes (not their labels), verifies the model hash and convention, and returns per-glyph candidate classes, distances and margins, or unknown. Predictions are not independent evidence. Reading-order and transcription alignment (v0.6), touching/compound glyph disambiguation, real-data open-set validation, calibration and scientific end-to-end acceptance remain open. No raw images, transcriptions, review files or model weights are to be committed. No GPU execution has been verified here.

## Validation — 2026-11-25

Linux Python 3.13.5, PyTorch 2.10.0+cpu, NumPy 2.3.5, Pillow 12.3.0, PyMuPDF 1.26.7, Xvfb: `xvfb-run -a python -m unittest -v test_worker test_pipeline test_gui test_bridge test_regions test_glyphs test_glyph_review`. 29 tests (22 prior, 6 glyph core, 1 GUI); synthetic controls only. New tests cover blank/edge proposals, inventory binding, malformed annotations, group separation, disagreement and unknown accounting, exact normalized duplicate refusal, prototype training/prediction, abstention and model tampering, actual GUI box replacement/add/delete, label/save/reopen and reviewer guard. The synthetic test has two toy classes and four held-out instances; its 4/4 classification is solely a smoke test. No Windows, RTX, real GitHub API, manuscript accuracy or scientific decipherment acceptance. EXP-0038g remains NOT_MET (59/74); K-0001 remains deferred.
