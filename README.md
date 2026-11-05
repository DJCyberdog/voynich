# PROJECT VOYNICH

Evidence-led, falsification-oriented investigation of Yale Beinecke MS 408. **No decipherment is assumed.**

## Research boundaries
Distinguish diplomatic reading, script decipherment, language identification, semantic interpretation, and dating/provenance. Evidence classes: VERIFIED, DOCUMENTED, CLAIMED, INFERRED, UNKNOWN, CONTRADICTED. Operational classes: ACTIVE, WATCHING, BLOCKED, SATURATED, RETIRED. Reproducible negative results are first-class outcomes.

## Governance
This initial README is the single authorized empty-repository bootstrap commit. All subsequent changes use topic branches and pull requests. Only this repository is a write target. Owner-authorized merges require checks for duplicate work, changed files and current main. See `docs/` and `memory/` after the first initialization PR.

## Primary source
Yale Beinecke Rare Book & Manuscript Library, MS 408: https://collections.library.yale.edu/catalog/2002046 ; manuscript collection explanation: https://beinecke.library.yale.edu/beinecke/collections/beinecke-cipher-voynich-manuscript . Source metadata, transcription versions and rights must be verified before data ingestion.

## Current research status (2026-11-05; after integrated PRs #21 and #22)

These are **work-package completion ratios**, not an estimated percentage of decipherment. The numerators and denominators are explicitly scoped; a completed inventory is not an authenticated image-to-folio concordance.

| Work package / denominator | Verified or recorded completion | Progress |
|---|---:|---|
| Unique canvas identifiers inventoried in owner-canonical SRC-0007: 213 expected IDs | 213/213 = **100%** (snapshot parsing only) | `██████████` |
| Full decipherment acceptance gates demonstrably satisfied under `docs/DECIPHERMENT_CRITERIA.md`: 5 gates | 0/5 = **0%** (no gate documented as passed) | `░░░░░░░░░░` |

**Evidence and workflow:** Canvas inventory VERIFIED only for the supplied SHA-256-pinned snapshot; user-designated canonical status is **not** independent live Yale authentication (**UNKNOWN**). Physical folio/canvas correspondence, visible glyphs, transcription conventions, language, semantics and historical dating are distinct layers. Decipherment remains **UNKNOWN**. Folio/canvas concordance and transcription provenance **ACTIVE**; independent live-manifest retry **SATURATED** by owner decision D-0005; corpus-wide confirmatory statistics **BLOCKED** pending independently audited rights, inputs and parser.

**Research integrated:** EXP-0017 reproduces the uploaded owner full-transcription evaluator exactly and executes 1,000 folio-shuffle and 1,000 line-shuffle null draws per comma policy (six controls; 0/1,000 exceedances each; one-sided empirical p=0.000999 per separately evaluated control). This VERIFIES class-order dependence relative to these exchangeability nulls **only** in the frozen local transcript/parser; positional effects and alternate witnesses remain untested. The corpus itself is not committed due to rights review. EXP-0016 verified only the arithmetic consistency of EXP-0015 owner-reported token/transition totals: inferred zero-token lines exclude/join/split = 116/79/76, with the exclude figure matching the independently reported 116. This is **not** parser reproduction or permutation significance.  EXP-0001 through EXP-0010 (with gaps in canonical register), and EXP-0013 registered retrospectively. PR #20 integrated EXP-0014 f3r tokenization sensitivity and within-line shuffles (not significant); PR #21 integrated EXP-0015 owner-reported full-transcription scores and *preregistered but unexecuted* full-corpus permutation controls. Both are now recorded in canonical memory. **Open PRs at the start of EXP-0017:** none; review the new EXP-0017 PR before counting it as integrated. Neither result independently verifies manuscript semantics. Never count open PRs as integrated results.

**Next:** Preregister position/length/section-conditioned controls, independently test other transcription witnesses and audit original images and text rights; independently spot-check canvas-to-physical-folio mapping. Do not infer a probability of decipherment from these work-package percentages.

## Resumption
Read this status together with the canonical memory registers, governance and open PRs. On a material integrated delta, update this README's dated status and denominator-defined progress bars via branch/PR only; do not manufacture commits on NO_CHANGE.
