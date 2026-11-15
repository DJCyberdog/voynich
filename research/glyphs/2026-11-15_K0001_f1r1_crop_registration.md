# K-0001 / INV-004 — f1r.1 uncertain-mark crop registration to pinned original raster

**Date:** 2026-11-15. **Research phase:** exploratory, nonblind. **Priority:** S-tier/P0 highest. **One bounded question:** Can a pre-existing magnified image crop of the ambiguous first-line cluster be located unambiguously in the byte-pinned f1r original raster, without using EVA labels as a guide? This is a source-coordinate registration, **not** a new glyph identification or proof that an editorial alternative is correct.

## Delta-first and sources

Starting integrated `main` `3c165fdd273d87e03e694555db8d92ab8b7ed7da`; no open PRs at the start of this cycle. Read all six governance/policy documents, README, all eight memory files and integrated 40-claims queue/protocol. Previous INV-002 already has 28 approximate line-region bands; INV-003 covered red marks S01/S02. **This test does not repeat those masks or create a new glyph-class ID.**

Original working raster: owner-held Beinecke MS408 PDF f1r, PDF page 4, original PDF SHA-256 `d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c`, previously documented PyMuPDF 2.5x RGB raster **1489×2105**, raw RGB SHA-256 `cbd95103a136471df3a27933f881fa4de7664c1d1075c4930c5e9e24234daf10`. This cycle independently rehashed the available raster PNG's decoded RGB bytes and matched that raster SHA. The available derived crops are `line1.png`, `line1left.png`, `ambigf1r1.png` and `line2.png`; their byte origins are local working copies, **not an independent imaging witness**. Their source pixel contents are not committed or redistributed. Canonical IIIF working snapshot SRC-0007 remains owner-designated; **no independent live Yale authentication**, and no exact PDF-to-IIIF canvas proof.

## Exploratory image-only registration

OpenCV grayscale template matching, `TM_CCOEFF_NORMED`, entire 1489×2105 raster, resize derived crops to the *specified* relative scales below. Coordinates refer to the raster top-left origin, half-open `[x0,y0,x1,y1]`. Matching was conducted without using EVA text to place the crop. Reported maxima are descriptive template correlations, **not calibrated statistical confidence**. Scale choices were inspected during exploratory matching and are **not preregistered**.

| Existing local crop | Scale | Match upper-left | Matched raster rectangle | Normalized correlation | Horizontal-flip negative-control max |
| --- | ---: | --- | --- | ---: | ---: |
| `line1.png` | 0.5 | (280,342) | [280,342,1260,414] | 0.984969 | 0.277698 |
| `line1left.png` | 0.5 | (280,342) | [280,342,750,424] | 0.998887 | 0.216689 |
| `ambigf1r1.png` | 1/3 | (760,337) | **[760,337,1050,414]** | **0.999417** | **0.290702** |
| `line2.png` | 0.5 | (280,397) | [280,397,1280,485] | 0.996582 | 0.220881 |

The last crop is a **positive registration sanity check** on the adjacent line, not a held-out manuscript witness. Horizontal flips are image-template negatives; they do not test grapheme identity. The image-region rectangles **overlap in y** (the line1 crop and line2 crop share y397–414). This confirms that a rigid, non-overlapping horizontal-band assignment could misattribute tall ascenders or descenders, and motivates per-mark polygons and explicit overlap flags. It does **not** establish that the actual ink strokes in the overlap belong to either line.

## Interpretation and falsification boundary

**DOCUMENTED/VERIFIED (local image scope):** the owner-raster decoded RGB SHA matches the frozen source-raster checksum; image-only template matching locates the existing ambiguous cluster crop at [760,337,1050,414] with a very high descriptive match, while its flipped template has a much lower match. The crop is now registered to a reproducible original-raster region rather than an unlocated illustration. The same method places both neighboring line crops and reveals a 17-pixel vertical intersection of their crop rectangles.

**Strongest alternative:** the high correlation is expected because the crops derive from this same raster and their sizes were inspected; it cannot independently verify the physical mark's identity, EVA alternative, number of graphemes or manuscript provenance. A source-crop duplicate is *not* a second witness. The observed overlap may simply reflect loose crop boundaries, not shared or ambiguous writing strokes.

**Attempted falsification:** prediction that a derived crop would align spatially with the raster substantially better than a horizontally flipped crop. Observed high real-template correlations versus lower flipped maxima; a narrow **registration** check passes. This is **not** a confirmatory identity test, as no predeclared scale-selection rule, probabilistic null, independent annotator or unseen manuscript leaf was used.

**Editorial layer:** previous cycle mentioned f1r.1 alternative `[cth:oto]` and `@254`; these remain **CLAIMED from prior transcript inspection**, not independently verified in this cycle against byte-pinned IVTFF content or matched to particular pixels. No EVA-to-stroke correspondence, ligature, diacritic, scribe or phonetic interpretation is assigned. Never treat `@254` as a glyph without its original editor-convention documentation.

**Hypothesis status:** K-0001 **ACTIVE**. Physical grapheme identities and EVA adequacy **UNKNOWN**. No language, cipher, artificial-text or hybrid model is privileged; all are unaffected by this narrow geometric result. No new or retired linguistic hypotheses, no decipherment.

## Next test and gates

The new rectangle enables a **future preregistered** manual segmentation test: independent annotators mark all ink strokes in [760,337,1050,414] and adjacent text context, using source-image pixels without editorial labels, distinguishing connected marks, separate strokes, damage and possible diacritics. Predeclare image versions, polygon protocol, split/join disagreements, a genuine second rights-cleared witness, positive controls (known continuous strokes), negative controls (damage/parchment), untouched folio-root holdouts f11+, and an agreement/rejection threshold. Only then expose competing EVA/editorial interpretations. No pseudo-blind validation from derived duplicate crops.

**Progress denominators unchanged:** first ten sides **20/20** indexed but **0/20** fully glyph-segmented/adjudicated; f1r **28/28** tentative line bands, **0/28** independently glyph-adjudicated; **0** verified grapheme classes, **0** EVA mappings, **0/5** decipherment gates; snapshot **213/213** canvas IDs inventoried only, **3/40** scoped claims audited. This new image registration is one **coordinate-level prerequisite**, not a new fully analyzed line or decipherment percentage. Source rights remain unverified for redistribution, so only derived metadata is committed.
