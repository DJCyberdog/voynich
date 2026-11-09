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

**Research integrated:** EXP-0016 verified only the arithmetic consistency of EXP-0015 owner-reported token/transition totals: inferred zero-token lines exclude/join/split = 116/79/76, with the exclude figure matching the independently reported 116. This is **not** parser reproduction or permutation significance.  EXP-0001 through EXP-0010 (with gaps in canonical register), and EXP-0013 registered retrospectively. PR #20 integrated EXP-0014 f3r tokenization sensitivity and within-line shuffles (not significant); PR #21 integrated EXP-0015 owner-reported full-transcription scores and *preregistered but unexecuted* full-corpus permutation controls. Both are now recorded in canonical memory. **Open PRs at this snapshot:** none before this reconciliation branch. Neither result independently verifies manuscript semantics. Never count open PRs as integrated results.

**Next:** Audit per-line counts and independently reproduce EXP-0015; pin/audit ZL3b-n v3b source bytes, line parser and rights; run prespecified within-folio and within-line permutation nulls; independently spot-check canvas-to-physical-folio mapping. Do not infer a probability of decipherment from these work-package percentages.

## Resumption
Read this status together with the canonical memory registers, governance and open PRs. On a material integrated delta, update this README's dated status and denominator-defined progress bars via branch/PR only; do not manufacture commits on NO_CHANGE.

## Integrated multilingual hypothesis discovery (2026-11-09)

PR #32 integrated the initial DE/EN multilingual hypothesis-family discovery; this is a **source inventory, not an independently verified manuscript explanation**. Continue original-literature tracing and hypothesis tests under RM-010; FR/ES/IT detail checking remains open. The prior phrase “proposed, not yet integrated” was stale after the owner-authorized merge. The integrated research-state experiment remains EXP-0016, while PR #25–31 are outstanding drafts.

## Owner-directed forty-claim review programme (2026-11-09; proposed branch/PR, NOT YET INTEGRATED)

The two desk audits in **open Draft PR #33 and #34** contain **40/40 inventoried candidate statements = 100% of this explicitly bounded list**, not 40 independent mechanisms, successful tests or a census of every historical Voynich theory. Formal queue: `research/hypotheses/2026-11-09_40_claims_queue.jsonl`; protocol: `research/hypotheses/2026-11-09_40_claims_protocol.md`. **0/40** candidate-specific programme closeouts (0%) and **0 new confirmatory manuscript tests** at initialisation; source-audit briefs in unmerged #33/#34 pre-exist. Each item must receive a falsifiable, provenance-scoped test or an explicit evidence-based unresolved/BLOCKED/RETIRED outcome, without counting shared sources or tests multiple times.

**Unchanged integrated metrics:** **213/213 = 100%** of canvas IDs inventoried in owner-canonical SHA-pinned SRC-0007; *not* a physical folio concordance nor live Yale authentication. **0/5 = 0%** of independently satisfied decipherment acceptance gates; *not* the probability of decipherment. **Evidence:** explanation claims are generally CLAIMED/INFERRED/UNKNOWN, **workflow:** prioritised ACTIVE/WATCHING until tests. **Blockers:** individual source provenance, transcription permissions, blind control samples, open PR #25–31 and overlapping draft #33/#34. **Next:** P0 source verification, preregistration, image-/corpus-controlled tests on heldout material. Merge only on explicit Owner permission and after overlap review. The existing enabled hourly Voynich task is to be updated with this mandate without changing its schedule.
