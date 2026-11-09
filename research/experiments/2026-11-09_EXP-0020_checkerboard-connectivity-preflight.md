# EXP-0020 methodological preflight — 2026-11-09

## Scope and preregistered test
Question: Is the elementary two-row/two-position checkerboard exchange sufficient to reach every table preserving each row's class multiset and each absolute column's class totals? Prediction under universal-connectivity claim: every admissible fixed-margin table is connected by these moves. Strong counterhypothesis: some nontrivial fixed-margin tables have disconnected components. This is a **synthetic combinatorial falsification**, not a Voynich corpus test.

## Reproducible enumeration (no external packages)
Enumerate all permutations of [0,1,2] as possible rows of a 3×3 table; retain triples with each column containing all three classes. There are 12 tables (3×3 Latin squares). For each table and each pair of rows i<j and columns a<b, a checkerboard exchange is admissible iff T[i,a]=T[j,b], T[i,b]=T[j,a] and the two classes differ. This move preserves both individual row multisets and column totals.

Result independently enumerated in this cycle: **12 admissible tables; 12 have zero checkerboard neighbors**. Therefore the move graph has 12 singleton components. A 2×2 positive control [[0,1],[1,0]] has one admissible exchange. The 3×3 cyclic Latin square [[0,1,2],[1,2,0],[2,0,1]] is a negative control with none. The 3×3 result is a counterexample to *universal* irreducibility, not evidence that actual Voynich tables are disconnected.

## Interpretation and limitations
VERIFIED (synthetic enumeration): elementary checkerboard moves are not universally irreducible for >=3 classes. CONTRADICTED (restricted claim): universal connectivity of this move family. UNKNOWN: connectivity of any real four-class ZL3b-n table, mixing, actual Markov advantage, language/cipher/nonlanguage explanation. No source manuscript image, glyph, EVA reading, held-out corpus, or inferential p-value was examined. Four-class relevance: a four-class sampler cannot rely on a general proof of universal irreducibility for all class counts when a three-class counterexample exists; a four-class-specific test/proof remains required. No semantic or decipherment claim.

## Next test
Pin a real four-class table and line/position strata from the authorized source; enumerate feasible states for a tractable slice and compare graph components under 2×2 moves and candidate longer alternating cycles. Use multiple starts, negative and positive controls, then held-out folio-CV statistic only after verifying irreducibility and mixing. Keep exploratory selection separate from confirmatory held-out material.

## Repository provenance
Based on verified main c639d6ea52c784ce2f60c9e5143dde580c96fa17. PR #25→#26→#27 are stacked and overlap README/memory; this branch is independent and must not merge before reconciliation. Owner-canonical SRC-0007 is not independently live-Yale authenticated. No third-party code or raw corpus copied.


## Follow-up within EXP-0020: exploratory longer-move connectivity (2026-11-09)
Question: can margin-preserving moves beyond elementary 2x2 checkerboards connect the 12-state counterexample? This is an **exploratory post-hoc extension**, not a preregistered manuscript test. Fixed 3x3 Latin-square margins imply each row and each column contains each of three classes once. Therefore exchanging two entire rows, or two entire columns, preserves both margin families. Exhaustive state enumeration and undirected neighbor graph traversal yielded:

| Allowed moves | Connected-component sizes | Undirected edges |
|---|---|---:|
| Whole-row transpositions only | 6, 6 | 18 |
| Whole-column transpositions only | 6, 6 | 18 |
| Union of whole-row and whole-column transpositions | 12 | 36 |
| Elementary 2x2 checkerboards only (prior control) | 1 repeated 12 times | 0 |

Reproduction with Python standard library: enumerate all 6^3 ordered triples of permutations of (0,1,2), retain triples with each column sorted equal to (0,1,2); map each retained tuple to an integer vertex. For every vertex, enumerate all three pairwise row swaps and all three pairwise column swaps; retain only neighbors in the enumerated set; count connected components by breadth-first search and edges as half the sum of distinct neighbor degrees. Positive control: row/column swap maps every Latin square to another admissible Latin square. Negative control: 2x2 checkerboard-only graph remains edgeless. The two single-family graphs each split into two components; their union connects all twelve. These counts were calculated locally, not inferred from Voynich data.

**VERIFIED (synthetic, bounded):** combined whole-row and whole-column transpositions connect this particular 3x3 fixed-margin state space, despite failure of elementary checkerboards. **UNKNOWN:** whether such moves are admissible or sufficient on any actual four-class table. In general whole-row swaps require the two rows to have identical class multisets, and whole-column swaps require identical position-frequency vectors; arbitrary source rows/positions cannot be swapped. The result does not establish universal irreducibility, unbiased stationary sampling, mixing time, or any manuscript interpretation. Next: source-pinned real four-class slice, exact margins, complete feasible-state enumeration where tractable, and graph connectivity under genuinely admissible longer cycles. Do not promote this exploratory synthetic result to confirmatory evidence.
