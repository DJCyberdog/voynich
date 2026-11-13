# K-0001: Recognize ALL glyphs in MS408 — exhaustive mandate & grounded pilot

**2026-11-13 Owner amendment to existing K-0001.** The task is not to enumerate an EVA character set, but to identify **EVERY possible script-bearing glyph occurrence of the original manuscript**. Applies to physical recto/verso, every foldout/panel, main text, headings, illustrations with labels, diagrams, zodiac and radial text, tiny marginalia, later additions explicitly differentiated, one-off signs, possible diacritics, abbreviations, ligatures, allographs, retracing and corrections, unclear/damaged glyphs. No arbitrary frequency or certainty threshold excludes an occurrence. Non-script/physical damage must have an auditable exclusion record.

## Difference between observing and recognizing

1. An **occurrence ledger** must cover all physical script-bearing image regions, with immutable IDs, precise source image SHA/coordinates, folio/panel/line if available, alternatives and UNKNOWN/UNREADABLE flags. Truly unavailable/pixel-blocked regions remain incomplete and counted, not silently dropped.
2. A separate **class hypothesis ledger** links occurrences to grapheme, allograph, ligature, modifier/diacritic, correction and/or decoration alternatives with evidence, source/witness/version and multiple independent annotation decisions.
3. A **coverage ledger** records every physical folio/panel and its status (uninspected, screened, segmented, independently adjudicated, blocked); maintains counts for missed marks and ambiguous marks. Do NOT declare 100% just from 213/213 owner-canonical IIIF canvas IDs or 214 PDF pages (which include non-folio pages).
4. A **blind identity-validation ledger** records original-image and alternate-transcription discrepancies and tests predeclared structural predictions on separate physical leaves, not split faces of the same leaf; include section/hand and rare form strata.

## Explicit non-negotiable completion gates

(A) Full legally usable source/folio/side/foldout inventory, byte pinned and image-pixel/folio concordance established, independent provenance noted. (B) Every possible written-mark region inspected and segmented or individually recorded as unresolved; no missing regions hidden in denominators. (C) Rare singleton, detached-mark, diacritic, joined, circular, damaged, repaired and later-hand strata separately audited with a missed-mark recall check against independent reviewers. (D) All identity/group/segmentation hypotheses evaluated with blind independent annotators and disagreement records. (E) Candidate glyph-to-EVA/STA/aaa or alternate transcription maps version- and position-pinned; letters in EVA are not assumed to equal physical graphemes. (F) Unseen folios/physical-leaf heldouts and a second imaging or editorial witness, with frozen positive/negative controls and calibrated rejection tests. (G) Independent cross-check plus explicit unresolved tally; no forcing uncertain signs into known labels to improve a completion percentage. K-0001 cannot be DONE with recognition blockers, even if inventory coverage improves.

## Actual pilot evidence (not manuscript-wide)

User-supplied MS408 PDF **SHA-256 d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c**, 214 PDF pages; source f16r image crop PDF page 32 SHA-256 0303fee883b1c30dbc9eca2f10fc0480e383fba65cb07e02384cc76dde3cc5e0. Twelve FONT v0.2 slots VY001–VY012 are **twelve image samples, not twelve distinct verified glyphs**. Six openly chosen comparison folios: f2r p.6, f8r p.18, f18r p.36, f20r p.40, f24r p.48, f26r p.52 (same image witness). Earlier exploratory inspection reported four recurring-looking samples (VY002/004/007/008), three plausible (VY001/005/011), one undecided (VY003), four likely neighboring-mark composites (VY006/009/010/012). Template matching scored one plant illustration at 1.0, so no numeric match score is accepted as proof. **Zero independently validated grapheme classes; zero independently verified EVA correspondences; no manuscript-wide denominator or percentage; no blind experiment**.

### VY001 — three separate candidates, owner re-review overrides earlier assumption

- **A f16r PDF p32** raster bbox [209.5,230,248,267]: cross-loop with extensive curved lower-left terminal, in exploratory first-word context.
- **B f24r PDF p48** [330,230,364,263]: similar upper shape, lower-left termination appears flatter.
- **C f20r PDF p40** [463,383,497,416]: similar upper shape, lower-left termination differs again.

Owner directly noticed the lower-left difference. **No evidence these are identical physical graphemes, no proof of three authors, and no confirmation of phonetic trema/umlaut.** Keep distinct source candidate IDs and compare five model families without privileging one: distinct letters, contextual allographs, neighboring ligatures, base-plus-diacritic/abbreviation marks, image/crop/ink artifacts. If an added mark recurs with other base glyphs, a modifier becomes more plausible; if it joins neighbors predictably, a ligature becomes more plausible. Whole-word/neighbor and same-hand/section controls must be annotated before deciding. The previous initial-word alignment to EVA p in pocheody on f16r is a hypothesis tied to one selected text position, NOT an independently verified mapping and not a transfer to B/C.

## Artifacts and precise interpretation

- Machine-readable 12 sample records in 2026-11-13_K0001_v02_samples.jsonl: source SHA, f16r pixel bboxes, exploratory analogues, unconfirmed status, no raw image bytes.
- Three independent VY001 record IDs in 2026-11-13_K0001_VY001_triad.jsonl; no collapse into one grapheme.
- Font v0.2 remains a **visual illustration downstream of evidence**, not a font-wide typographic alphabet validated by K-0001.
- O-01 covers actual correction/reinking claims, K-0002 and EXP-0025 study predictive EVA statistics; no EVA-only model validates physical manuscripts without image-level support.

**Status:** K-0001 ACTIVE and NOT DONE. Image-wide glyph segmentation/recall not started, no confirmed class identity, no entire-manuscript coverage, no original source images or fonts redistributed to GitHub pending rights verification, no new EXP/decipherment. **0/5 acceptance gates unchanged.**
