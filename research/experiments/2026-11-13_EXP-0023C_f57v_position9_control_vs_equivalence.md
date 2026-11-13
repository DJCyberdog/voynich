# EXP-0023C — Is f57v's ninth-slot f/p switch a decoder control?

**Date:** 2026-11-13. **Workflow:** RESEARCH_COMPLETED for one bounded *exploratory* same-witness test; **WATCHING** for glyph-level and out-of-sample meaning tests. **Evidence:** VERIFIED local IVTFF computation / DOCUMENTED historical alternative / UNKNOWN semantic role.

## Core question and competing explanations

User proposed that the glyph at **position 9** of four 17-unit sectors on MS 408 f57v is important to decoding. Competing hypotheses:

- **H-control:** `f` / `p` is an explicit control bit (mode, state, reference quadrant), which should eventually yield a stable mapping to different *observable* outputs in other untouched, physically comparable encoded regions.
- **H-equivalence:** `f` / `p` are variants, closely related signs or possible homophones/near-substitutes with similar orthographic distributions. Identity of plaintext letters is NOT proven.
- **H-copy:** copy/edit/ornamentation of a circular reference sequence; after two sectors the exemplar or glyph choice changed, without encoding anything.
- **H-contextual:** different scribal, section, word-position or transcription conventions determine the glyph choice.

The analysis was designed **after** seeing f57v and the historical discussion, so it is not a new blind decipherment test. It cannot select a semantic reading without a frozen external plaintext anchor.

## Primary source and historical priority

- SHA-256 pinned owner-supplied ZL3b-n v3b (13 May 2025): `bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc` (SRC-0101). Original `<f57v.3,+Cc>`: 68 **dot-separated editorial transcription units**, 4 × 17; `@169;v` is a composite editorial unit; `[d:j]` explicitly denotes ambiguity. These are not newly image-verified 68 glyphs.
- Historic independent textual witness from VIB (SRC-0047) reports four repetitions, variations in slots 3, 9 and 16 depending on reader.
- **Mary E. D'Imperio (1978), *The Voynich Manuscript: An Elegant Enigma*, pp. 24–25, §4.1.4, NSA-hosted primary monograph**, already discusses the two `f` versus two `p` forms at slot 9. She suggests functional identity of one- and two-looped forms while explicitly cautioning that shapes are clearly distinct and lack ambiguous intermediates. The original monograph mistakenly prints **f57r** for the ring widely identified as **f57v**. New SRC-0051. This is not our discovery.
- Voynich Studies (18 Oct 2026), *List pages*, publicly reports a context cosine ~0.948 and emphasizes evidence for functionally similar `f/p`; independently reproduced on a slightly different token parser below. The same site counts 18 vs our 17 transcription units (likely segmentation convention, not settled glyph truth); site is secondary, not a verified independent manuscript observation. New SRC-0052.

## Exact four sectors and immediate logic

| Internal slot | Sector 1 | Sector 2 | Sector 3 | Sector 4 |
|---|---|---|---|---|
| 3 | `[d:j]` | `d` | `d` | `d` |
| **9** | **`f`** | **`f`** | **`p`** | **`p`** |
| 16 | `I` | `c` | `c` | `c` |

All remaining 14 slots have the same local IVTFF unit across all four sectors. Adjacent sector matches 1→2: **15/17**, 2→3: **16/17**, 3→4: **17/17**. The sole change between sectors 2 and 3 is at **slot 9**. Consequently there is **no observable corresponding change in any other slot** that covaries exactly with f versus p. A simple "switch changes other visible sector glyphs" model is **CONTRADICTED within this circle**, but a switch affecting *unobserved decoded output* remains **UNKNOWN / NOT IDENTIFIABLE from ciphertext alone**.

The specific 2+2 arrangement by itself is weak evidence for a control: conditional on two f and two p and arbitrary quadrant order, exactly `ffpp` has probability 1/6; either `ffpp` or `ppff` is 2/6. An intentional copy-template change can make the same arrangement.

## Independently run descriptive running-text controls

A separate stdlib script re-parsed the owner's **entire unchanged original file**, retained only tagged `P0` lines, removed editorial comments, tokenized certain-period/whitespace segments, excluded comma-uncertain and non-ASCII words, and excluded special list leaves f57v/f49v/f66r from this context sample. No images, word translations, or copied corpus bytes were added.

- **27,727** ordinary P0 token instances in this filter, containing **1,594** `f/p` occurrences on **195** eligible folios; **f=326**, **p=1,268**.
- **90 distinct pairs of word types** differ by exactly one `f↔p` character (e.g., `fchedy/pchedy`, `qofchedy/qopchedy`). This is descriptive; it needs matched controls before claiming unusual abundance.
- Cosine of immediate ordered **left/right character** co-occurrence vectors, including word boundaries `^/$`: **f/p=0.9521104**; comparators **k/t=0.9384441**, **f/k=0.4188183**, **p/t=0.5892956**. The present cosine was calculated on the stated exact parsing and not copied from the secondary site's 0.948.
- Frequencies and positions still differ: `f` is ~20.5%, `p` ~79.5% of f/p events; word-initial `f` 84/326 and `p` 446/1268. Similar lexical contexts **do not imply interchangeable plaintext meanings or same glyph identity**.
- Fixed five-fold **folio-heldout** descriptive check using SHA-assigned folds: global Beta(0.5,0.5) prior vs word-position-smoothed prior (strength 20) vs pair-context-smoothed prior (strength 20). Average context model gain over global **+0.004386 nats per occurrence**, position-only **+0.002092**, context beyond position **+0.002294**. Fold gains varied in sign; 2,000 seeded folio-resample bootstrap **95% [−0.004409,+0.012885]**, including zero. This model provides **no robust independent classification evidence** that one glyph signifies a control state.
- 128 folios in the filtered sample contain both forms, so their appearance is not merely caused by mutually exclusive scribal pages, although finer hand/section confounding remains possible.

These are **exploratory descriptive diagnostics**, with no prespecified significance family, multiple-model corrections or independent paleographic validation.

## Assessment

- **VERIFIED, scoped:** a real f→p change precisely between the two pairs of 17-unit cycles in the pinned transcription; broad f/p word-context overlap elsewhere; weak local predictive discrimination between choices.
- **DOCUMENTED:** D'Imperio's *existing* functional-equivalence interpretation and her explicit counterpoint that the looped shapes are clearly distinct. Other transcriptions differ in several glyph segmentation/reading details.
- **INFERRED (currently best working explanation):** the ring could show alternative marks occupying one **structural slot**: scribal allograph, near-homophonous glyph, or chosen variant of one class. This is an *equivalence-class lead*, not decipherment.
- **UNKNOWN:** whether position 9 toggles a hidden decoding mode, indicates a pair of quadrants, is a homophonic cipher variant, or represents the intentional mid-copy switch of one template. All these models can produce the same 4-sector string, with **no deciphering key identified**.
- **Narrowly disfavored:** a controller that visibly changes the remaining sector symbols; there is no corresponding 2+2 co-change in their observed glyph positions.
- Physical high-resolution glyph verification was not independently achieved here. NSA PDF screenshot requests and an external folio image fetch were inaccessible; existing published reproductions were viewed at source-summary level, not audited stroke-by-stroke. Do not assert direct manuscript visual authentication or redefine 17 vs 18 as settled.
- **0/5 decipherment acceptance gates.** No decoded word or syllable.

## Specific falsifier that would progress the key idea

Freeze **before target inspection** the rule "one loop vs two loops is a decoder control" including: (1) exact physically imaged f/p glyph classes and how they map to EVA; (2) which two semantic/algorithmic outputs differ; (3) a predicted observable consequence at specific previously unseen non-circular loci; (4) matching copy-edit and homophone/allograph baselines on identical loci; (5) blind scoring threshold. Without those commitments, reinterpreting the two forms post-hoc is unidentifiable and cannot count as decipherment.

**Repo policy:** Add this as an EXP-0023C follow-up to existing Draft PR #38 (not a distinct independent manuscript source). Current main remains untouched; source text and scans are not redistributed; no automation changed. 