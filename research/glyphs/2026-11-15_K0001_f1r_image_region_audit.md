# K-0001 / f1r — Image-grounded stroke-region pilot, NOT a complete glyph inventory
Date: 2026-11-15. Owner S-tier / highest P0. Repository `DJCyberdog/voynich`.

## Single bounded research question

**Can the first original-image surface (f1r) be registered at repeatable pixel positions, including ornaments, uncertain marginal marks and writing regions not safely reducible to one EVA ASCII character?** This extends the merged ten-folio source/EVA census (PR #54, merge `c6c814904966002b3ea54f2501f08d1fd12b33b1`), without calling editorial characters physical glyphs.

**Prerequisite vs finding:** A valid complete original-glyph inventory would require separate image-mark detection, segment boundaries, grapheme equivalence judgments and independent annotation. This cycle deliberately solves only the **first, region-level** part.

## Source, coordinates, legal scope

- Owner-provided Beinecke MS408 PDF `voynich.pdf`, SHA-256 **d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c**. Local byte check PASS. **f1r is physical printed label on PDF page 4 (1-based)**; front matter excluded.
- Deterministic PDF page render: PyMuPDF 1.26.7, `get_pixmap(matrix=fitz.Matrix(2.5,2.5),alpha=False)`, RGB 1489×2105, raw RGB SHA-256 **cbd95103a136471df3a27933f881fa4de7664c1d1075c4930c5e9e24234daf10**. All boxes are `[x0,y0,x1,y1]` in this render, top-left origin. Version and checksum MUST match before reusing coordinate geometry.
- Source-level distinction: The owner-canonical working Yale IIIF snapshot **SRC-0007** remains canonical but was **not live Yale-authenticated**; the exact PDF-page-to-IIIF-canvas association is still **UNKNOWN**. The separate editorial witness is user-held ZL3b-n v3b, 13 May 2025, SHA-256 `bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc`. Transcript labels are not image pixels. Rights to redistribute original manuscript images or full IVTFF transcription were not asserted; **no image pixels or transcript lines were committed**.

## What was observed and registered

The source was inspected directly at overview resolution and in enlarged original-image crops. The following are physical *image region observations*, not semantics or verified glyph classes.

1. **28 approximate horizontal image text bands** were registered with raw-pixel coordinate bounds, provisionally indexed f1r.1–f1r.28. Placement used row-projection peaks plus visual inspection **with knowledge of the 28-line IVTFF witness**. Thus this is neither blind nor independent image-to-transcription line alignment; short lines and tall loops can cross these approximate bands.
2. **S01:** a red curved, V-like ornamental mark near the start of the second block, approx bbox [289,581,424,674]; **S02:** another red curved, V-like mark at the next block [285,807,371,867]. Both are image-visible (DOCUMENTED). The IVTFF witness uses editorial paragraph/control material at starts of f1r.7 and f1r.11 (e.g. `<%>` and rare markup `<!@252;>`, `<!@253;>`); neither the physical **number of graphemes** nor exact EVA mapping is established.
3. **S03:** elongated fine opening loop/flourish [302,1225,520,1320] by the fourth text block (provisional f1r.22). It might be one mark, several strokes or decoration. **S04:** mixed dark and red outer-right marks [1195,301,1318,622], potentially script, later ink, damage or staining; **S05:** faint upper marks [269,262,601,376] of unresolved origin. No mark silently discarded as nontext.
4. **33 region records** = 28 provisional text-line bands + 5 overlapping special regions, in `research/glyphs/2026-11-15_K0001_f1r_image_regions.jsonl`. **These are not 33 glyphs**, and overlapping regions must not be added as disjoint physical areas.
5. Exploratory automated local-darkness component sweep in script `research/glyphs/k0001_f1r_image_candidates.py`: `threshold = 14, 18, 22, 26` produces **2,227 / 1,980 / 1,826 / 1,742 connected dark-pixel component candidates**, respectively, within a broad f1r text-area centroid mask; minimum 5 pixels/maximum 5,000. These numbers are **NOT** glyph frequencies. Threshold choice changes the count by **485** (21.8% of the threshold-14 count), so even purely visual physical segmentation is method-sensitive. The f1r component ledger for threshold 18 is regenerable from the same original PDF by the committed script; **these component candidates include possible parchment texture, fused letters, disconnected strokes and side marks**. No automated candidate was independently adjudicated as one glyph.

## Exploratory positive/negative image controls (NOT language or scribal tests)

With fixed color predicate `HSV hue <= 9, saturation >= 75, value <= 200` on the owner-raster, two visually chosen red-ornament rectangles contain 1,713 / 12,015 and 470 / 4,250 positive pixels. Equal-area visually chosen blank-parchment rectangles each yield **0** red-positive pixels. This checks **local color discrimination**, not glyph identity; red controls were chosen after visual inspection and must not be represented as blinded or preregistered proof. The color result alone cannot distinguish script, decoration or an added hand.

### Falsification structure

- **Candidate prediction needing future preregistration:** a single image glyph code and stable segmentation would yield consistent independent classifications on matched duplicate crops and on independent imaging of unseen physical leaves. Define missed-mark recall and agreement thresholds *before* exposing labels.
- **Strongest alternative:** ink strokes belong to joining/ligature conventions, context-dependent allographs, decorative paragraph marks, corrections or late additions; alternatively parchment damage makes some source-visible pixels look like writing.
- **Actual attempted check:** compare automatically extracted dark connected components across four thresholds, and compare red-vs-blank controls. Result: detected dark regions vary materially with threshold; two red initials are reproducibly separable by color locally, but **there is no validated identity partition**, and no script/language/cipher/nonlanguage model can yet be preferred.
- **Null model:** spatially matched bare parchment regions for color detector artifact background; this is NOT a statistical null for the Voynich script. **Positive controls:** pre-observed red strokes; **negative:** matched blank paper. **Holdout:** physical leaves f11 onward (not used) plus independent image witness. **NOT RUN:** blinded multi-annotator crop agreement, second image source, independent EVA re-alignment, actual decipherment test. Current trial is exploratory and not pre-registered; cannot claim a passed confirmatory gate.

## Evidentiary classes and research state

- **VERIFIED (local scope):** original PDF SHA; rendered pixel geometry/hash; script-recomputed component count per frozen thresholds; exact red-pixel counts and blank controls, conditional on masks and image.
- **DOCUMENTED (image scope):** two red ornament-like marks, thin opening flourish, right-margin dark/color marks, faint upper marks; coordinate regions.
- **INFERRED:** approximate mapping of 28 image line bands to 28 editorial line IDs. It was informed by knowing the text count; NOT blind.
- **UNKNOWN:** number of true physical glyph occurrences on f1r, glyph classes, allograph/ligature/modifier distinctions, writing hand(s), whether decorations are linguistic signs, direction or function of marginalia, exact EVA-to-stroke correspondence, physical folio-to-IIIF canvas association.
- **ACTIVE:** K-0001. This **does not complete f1r**. 0/1 f1r sides fully segmented/independently validated; **0/20** first-ten-folio sides fully segmented; 0 confirmed grapheme classes or EVA mappings; decipherment gates **0/5**. Other unchanged work-package denominators: 20/20 target PDF folio sides indexed, 213/213 owner-canonical canvas IDs inventoried (not independently validated folio mappings), and 3/40 narrowly concluded audit claims. No overall decipherment percentage.

## Next exact step

**Manual region-to-ink-stroke adjudication on f1r**, beginning with S01/S02/S03 and source-visible text bands 1–6: independently record every uncertain mark and *stroke cluster* with pixel boxes, class alternatives, adjacent context and reviewer disagreement, never force one EMA/EVA symbol per component. Acquire a second independently licensed image witness and inspect blind duplicate crops before elevating class identity; reserve unseen physical leaves for heldout. Only then expand to f1v and further pages.

No new HYP, EXP, or language/semantic claim was registered. Owner-authorized PR-only integration; hourly automation not changed. Prevent duplicate treatment of O-01 correction traces and earlier K-0001 VY001.
