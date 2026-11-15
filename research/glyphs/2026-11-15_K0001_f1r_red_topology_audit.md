# K-0001 / INV-003: f1r red paragraph marks — image topology is not glyph identity

**Date:** 2026-11-15. **Priority:** Owner S-tier, highest P0. **Scope:** One bounded, falsification-oriented image/source audit of *already* documented f1r S01/S02, not a new glyph class or separate artificial null study.

## Question

**Does the fixed, previously integrated red-ink detector assign a stable single image component to each of the two visually similar red paragraph-initial marks, S01 and S02?** This is a prerequisite for interpreting the automated segmentation pipeline as glyph occurrences. If disconnected pixel patches are silently counted as separate signs, a putative “new alphabet” could be an image-processing artifact.

**Prior work dedup:** f1r 28 provisional line bands and S01/S02 regions, plus two red-vs-blank color controls, are already integrated via PR #55 / D-0221. This report is limited to the **new connected-component and closing-kernel topology** and a two-line check against distinct IVTFF editorial markers; it does not re-register these as new source objects or claims.

## Input/provenance layers

- **Image witness:** user-supplied 214-page Yale Beinecke MS 408 PDF, SHA-256 `d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c`; f1r = PDF page 4. Existing verified render PyMuPDF 1.26.7, zoom 2.5, RGB 1489×2105, raw pixel SHA-256 `cbd95103a136471df3a27933f881fa4de7664c1d1075c4930c5e9e24234daf10`. Top-left `xyxy` raster coordinates.
- **Second layer (editor, not image):** owner-provided `ZL3b-n.txt`, v3b 2025-05-13, SHA-256 `bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc`. Lines f1r.7 and f1r.11 contain distinct tags `<!@252;>` and `<!@253;>` before the ordinary EVA text (in each case `<%>` appears too). They are **different source string markers**, not two independently verified phonetic letters or even necessarily the editor's glyph-class IDs. Their exact editorial semantics require convention/source review.
- **IIIF policy:** SRC-0007 is the user-designated canonical working snapshot for canvas/folio mapping; *no separate live Yale authentication* was attempted. This PDF and transcription are not by themselves an independently verified PDF↔IIIF canvas mapping.
- **Rights:** original PDF pixels and full IVTFF lines retained locally only. PR commits **derived metadata, method and results**, not source scans/crops, original transcription or font glyph files.

## Frozen prior region choices and exploratory procedure

Use the existing PR #55 ROIs, not new post-result hand-picked examples:
- S01 `[289,581,424,674]` (near f1r.7);
- S02 `[285,807,371,867]` (near f1r.11);
- equal-area previously selected blank-parchment controls `[380,1660,515,1749]` and `[1000,1680,1085,1730]`.

The same OpenCV RGB→HSV color rule previously used to separate red from parchment is **H≤9, S≥75, V≤200** (hue is the OpenCV integer scale). New here: run 8-connected component labeling on the mask and retain regions of area **at least four pixels**; then repeat after morphological closing with elliptical kernel sizes 1 (none), 3, 5, 7, 9, 11, 15 pixels. Kernel sweep is **exploratory/post hoc**, not a preregistered confirmatory test. This mask is a red-pigment detector, NOT a script classifier.

### Observed result

| ROI | Red pixels with unmodified rule | Components ≥4 px, no closing | Components after 5 px closing | After 15 px closing |
| --- | ---: | ---: | ---: | ---: |
| S01, red first block mark | **1,713** | **1** (area 1713) | 1 | 1 |
| S02, red next block mark | **470** | **4** (areas 254, 125, 83, 8) | 2 | 1 |
| Blank control A | **0** | 0 | 0 | 0 |
| Blank control B | **0** | 0 | 0 | 0 |

**VERIFIED, scoped local image computation:** S02's red segmentation fragments into **four** disconnected components under the fixed detector; artificially joining at 15 px reduces it to **one**, without adding evidence of a new physical letter. S01 stays one under all tested kernels. A separate SciPy 8-neighbor component implementation reproduced the raw 1-versus-4 counts and per-component areas. Both matched local source hashes. The result is reproducible by `research/glyphs/k0001_f1r_red_topology.py`; derived details are in `2026-11-15_K0001_f1r_red_topology_results.json`.

**DOCUMENTED image:** in enlarged PDF crops, S01 and S02 are red V-/fork-like paragraph marks with differing widths, ink density and lower extensions. However direct visual similarity alone is insufficient to conclude they are one or two graphemes, a letter, decoration or later modification.

**Interpretation:** the assumption `color component count = physical glyph count` fails as an inference strategy on this already-selected source pair: one red candidate can yield four masks, two masks, or a fused mask according to investigator-controlled closing. This demonstrates **segmentation parameter-dependence**. It does **not** prove that S02 consists of one historical pen stroke, nor falsify the standard EVA system or a natural-language/cipher/non-language/hybrid reading.

## Falsification protocol

- **Weak technical model under test:** a stable one-component-per-sign pigment detector can read candidate red initials independently of preprocessing and editorial tags. **Outcome: CONTRADICTED for this technical model on S02** (at fixed source, 4→2→1 under closing).
- **Strongest counterexplanation:** pigment attenuation, thin disconnected strokes, partial original ink loss, decoration, overlapping elements, print-scanner artifacts or disconnected historic pen strokes can account for multi-component masks without distinct graphemes. Contextual allography remains viable.
- **Positive controls:** S01/S02 manually preselected visible red marks; pigment mask captures them. **Negative controls:** previously selected blank parchment ROIs both return zero, including after closing. These are *not* blinded or prospectively random.
- **Null/heldout:** no valid null model or genuinely unused held-out imaging witness for **grapheme identity** in this cycle. A matched-blank null tests only color discrimination; f11+ physical leaves remain reserved for future confirmatory predictions. No p-value or independent cross-witness claim.
- **Preregister before future identity testing:** fix true/false crop IDs, physical-leaf separation, source-image versions/rights, normalizations, duplicate-crop and comparable known/allograph controls, second annotator, acceptance threshold and untouched leaf holdout. Distinguish red ink, damaged text, ornamental marks and main running script. In particular, independent annotation must be blind to the `@252`/`@253` editorial labels.

## Results and open gates

**K-0001 remains ACTIVE / NOT_DONE.** First ten folios: **20/20** source-PDF sides caption-indexed, **0/20** sides completely segmented and independently adjudicated. f1r **28/28 provisional line bands** mapped only as regions, **0/28** completely adjudicated. **0 independently validated grapheme classes**, **0 verified EVA-to-glyph mappings**, **0/5** decipherment criteria. Existing counts: **213/213** snapshot canvas IDs inventoried (not a validated canvas-folio concordance), **3/40** narrowly adjudicated owner A/W audit claims. No total decipherment probability.

**No new decipherment/language/semantics/author attribution.** Technical mask instability is **VERIFIED**; identity of physical signs is **UNKNOWN**; operational next step remains **ACTIVE**. Follow-up: independently adjudicate candidate strokes at S01/S02 and at f1r line bands 1–6 with second imaging witness and blind annotations; then apply the same documented procedure to f1v. Do not create a second EVA-only evidence loop.
