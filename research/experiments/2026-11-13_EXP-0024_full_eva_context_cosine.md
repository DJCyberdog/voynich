# EXP-0024 — Complete immediate EVA context cosine: ASCII units vs composite glyph units

**13 November 2026 · RESEARCH_COMPLETED as descriptive corpus statistic · exploratory, not preregistered decipherment.** Part of Draft PR #38, **not integrated main**. Code: `research/scripts/exp0024_eva_allpair_context_cosines.py`.

## Question
For **every unordered pair** of observed EVA characters/glyph units, how similar are the *immediate ordered preceding/following* contexts? Does the f/p similarity highlighted by f57v position 9 remain distinctive after a full 25-character and compound-aware comparison?

## Source and exact reproducible filter
Owner-held ZL3b-n v3b (13 May 2025), SHA256 `bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc`; stable source registry SRC-0101, notation standards SRC-0019. Ignore f57v/f49v/f66r specially annotated list folios. Read tagged `P0` lines and remove editorial angle-bracket comments, paragraph begin/end tags and `<->` treated as separator. Split at whitespace/period, drop uncertain-comma-containing tokens, require `[a-z]{2,}`. Result **27,727 words**, **201 folio identifiers**, 3,827 selected P0 lines.

A token unit u has a sparse count vector `v_u[(left,right)]` of its immediate previous and next *unit* within a word; `^` and `$` represent word boundaries. Compare **raw-frequency cosine** `v_a·v_b/(||v_a||||v_b||)`, bounded 0..1. This is DESCRIPTIVE and does **not** directly imply identical phonemes, grammatical functions, substitution, encryption or statistical significance.

Two different segmentation choices were deliberately kept **separate**:
- **ASCII / literal**: 25 observed lowercase EVA transcription symbols, **300 unordered comparisons**; e.g. `ch` contributes c then h.
- **Glyph-aware operational**: 31 observed units, **465 unordered comparisons**; greedy longest match of common EVA composites `cth, ckh, cph, cfh, ch, sh`, then residual single lowercase EVA symbols. This is an *explicit modeling convention*, not independent manuscript stroke identity. Compare published rules <https://www.voynich.nu/transcr.html> and <https://www.voynich.nu/hist/gabriel/eva2_reference.pdf>.

## Highest similarity pairs with both glyph frequencies >=100

| Rank | Glyph-aware pair | cosine | minimum count |
|---:|---|---:|---:|
| 1 | `ch / sh` | **0.973153** | 3,615 |
| 2 | `k / t` | **0.956963** | 4,335 |
| 3 | `f / p` | **0.954148** | 273 |
| 4 | `cph / cth` | **0.913487** | 170 |
| 5 | `l / r` | **0.904320** | 5,184 |
| 6 | `m / r` | **0.875735** | 728 |
| 7 | `ch / cph` | 0.847394 | 170 |
| 8 | `cph / sh` | 0.846840 | 170 |
| 9 | `ckh / cth` | 0.756347 | 757 |
| 10 | `ch / cth` | 0.685428 | 757 |
| 11 | `cth / sh` | 0.661337 | 757 |
| 12 | `l / m` | 0.648304 | 728 |
| 13 | `cth / q` | 0.625043 | 757 |
| 14 | `ckh / cph` | 0.612357 | 170 |

Literal-ASCII top stable pairs are `c/s=0.955924`, `f/p=0.952110`, `k/t=0.938444`, `l/r=0.903531`, `m/r=0.875732`. The prior EXP-0023C **f/p=0.95211038575** is reproduced exactly with the unchanged literal-ASCII corpus definition. Compound-aware f/p changes slightly to **0.954148272** because letters inside composites are no longer counted as stand-alone neighbors.

**Warning: rare-value trap.** Among ALL pairs the raw highest value is `q/v≈0.9999` but **v occurs once** in this filtered corpus. Such near-1 values from a single rare glyph are not meaningful. Mark pairs with any member below 100 occurrences as low-coverage and never rank them as credible substitutions. Under the compound segmentation, `h` and `c` residual single units each occur only 3 and 2 times: the original `ch` is not the same unit as bare `c`.

## What can and cannot be concluded
- **VERIFIED within pinned source and parser:** all 300 ASCII and all 465 operational compound-glyph pair cosines are reproducibly calculable; distinct context-similarity clusters `ch/sh`, `k/t`, `f/p`, `l/r`, `cph/cth`.
- **INFERRED:** the f57v ninth-slot f/p alternation is part of a broader family of glyph pairs filling similar *orthographic slots*, not a unique manuscript-wide decoder control signature. Relatedness is not value equivalence.
- **UNKNOWN:** whether any pair maps to the same plaintext, is a homophonic cipher variant, is a scribal allograph or arises from morphology/section/position/copy model.
- Similar cosine can arise because two different glyphs share word beginnings/endings. The vectors pool all folios, hands, Currier sections and word positions; no matched-frequency or hand-conditioned significance test was performed.
- **Next concrete falsifier:** freeze per-folio/hand segmentation and compare matched-frequency, split-witness, prefix/suffix/word-position-conditioned similarities and predictive interchange substitution on untouched folio groups. Do not infer f/p decoding, collapse multi-glyph sequences, or claim manuscript glyph observation without independent manuscript image checks.
- Manuscript reading/script/language/semantics/origin acceptance criteria remain **0/5**. Current owner-canonical IIIF snapshot untouched, no permission change, no source redistribution, no change to hourly automation.

The accompanying downloadable workbook/CSV bundle from this ChatGPT run includes the **complete 25×25 and 31×31 numeric matrices**, all 765 ranked pair records, token frequencies and heatmaps; the repository reproducer independently regenerates all pair matrices from the owner-held source file without redistributing source bytes.