# RC2-02d–f completion audit — 2026-11-27

## Disposition
The remaining engineering experiments were executed; no new scientific acceptance criterion was waived. RC2-02d remains NOT_MET for reliable script/material separation and BLOCKED for independent physical-leaf and script-type validation. RC2-02e exact polygon and bounded quadratic-curve baseline EXPERIMENTAL TECH_PASS; RC2-02f guarded skeleton/medial-axis and width comparison EXPERIMENTAL TECH_PASS. Production integration, dependency qualification where needed, scientific validation and release acceptance remain open; do not interpret these dispositions as closure of RC2-02 overall, nor as automatic authorization to proceed past a dependent gate. Existing 13 top-level packages, private source, labels, and final cumulative ZIP policy unchanged. The prior commit 072774d completed all three hosted workflows successfully.

## Reproducible experimental implementation
- experiments/vrs_geometry.py blob 97b9defaf112d4be1b2858e8b1c266b077943b83
- experiments/test_vrs_geometry.py blob 58b3b8e39aa9e37a24618dbe691d8f15680d481f
- experiments/audit_geometry.py blob 156ac04af9a22f3ccfbd9bcdfb6c9fdf718b7a86

Experimental code only; not added to the managed portable runtime. Existing vrs_vectors and vrs_artifacts are unchanged. The local test environment uses NumPy 2.3.5, Pillow 12.3.0, PyMuPDF 1.26.7, SciPy 1.17.0, scikit-image 0.26.0, CairoSVG 2.8.2. The installed distribution metadata identifies SciPy and scikit-image as BSD-licensed (scikit-image BSD-3-Clause), CairoSVG LGPL-3.0-or-later. This is an initial dependency check, not a full transitive license/wheel/Windows portability audit. Exact contours, rounding, reduction and identity only use existing dependencies. Optional material/medial experiments need SciPy/scikit-image; CairoSVG only tests. No additional managed-runtime installs or changes to portable requirements. From worker, with worker and experiments on PYTHONPATH and optional experiment dependencies installed in an isolated environment, run python experiments/test_vrs_geometry.py; run python experiments/audit_geometry.py PRIVATE_PDF PRIVATE_REVIEW_JSON windows; then mode full 4 50 127 214; and mode leaves 2 3 4 20 50 75 100 127 159 180 200 214. Run without -O. Outputs are private local JSON, never published automatically. Source and canonical review manifest digests and all 200 IDs rechecked. Same 180 native windows across 80 pages; 20 modern wrapper controls excluded. Frozen six-method ensemble strict majority. This is a development set, not independent ground truth.

## d — material contour and script zones
Bright-material silhouette hypotheses use median filter 5, grayscale thresholds 30/50/70, largest 8-connected foreground region, hole filling. Their intersection and disagreement are retained; no physical folio identity inferred. All 12 tested full digital images have nonempty core: 16,923,555 core pixels, 62,705 disagreement pixels, 18,595,800 total image pixels. This is agreement, not accuracy. It can include adjoining leaves and miss dark material; no physical boundary labels. The script-zone proposal groups aligned non-tiny, non-elongated components with line-context flags. At least three components form a candidate zone, all UNRESOLVED. No automatic removal or Voynichese claim.

| Candidate class | N | Envelope intersects proposed zone |
|---|---:|---:|
| Handwriting | 66 | 64 |
| Non-script/blank | 92 | 52 |
| Random handwriting | 8 | 7 |
| Random non-script/blank | 12 | 7 |

Mixed and uncertain cases each overlap a zone; excluded from primary denominators. These observations are exploratory overlap, not script segmentation accuracy. The heuristic is NOT_MET as a reliable filter; it misses two handwriting envelopes and includes 52 negative envelopes. No authenticated independent physical contour/annotation type labels in the supplied review, which also includes one suspected non-Voynich handwritten case. Do not infer language/script from geometry or relabel existing handwriting as Voynichese. Independent source-backed contour and script-type reference data, improved methods and a disjoint test are required; no user review demand introduced here.

## e — curve/point reduction and provenance
Quadratic Bezier corner rounding with radius 0.22 native px; closed Ramer-Douglas-Peucker reduction at tolerance 0.75 px before rounding as an explicitly non-authoritative alternative. External renderer CairoSVG alpha >=128, native-size pixel comparison on every fifth window in deterministic page/manifest order (36 masks). Independent component count and Euler characteristic compared. Exact integer-grid SVG remains authoritative.

| Variant | Input contour vertices before rounding | Pixel discrepancies | Identical masks | Component/hole counts equal |
|---|---:|---:|---:|---:|
| Exact | 51130 | 0 | 36/36 | 36/36 |
| Rounded | 51130 | 0 | 36/36 | 36/36 |
| Reduced + rounded | 32428 | 3894 | 4/36 | 6/36 |

Reduced variant rejected as a scientific default; rounded variant remains a derived view. These are pre-curve vertices, not the final SVG control-point count. Pixel identity at native resolution does not imply geometry identity at higher render resolutions or all renderers. All 180 source-bound vector record IDs distinct; exact and curve SVG SHA-256, source PDF hash, page number, decoded RGB page hash, native crop origin/size, affine to PDF points, mask method and bytes hash included in canonical record ID. Existing mask-to-contour internal roundtrip 180/180 additionally checked. Records generated in memory; no durable storage/runtime integration claimed. Existing 540-mask exact baseline remains intact.

## f — medial axis, width and full-page controls
Deterministic scikit-image medial_axis (rng=0), exact Euclidean distance transform on zero-padded mask, twice nearest background-center distance as local digital diameter proxy (not physically calibrated pen thickness). Guard each component against connectivity/Euler changes and restore original on failure; explicit fallback list. Coordinate grouping once, no per-component full-image search. Compared with unchanged guarded Zhang-Suen on 180 majority masks. Independent SciPy components and scikit-image Euler checks passed all 180 for both methods; 80 additional seeded random masks (seed 271126, 17x23, density uniform .03–.97) passed for medial with 48 fallbacks. Five local unit tests passed. On context windows Zhang-Suen 146123 skeleton pixels, 124 fallback components, 4.38 s; medial 209267 pixels, 267 fallbacks, 9.38 s. Input 301197 foreground pixels. Neither count is glyph count; large fallback regions are not thin skeletons. Medial has not displaced Zhang-Suen. Existing 540-mask union/majority/intersection Zhang-Suen checks retained.

Full-page majority-mask checks on four separate complete native digital images now completed: exact internal contour roundtrip, both skeleton subsets, independent component and Euler equality for each. Full run 16.83 s including mask generation and checks. Local Linux timing, not owner's CPU/CUDA target.

| PDF page | Input pixels | Zhang-Suen s | Medial s | Zhang-Suen fallbacks | Medial fallbacks |
|---|---:|---:|---:|---:|---:|
| 4 | 113915 | 1.76 | 1.94 | 111 | 26 |
| 50 | 104697 | 1.31 | 1.41 | 71 | 42 |
| 127 | 66803 | .74 | .86 | 36 | 9 |
| 214 | 108327 | 1.37 | 1.50 | 138 | 3 |

Performance is measured on four images, not full corpus, not native Windows, and no claim of a production throughput improvement. Width is a digital mask-dependent proxy. Full manuscript, backend/target performance and integration remain their existing gates. No private source, individual labels, SVGs or local output files committed.
