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

## Proposed research-direction delta (2026-11-09; **not yet integrated**)

A scoped DE/EN Wikipedia-led hypothesis-family inventory and source trail is proposed in the dedicated hypothesis-audit PR. It is discovery, not manuscript evidence or a decipherment result; FR/ES/IT and original-paper audits remain open. Integrated status above stays EXP-0016 until owner-authorized merge. Progress denominators unchanged: **213/213 canvas IDs inventoried** (owner-canonical snapshot only), **0/5 decipherment gates passed**. No overall decipherment percentage exists. Seven older open draft PRs (#25–#31) overlap README/memory and require reconciliation. Next: audit original hypothesis papers, source rights, blind tests and PR backlog.


## Proposed EXP-0022 — C-1 context model (2026-11-12; DRAFT, NOT INTEGRATED)

**Status:** Experimental code and an independently rerun transcription-source SHA-256 check exist only in a review branch. C-1A clarity (79/135 artificial sense markers) and C-1B economy (34/135) passed their synthetic reader controls; both have gross word-length/ending-frequency mismatches versus the ZL3b-n f4r witness. This is not a Voynich translation, an A-13 self-copy reproduction, or an integrated new decipherment gate.

**Source:** The user's previously supplied ZL3b-n v3b file was hashed independently in the local computation (SHA-256 bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc); external origin-file identity and per-artifact redistribution rights remain unverified. The source file was not committed. Primary f4r: 13 nonempty lines / 54 conservative tokens. An exploratory post-protocol full-file pass covered 226 folio identifiers / 5,039 nonempty lines / 31,531 tokens under this distinct parser; not the EXP-0015 parser. Within-line permutation p-values are exploratory, not predeclared confirmation.

**Progress denominators unchanged for integrated research:** owner-canonical SRC-0007 canvas IDs inventoried **213/213 = 100%** `██████████`, independently accepted decipherment gates **0/5 = 0%** `░░░░░░░░░░`. None of these percentages estimates decipherment probability. **Workflow:** proposed EXP-0022 WATCHING for review; hypothesis validity UNKNOWN. **Blockers:** independent alternate transcription, generation-model calibration without data leakage, source redistribution rights, PR collision reconciliation. **Next:** independently preregister matched baselines and owner-review the branch; no merge implied.

### EXP-0022 follow-up — prefix-controlled suffix/context test (2026-11-13, proposed, NOT INTEGRATED)
Pure-Python five-fold folio-heldout comparison on previously user-supplied, locally hash-verified ZL3b-n v3b: **26,611 eligible target words** across 225 eligible IVTFF folio identifiers. After controlling target prefix3, length bin and first/middle/last position, left+right neighboring suffix classes add **+0.01294245 nats/target** (5/5 fold gains positive; 500-folio-bootstrap 95% interval [+0.01032,+0.01546]). 199 exploratory permutation controls within heldout folio×length-bin×line-position yield **p=0.005**. Original protocol separately frozen before this calculation. This is a statistical *text-context* result, not a semantic or C-1A/C-1B distinction, and overlaps the broader dependency family already tested in unmerged PR #26. Source already examined in earlier analyses; no new independent original manuscript witness. **Status: VERIFIED in bounded local transcription/parser scope; operational WATCHING pending PR #36 review.** All five decipherment gates remain unmet. **Integrated progress remains 213/213 owner-snapshot canvas IDs inventoried (100%) and 0/5 gates satisfied (0%)**. Blockers: alternative independent transcription witness, controls for line composition/scribe/section, rights and PR-file reconciliation. Next: fair model comparison without semantic overclaim.
