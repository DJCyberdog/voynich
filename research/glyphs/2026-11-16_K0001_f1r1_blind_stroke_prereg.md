# K-0001 / INV-005 — prospective, EVA-blind f1r.1 stroke-boundary test contract

**Date:** 2026-11-16. **Phase:** PREREGISTERED PROTOCOL ONLY; NO NEW INK-STROKE TEST RUN. **Scope:** one bounded methodological research question, not an independent witness or a new physical glyph class. **Status:** K-0001 ACTIVE; protocol READY_FOR_INDEPENDENT_ANNOTATION, execution BLOCKED on an independent second annotator and a separately licensed image witness for cross-source confirmation.

## Delta-first and duplication check

Integrated main before this protocol: `d43b5f412bb685d0c03c8b281f207c32e4840b21`, zero open PRs at inspection. Read README, all six mandatory governance/method/transcription documents, eight memory files, 40-claim queue and protocol, and prior K-0001 INV-002/003/004 reports. INV-004 localized the crop; INV-003 falsified the inference from pixel components to glyphs. **Neither specifies a frozen, executable, EVA-blind annotation adjudication protocol**. This document supplies only that missing prospective test contract. No source-image or IVTFF bytes are committed.

## Single question and competing predictions

**Question:** For the ambiguous cluster in physical f1r.1, can two independent readers, given only original-raster pixels and adjacent visual context, reproduce the same *visible ink-stroke cluster boundaries* before seeing any EVA or editorial labels?

- **H1 (reproducible visual boundaries):** two annotators independently produce a one-to-one spatial matching of stroke clusters with high agreement on the preselected region. This would support only a *visual segmentation protocol*, not a grapheme inventory, EVA adequacy, language or decipherment.
- **H0 / strongest alternative (ambiguous segmentation):** equally plausible splits/joins, damage, ligatures, retouching or background texture lead to systematic unmatched clusters or low agreement; high agreement can also arise from shared training or seeing EVA, so annotators must be separated and blinded.
- **Other explanatory families:** natural language, cipher, nonlanguage, hybrid and later-added writing can all generate visible strokes. This experiment does not distinguish them; no language/semantic inference is licensed.

## Immutable source and region

- Owner-held Yale Beinecke MS 408 PDF, f1r printed label, page 4 (1-based); PDF SHA-256 `d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c`.
- Source raster PyMuPDF 1.26.7 zoom 2.5, RGB 1489×2105, raw RGB SHA-256 `cbd95103a136471df3a27933f881fa4de7664c1d1075c4930c5e9e24234daf10`; top-left origin; half-open integer xyxy.
- **Fixed test ROI:** `[760,337,1050,414]`. **Context only, not scored:** line1 `[280,342,1260,414]`, line2 `[280,397,1280,485]`. Existing crop intersection is 17 px, not proof of actual cross-line strokes. Annotators can view context after the isolated test ROI, but must log when context was revealed.
- **Editorial witness sealed until scoring:** owner-held ZL3b-n v3b, 2025-05-13, SHA-256 `bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc`; earlier claimed alternative `[cth:oto]` and editor marker `@254` must be independently source-checked before use. Editorial markup is not a physical glyph.
- SRC-0007 is the owner-designated SHA-256-pinned canonical IIIF working manifest, not independently live-Yale authenticated; this PDF-to-IIIF canvas correspondence is not yet independently validated. No routine 403 retry.

## Frozen annotation rules (before either blind reader begins)

1. Give annotator A and annotator B the **same byte-verified source raster ROI**, without folio name, EVA, IVTFF, source article, prior mask topology, or the other's annotations. Independent means two distinct human annotators, not two runs of one program or two personas from one model. Record reviewer pseudonym, timestamp, image SHA, pixel dimensions, any enhancement, and whether they had prior Voynich exposure. No coaching toward one candidate glyph count.
2. Each annotator records every visually plausible **ink-bearing cluster** as a closed polygon in global raster pixel coordinates, plus `region_id`, `polygon_xy`, `layer_candidate` in `INK|DAMAGE|BACKGROUND|UNCERTAIN`, `split_join_alternatives` (array of local IDs), `confidence_ordinal` in `CLEAR|UNCERTAIN|UNREADABLE`, and `touches_roi_boundary`. Distinguish **visible strokes** from **inferred graphemes**: no letter names, no phonetic values, no scribe IDs. Every mark, including tiny disconnected spots, gets a record or an explicit reason for exclusion.
3. Each annotation must be made on the unmodified RGB source first; any contrast-enhanced secondary view is logged and may alter uncertainty, not silently replace the source. Annotators mark occlusions, faint ink and parchment texture explicitly. A polygon crossing the crop boundary is tagged `touches_roi_boundary=true` and cannot be scored as a complete isolated mark.
4. **Positive procedural control:** each annotator independently marks a clearly continuous, visually agreed ink stroke from a separate f1r.1 context crop (not the test ROI), with its exact control rectangle frozen by a coordinator before annotation and source-pixel checksum recorded. **Negative procedural control:** similarly preselect an apparently blank parchment patch outside all text bands, without revealing class to annotators. Do not choose controls based on post hoc success. If control coordinates cannot be frozen from the licensed raster, **do not start**; no control result is currently claimed.
5. **Heldout:** physical leaves f11 onward are untouched for future confirmatory cross-folio claims. The second separately acquired, rights-cleared imaging witness of the same ROI is held out from annotators and must be hash- and coordinate-registered before cross-witness adjudication; derived crops from the same PDF are NOT independent witnesses.

## Frozen scoring and decision logic

- Before opening either annotation, the coordinator records each annotation file SHA and confirms no EVA strings or reviewer overlap. A and B are locked before pairing.
- For two polygons, calculate intersection-over-union (IoU) on the same raster. A candidate pair qualifies only if **IoU >= 0.50**, both are marked INK or UNCERTAIN, and neither is ROI-truncated. Use **maximum-cardinality bipartite matching**, breaking ties by maximum summed IoU, then stable lexicographic IDs. Do not count one-to-many matches as agreements; record splits/joins as disagreements.
- **Primary descriptive endpoint:** matched nontruncated INK-or-UNCERTAIN clusters divided by the union of unmatched and matched eligible clusters (one-to-one Jaccard-style count); report numerator/denominator, split/joins, all ROI-truncated exclusions, and an alternate strict `INK only` score. This is a measure of annotation agreement, NOT glyph truth.
- **Prespecified operational pass:** both independently chosen controls correctly classified (ink vs blank) AND primary agreement >= 0.80 AND no unadjudicated split/join affecting the ambiguous central cluster. Otherwise the boundary protocol **FAILS / INCONCLUSIVE** in this one ROI; revise only in a separately versioned exploratory cycle, never retrospectively change thresholds.
- The 0.50 and 0.80 cutoffs are *prospective operational conventions*, not empirical probabilities, published script thresholds, or an estimate of decipherment accuracy. A passing result still cannot validate a physical grapheme class without independent image witness and glyph-level cross-locus controls.
- No statistical p-value is preregistered for a single ROI; the constrained null is **independent annotator segmentation under the same pixels with no EVA access**, not random pixels, shuffled EVA or independent language evidence. Report raw disagreement rather than invent a null distribution. Future larger-sample significance needs a separate precommitted design.

## Execution gates and outcomes

**Currently available (DOCUMENTED):** PDF/raster checksums and fixed ROI from INV-004, editorial witness hash, earlier control types and source provenance. **Not performed (UNKNOWN):** independently blinded A/B polygon annotations, frozen independent control crop coordinates, second licensed imaging witness, source-specific cross-witness alignment, inter-reader scores, EVA-to-physical-stroke comparison. Do not claim VERIFIED annotation agreement from this protocol alone.

**Falsification:** the protocol explicitly allows the central ambiguous mark to be split differently, control failure, or low agreement. Such a result rejects the *operational reproducibility claim for this ROI*, not all natural-language or cipher hypotheses. Passing only permits a next-stage independent-image replication and then an editorial convention comparison.

**Rights:** owner possession and the canonical manifest instruction do not imply permission to redistribute image pixels or entire transcript lines. Only polygon coordinates, checksums and methods may enter GitHub pending rights clearance.

## Fixed denominators and next action

K-0001 remains ACTIVE / NOT_DONE. First-ten sides 20/20 indexed, 0/20 independently glyph-adjudicated; f1r 28/28 tentative line bands mapped, 0/28 fully adjudicated; zero verified physical grapheme classes and EVA mappings; 213/213 owner-canonical canvas IDs inventoried only; 3/40 narrowly completed A/W audits; 0/5 decipherment gates. **Next:** freeze positive/negative control rectangles on source image, commission a genuinely independent A/B annotation under the rules above, obtain rights-cleared second witness, and report raw annotation data and scoring before unsealing EVA. Do not run another same-raster threshold or crop-correlation cycle. No automation modification.
