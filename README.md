# PROJECT VOYNICH

Evidence-led, falsification-oriented investigation of Yale Beinecke MS 408. **No decipherment is assumed.**

## Research boundaries
Distinguish diplomatic reading, script decipherment, language identification, semantic interpretation, and dating/provenance. Evidence classes: VERIFIED, DOCUMENTED, CLAIMED, INFERRED, UNKNOWN, CONTRADICTED. Operational classes: ACTIVE, WATCHING, BLOCKED, SATURATED, RETIRED. Reproducible negative results are first-class outcomes.

## Governance
This initial README is the single authorized empty-repository bootstrap commit. All subsequent changes use topic branches and pull requests. Only this repository is a write target. Owner-authorized merges require checks for duplicate work, changed files and current main. See `docs/` and `memory/` after the first initialization PR.

## Primary source
Yale Beinecke Rare Book & Manuscript Library, MS 408: https://collections.library.yale.edu/catalog/2002046 ; manuscript collection explanation: https://beinecke.library.yale.edu/beinecke/collections/beinecke-cipher-voynich-manuscript . Source metadata, transcription versions and rights must be verified before data ingestion.

## Current research status (2026-11-05; main through EXP-0016; EXP-0017 proposed, not yet integrated)

These are **work-package completion ratios**, not an estimated percentage of decipherment. The numerators and denominators are explicitly scoped; a completed inventory is not an authenticated image-to-folio concordance.

| Work package / denominator | Verified or recorded completion | Progress |
|---|---:|---|
| Unique canvas identifiers inventoried in owner-canonical SRC-0007: 213 expected IDs | 213/213 = **100%** (snapshot parsing only) | `██████████` |
| Full decipherment acceptance gates demonstrably satisfied under `docs/DECIPHERMENT_CRITERIA.md`: 5 gates | 0/5 = **0%** (no gate documented as passed) | `░░░░░░░░░░` |

**Evidence and workflow:** Canvas inventory VERIFIED only for the supplied SHA-256-pinned snapshot; user-designated canonical status is **not** independent live Yale authentication (**UNKNOWN**). Physical folio/canvas correspondence, visible glyphs, transcription conventions, language, semantics and historical dating are distinct layers. Decipherment remains **UNKNOWN**. Folio/canvas concordance and transcription provenance **ACTIVE**; independent live-manifest retry **SATURATED** by owner decision D-0005; cross-witness manuscript-level confirmation **BLOCKED** pending independent transcription, physical glyph and full rights/IVTFF parser audits; the narrow permutation result is **VERIFIED** for the uploaded source and code.

**Research integrated:** EXP-0016 verified only the arithmetic consistency of EXP-0015 owner-reported token/transition totals: inferred zero-token lines exclude/join/split = 116/79/76, with the exclude figure matching the independently reported 116. This is **not** parser reproduction or permutation significance.  EXP-0001 through EXP-0010 (with gaps in canonical register), and EXP-0013 registered retrospectively. PR #20 integrated EXP-0014 f3r tokenization sensitivity and within-line shuffles (not significant); PR #21 integrated EXP-0015 owner-reported full-transcription scores and preregistered the then-unexecuted full-corpus permutation controls, which proposed EXP-0017 now implements. Both are now recorded in canonical memory. **Open PRs at the start of EXP-0017:** none; PR #25 remains a draft until owner authorization. Neither result independently verifies manuscript semantics. Never count open PRs as integrated results.

**EXP-0017 (proposed PR, NOT integrated until merge):** Owner-uploaded ZL3b-n v3b and original evaluator reproduce EXP-0015 exactly. Six independently executed 1,000-permutation null tests (within-folio and within-line for each of three comma policies) yielded zero exceedances per 1,000 draws, with empirical p=1/1001 in each cell. Original four-class evaluator reproduced all uploaded values; block frequency preservation was checked in all six cells. These are statistical order-dependence tests, not language or semantics evidence. **Next:** preregister position/length/section-conditioned nulls and test an independent transcription witness; spot-check canvas/physical folios. Do not infer a probability of decipherment from these work-package percentages.

**EXP-0018 (stacked draft; NOT integrated until both PRs merge):** Independently executed a strict position-and-length-matched falsification: 1,000 within-(folio, exact line length, exact token offset) class-shuffles per exclude/join/split. In all three, the original Markov gain exceeded every randomized gain (one-sided Monte Carlo p=1/1001 each). A second within-(folio, exact offset) family also rejected all three, so **6/6 scoped null cells** rejected positional exchangeability. An exploratory held-out position-aware prediction model also benefited from previous-class information (+0.011352/+0.010506/+0.009590 nats per transition). This rules out those particular positional marginals as a full explanation, but **does not** control each line's own class composition, prove a neighboring-token mechanism, or satisfy a decipherment gate. See EXP-0018 report; stacked after the still-draft EXP-0017 PR #25. No corpus redistribution, no semantic claim, no changes to 213/213 inventory or 0/5 decipherment gates.

**EXP-0019 (stacked draft; not yet merged):** Data-integrity audit of Tobias Franke's reported 176-folio VGM371/377 subset. Six local ZL3b-n row-scope/comma-policy pipelines were tested for exact simultaneous match to 176 IDs, 3,659 nonempty lines, 3,633 lines with 2+ tokens, 30,925 tokens and all four suffix-class totals. Five were infeasible even as linear relaxations. P-text-only + split permits at least TWO distinct 176-ID subsets matching every aggregate yet yielding different locally computed Markov gains (0.016713 / 0.016507 vs published 0.017003). A 5,000-draw unconditioned random-176 sensitivity is **NOT** comparable on token totals (4/5,000 random sets reached 30,925 tokens). Franke's original VGM356/interlinear_all.csv, VGM377/run377.py, ID manifest and historical selection rationale were not found as downloadable artifacts; selection intent remains UNKNOWN and there is **no evidence of deliberate manipulation**. Detailed report and summary under EXP-0019; project pipeline and 0/5 decipherment criteria unchanged.

## Resumption
Read this status together with the canonical memory registers, governance and open PRs. On a material integrated delta, update this README's dated status and denominator-defined progress bars via branch/PR only; do not manufacture commits on NO_CHANGE.
