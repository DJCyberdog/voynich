# RC2-02d — non-destructive component and artifact evidence

Status: LOCAL ENGINEERING PASS for evidence extraction, PARTIAL for the package. Physical leaf contour extraction, validated artifact rejection, script localization and separation of Voynichese from later handwriting remain open. No production activation. No pixels or private annotations deleted.

## Implementation
Native image coordinates, half-open boxes, deterministic 8-connected run labeling on the union of the six RC2-02c binary hypotheses. Each union pixel retains its component ID; records include area, mean method votes, mean signed grayscale residual relative to a Gaussian background (radius 16), and aligned neighbor count. Fixed exploratory flags: tiny area <=4 px; elongated long side >=24 px and >=8 times short side; near image edge <=8 px; touches window edge; broad low contrast area >=64 px and mean residual <8; mean agreement strictly below half; line context >=2 eligible aligned neighbors; isolated means no such neighbor. Exact implementation defines the neighbor geometry. A native image boundary is not a physical leaf boundary. The label UNRESOLVED is retained for every component; no learned or calibrated script/ink classifier exists here. Fixed pixel thresholds are provisional, not scale-calibrated. IDs are local to the analyzed mask, not globally stable glyph identities.

## Verified local tests
Exact module blob cdc90ec3e6aafdc07ecf78c7c8d43d0495a379df and test blob 10c750b6c38346830a59ea5184a53a9928c9d03c. Five unit tests PASS. 300 seeded random masks agree with independent SciPy 8-connectivity partitions. Four full native images (PDF pages 4, 50, 127, 214) match the independent partition and conserve every union pixel: 10,657 / 5,746 / 4,152 / 11,624 components; total 32,179 components and 542,159 union pixels. These counts are not glyphs. The four full-image tests are not a full-manuscript run. The previous commit 1e2eb40 completed all three GitHub workflows successfully; current change requires its own hosted checks.

## Private development audit
The audit script reproduces the six ensemble formulas separately (not a direct call to vrs_binarize.hypotheses), with native context margins of 64 px, and rechecks source SHA-256 and canonical review manifest hash/ID set. Local execution with Python 3.13, NumPy 2.3.5, Pillow 12.3.0, PyMuPDF 1.26.7 and SciPy 1.17.0. Run from worker with PYTHONPATH set to worker, python experiments/audit_rc2_artifacts.py PRIVATE_PDF PRIVATE_REVIEW_JSON, without -O. Output audit-result.json is local and includes case-level example IDs; do not publish. No private files or raw labels are in the repository. Audit script SHA 326bea775ef2ad1663f1a55f3dd817d9fd78c369. 180 context windows across 80 pages (160 candidates plus 20 random windows; 20 wrapper cases excluded). 43,992 component occurrences across overlapping windows, not unique manuscript-wide objects. Component membership and foreground area conserved in every window. Observations below are counts of candidate envelopes intersecting one or more flagged components, not independently annotated component labels.

| Feature | Handwriting (66) | Non-script/blank (92) |
|---|---:|---:|
| Any union foreground | 66 | 82 |
| Tiny present | 35 | 64 |
| Only tiny components intersect target | 0 | 19 |
| Elongated | 0 | 9 |
| Near image edge | 0 | 4 |
| Touches window edge | 0 | 30 |
| Broad low contrast | 0 | 1 |
| Low method agreement | 38 | 72 |
| Line context hint | 66 | 63 |
| Isolated in window | 5 | 47 |

Mixed and uncertain candidate envelopes omitted from these denominators. Random controls: 8 handwriting / 12 non-script or blank; all have union foreground, 8 / 8 have line context hint respectively; 8 / 11 have tiny components, 0 / 1 have only tiny components. Flags overlap. The previously discussed speck and shadow example have no union pixels in their native envelopes; the leaf-edge example still intersects 31 components including elongated and tiny flags; the non-Voynich handwriting example remains UNRESOLVED. This is not proof of ink removal accuracy or script identity. Context thresholds can change in whole-page runs. No independent holdout, pixel ground truth, physical leaf contour segmentation or handwriting-script taxonomy has been qualified. Do not infer population prevalence, auto-delete, or mark the scientific gate passed. Independent contour/skeleton experiments can proceed with the preserved mask alternatives; RC2-02g/h must reconcile artifact/script localization before production acceptance.
