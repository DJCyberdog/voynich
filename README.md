# PROJECT VOYNICH

Evidence-led, falsification-oriented investigation of Yale Beinecke MS 408. **No decipherment is assumed.**

## Research boundaries
Distinguish diplomatic reading, script decipherment, language identification, semantic interpretation, and dating/provenance. Evidence classes: VERIFIED, DOCUMENTED, CLAIMED, INFERRED, UNKNOWN, CONTRADICTED. Operational classes: ACTIVE, WATCHING, BLOCKED, SATURATED, RETIRED. Reproducible negative results are first-class outcomes.

## Governance
This initial README is the single authorized empty-repository bootstrap commit. All subsequent changes use topic branches and pull requests. Only this repository is a write target. Owner-authorized merges require checks for duplicate work, changed files and current main. See `docs/` and `memory/` after the first initialization PR.

## Primary source
Yale Beinecke Rare Book & Manuscript Library, MS 408: https://collections.library.yale.edu/catalog/2002046 ; manuscript collection explanation: https://beinecke.library.yale.edu/beinecke/collections/beinecke-cipher-voynich-manuscript . Source metadata, transcription versions and rights must be verified before data ingestion.

## Current research status (2026-11-13; EXP-0017 integration reconciled)

These are **work-package completion ratios**, not an estimated percentage of decipherment. The numerators and denominators are explicitly scoped; a completed inventory is not an authenticated image-to-folio concordance.

| Work package / denominator | Verified or recorded completion | Progress |
|---|---:|---|
| Unique canvas identifiers inventoried in owner-canonical SRC-0007: 213 expected IDs | 213/213 = **100%** (snapshot parsing only) | `██████████` |
| Full decipherment acceptance gates demonstrably satisfied under `docs/DECIPHERMENT_CRITERIA.md`: 5 gates | 0/5 = **0%** (no gate documented as passed) | `░░░░░░░░░░` |

**Evidence and workflow:** Canvas inventory VERIFIED only for the supplied SHA-256-pinned snapshot; user-designated canonical status is **not** independent live Yale authentication (**UNKNOWN**). Physical folio/canvas correspondence, visible glyphs, transcription conventions, language, semantics and historical dating are distinct layers. Decipherment remains **UNKNOWN**. Folio/canvas concordance and transcription provenance **ACTIVE**; independent live-manifest retry **SATURATED** by owner decision D-0005; corpus-wide confirmatory statistics **BLOCKED** pending independently audited rights, inputs and parser.

**Research integrated:** EXP-0016 verified only the arithmetic consistency of EXP-0015 owner-reported token/transition totals: inferred zero-token lines exclude/join/split = 116/79/76, with the exclude figure matching the independently reported 116. This is **not** parser reproduction or permutation significance.  EXP-0001 through EXP-0010 (with gaps in canonical register), and EXP-0013 registered retrospectively. PR #20 integrated EXP-0014 f3r tokenization sensitivity and within-line shuffles (not significant); PR #21 integrated EXP-0015 owner-reported full-transcription scores and *preregistered but unexecuted* full-corpus permutation controls. Both are now recorded in canonical memory. **PR status:** integrated work listed through EXP-0017 only; remaining open experimental and source-audit PRs require individual review. Neither result independently verifies manuscript semantics. Never count open PRs as integrated results.

**EXP-0017 — locally reproduced:** SHA-256-pinned, owner-supplied ZL3b-n v3b and unchanged evaluator reproduce EXP-0015's baseline exactly across three comma policies and five folds. A separate 2026-11-13 local recalculation independently reproduced all six sets of 1,000 frequency-preserving permutation draws to numerical tolerance below 1.1e-16; no randomized draw exceeded the observed gain. Six correlated Monte Carlo results each have one-sided resolution p=1/1001. This is **VERIFIED solely for the pinned upload and tokenization model**, not manuscript image/glyphs, language, semantics or authorship; alternative position/section mechanisms remain viable. Source IDs SRC-0101..0104 are unique cross-branch reconciliations of former draft-only SRC-0021..0024 and do not change main's Wikipedia-related SRC-0021..0024. Q-020 tracks the unresolved stronger-null and independent-witness question. **Next:** EXP-0018 position/length controls (#26), EXP-0022 contextual controls (#36), then reconcile hypothesis and synthetic-null PR backlog. No overall decipherment probability is computed.

## Resumption
Read this status together with the canonical memory registers, governance and open PRs. On a material integrated delta, update this README's dated status and denominator-defined progress bars via branch/PR only; do not manufacture commits on NO_CHANGE.

## Multilingual hypothesis-discovery direction (2026-11-09; landscape inventory integrated via PR #32)

A scoped DE/EN Wikipedia-led hypothesis-family landscape inventory and source trail was integrated in PR #32. It is discovery, not manuscript evidence or a decipherment result; FR/ES/IT and original-paper audits remain open. The remaining detailed #33/#34 claim audits and #35 queue are separate open drafts; do not count them as integrated. Progress denominators unchanged: **213/213 canvas IDs inventoried** (owner-canonical snapshot only), **0/5 decipherment gates passed**. No overall decipherment percentage exists. Seven older open draft PRs (#25–#31) overlap README/memory and require reconciliation. Next: audit original hypothesis papers, source rights, blind tests and PR backlog.
