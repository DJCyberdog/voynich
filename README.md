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

## Methodological preflight — 2026-11-09 (draft, NOT integrated)
EXP-0020 synthetic 3×3 three-class enumeration finds 12 admissible Latin-square states and zero elementary 2×2 checkerboard moves between them; this falsifies universal irreducibility of that move family, **not** a manuscript hypothesis. Real four-class source-table reachability and convergence remain BLOCKED. Work-package denominators remain 213/213 canvas IDs inventoried (100% of snapshot inventory) and 0/5 decipherment acceptance gates (0%); no global decipherment percentage. This draft is separate from integrated main EXP-0016 and stacked PRs #25–#27; reconcile before merge. Owner-canonical Yale manifest has no independent live authentication.


**EXP-0020 draft extension (2026-11-09, not integrated):** In the same synthetic 12-state Latin-square test, whole-row transpositions alone give components 6+6, whole-column transpositions alone 6+6, and their union connects 12/12 states. This identifies a possible longer-move family, **not** a validated real four-class sampler. Row/column exchanges require matching respective margins in actual data. Existing 213/213 (canvas-ID inventory only) and 0/5 (decipherment gates) denominators remain unchanged. PR #28 remains draft and overlaps #25–#27; no merge authorized.

### EXP-0020 four-class reachability addendum (2026-11-09; Draft, NOT integrated)
Exploratory exhaustive synthetic 4×4 Latin-square test: **576 states, four disconnected components of 144** under combined whole-row and whole-column swaps, versus one 12-state component in the order-3 positive control. The universal irreducibility claim for that combined move family is **CONTRADICTED** in this synthetic scope; real Voynich four-class margins, alternative cycles and held-out folios are **UNKNOWN**. Report: `research/experiments/2026-11-09_EXP-0020_fourclass-orbits.md`. EXP-0020 remains **BLOCKED** for statistical inference; no transcription or manuscript images used. Existing package denominators unchanged: canvas IDs 213/213 (100% snapshot inventory, not physical concordance); decipherment gates 0/5 (0%, not a decipherment probability). PR #25→#26→#27 and PR #28 remain unintegrated; this addendum is stacked on #28 and must not merge independently. Next: rights-reviewed real four-class table and tested alternating cycles.
