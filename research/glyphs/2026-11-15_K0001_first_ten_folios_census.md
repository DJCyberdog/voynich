# K-0001 / INV-001 — First ten physical folios: source-grounded preliminary inventory (2026-11-15)

**Research priority:** owner S-tier / highest P0. **Scope:** physical leaves f1–f10, BOTH sides f1r…f10v, no folio beyond f10v. **Finding:** a first exact, source-pinned **20-surface / 268-editorial-line** index was created. This is an exploratory **image-page + editorial-witness census**, **NOT a complete physical glyph inventory**, not a decipherment experiment and not independent confirmation of EVA glyph classes.

## Frozen sources and independently checked scope

1. User-provided Yale Beinecke MS 408 PDF (214 pages), SHA-256 `d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c` (the existing local/source pointer checksum). All original PDF bytes matched; each page's embedded printed folio label was extracted and checked, **f1r = PDF p4 … f10v = PDF p23**. Pages 1–3 are front matter / binding, NOT counted as Folio 1. Twenty full-page overview images were visually screened, **not** zoom-audited glyph by glyph. Source images remain out of this PR.
2. Owner-supplied **ZL3b-n v3b (13 May 2025), IVTFF/EVA 2.0**, SHA-256 `bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc`; version header and actual bytes separately checked locally. Editorial text-line IDs were indexed; only derived counts, never original transcript lines, are committed.
3. Owner-designated canonical IIIF snapshot **SRC-0007** applies independently; its source authority is owner-canonical, **not live Yale-authenticated**. This pilot has **NOT** matched these PDF pages to IIIF canvas IDs or original-image pixel positions; PDF print-caption concordance does not substitute for IIIF concordance.
4. Reproduction: `research/glyphs/k0001_f1r-f10v_census.py` with owner-held matching PDF and IVTFF source bytes and an existing PyMuPDF installation (tested locally with MuPDF binding 1.26.7). No third-party code downloaded/executed, no original images/transcript redistributed.

## What was actually inventoried

- **20/20 pages**: verified PDF-page-to-printed-folio *captions*, plus overview visual screening (**DOCUMENTED/VERIFIED within PDF scope**).
- **268/268 editorial line records** in the pinned IVTFF subset f1r–f10v. This is a count of **transcribed lines**, not a verified count of image text lines or image-to-line alignments.
- **8,605 unqualified literal lowercase ASCII codepoint occurrences in that editor's transcription**, spanning **22 distinct ASCII labels** `abcdefghijklmnopqrstvy`. These are not 8,605 physical glyphs and not 22 identified graphemes. In particular EVA multi-letter conventions (e.g., `ch`, `sh`, `cth`), joined strokes, allographs, uncertain punctuation and image damage forbid one-to-one inference. Rare ASCII `b`, `g`, `j`, `v` are editorial witnesses, not newly proven characters.
- Ambiguity excluded rather than silently resolved: **28** bracketed alternatives, **32** braced ambiguous spans, **5** numbered unusual-glyph codes `@nnn;`, **6** literal question marks. Counts measure markup occurrences, not the number of actual damaged signs. Angular control/gap markers and comments excluded.
- **0** individually segmented and independently verified physical glyphs in this pilot; **0** validated grapheme classes; **0** validated EVA-to-glyph mappings. No hand attribution or transcription-to-image alignment was tested. Special warning for f1r: source editor reports non-Voynich marginal alphabet/signature and unusually marked paragraph starts; main-text EVA census must not absorb them as ordinary glyphs.

| Folio | PDF page | Editorial lines | Unqualified EVA ASCII units |
|---|---:|---:|---:|
| f1r | 4 | 28 | 976 |
| f1v | 5 | 10 | 390 |
| f2r | 6 | 15 | 463 |
| f2v | 7 | 8 | 284 |
| f3r | 8 | 20 | 563 |
| f3v | 9 | 14 | 385 |
| f4r | 10 | 13 | 323 |
| f4v | 11 | 14 | 415 |
| f5r | 12 | 7 | 265 |
| f5v | 13 | 6 | 231 |
| f6r | 14 | 14 | 386 |
| f6v | 15 | 21 | 502 |
| f7r | 16 | 10 | 345 |
| f7v | 17 | 9 | 359 |
| f8r | 18 | 21 | 684 |
| f8v | 19 | 17 | 558 |
| f9r | 20 | 10 | 394 |
| f9v | 21 | 12 | 388 |
| f10r | 22 | 12 | 428 |
| f10v | 23 | 7 | 266 |
| **Total** | **20 surfaces** | **268** | **8,605** |

See `2026-11-15_K0001_f1r-f10v_preliminary_coverage.jsonl` for per-folio ID, PDF label, scope, ASCII label types, separated ambiguity markers, source digests and **explicit NULL physical-glyph counts**. The automated counts are derived metadata, not a full-transcript copy.

## Falsification design and controls

**Question:** Does the source-pinned editorial inventory sufficiently identify individual image graphemes? **Prediction to challenge:** a one-to-one EVA-character-to-physical-glyph assumption would require one spatially identifiable stroke unit per encoded character and stable segmentation under an independent blinded witness. **Strongest alternative:** ligatures, context-dependent shapes, independent marginalia, damaged signs and editorial segmentation make EVA-to-mark correspondence non-bijective. Neither model has been accepted.

**Performed source/census controls:** (positive) check all 20 PDF footer folio labels, PDF hash, exact editorial source version, unique line IDs and expected 268/8605 regression totals; (negative) exclude PDF front matter, comments, alternative readings and rare-symbol markup from any “unqualified ASCII” count. These verify the editorial census ONLY. **NOT RUN:** pixel-level mark detection and image-to-EVA correspondence, sensitivity to a second transcription witness, blind annotator test, class-recall test, manuscript-level statistics. **Held-out for confirmatory mapping:** new physical leaves (f11 onward), plus an independently sourced image/transcription witness; do not treat the currently screened f1–f10 as unseen.

## Classification / limitations / next step

- **VERIFIED scoped:** input SHA-256 values, PDF printed captions, 20-row index, 268 editorial lines, derived 8605/22 ASCII statistics.
- **DOCUMENTED scoped:** original page overview; editorial anomalies and variant markup as found in pinned witness.
- **UNKNOWN:** total physical glyph occurrences, exact script-bearing ink-region boundaries, all grapheme/ligature/modifier classes, second-witness concordance, image rights for redistribution, translation/semantics.
- **ACTIVE:** K-0001 inventory. **NOT_DONE:** its A–G completion gates. No language/natural-cipher/nonlanguage/hybrid model tested or favored. The 40-point claim queue remains open and subordinate under owner RM-036 priority.

**Next bounded research step:** use first-page full-resolution image f1r to construct **pixel-coordinate regions for every possible writing-bearing mark**, distinctly including marginal alphabet, paragraph initials, original text and signature; assign unresolved IDs even where multiple strokes are joined. Then repeat surface by surface through f10v with blind second-pass review, check against another image witness and reserve unseen physical leaves. Do not report folio glyphs “completed” from an EVA census.

**Progress-denominator honesty:** 20/20 target sides source-indexed and overview-screened, 0/20 pixel-level fully segmented and independently checked, 0 confirmed grapheme classes, 0 verified EVA mappings. Existing whole-project totals remain 213/213 *canvas IDs inventoried* (not folio-image verification), 3/40 narrowly closed audit claims and 0/5 decipherment gates. No total decipherment percentage exists.
