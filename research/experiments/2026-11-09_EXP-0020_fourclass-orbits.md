# EXP-0020 four-class synthetic reachability preflight (2026-11-09)

## Scope and question
Exploratory mathematical counterexample, **not** an MS 408 corpus experiment. Does the combined row-permutation and column-permutation move family, which connects all 12 order-3 Latin squares in the earlier EXP-0020 preflight, necessarily connect a four-class fixed-margin state space?

Prediction to falsify: all order-4 Latin squares are connected by row and column swaps. Strong counterhypothesis: multiple disconnected orbits exist even when both row and absolute-position class counts are fixed.

## Frozen test specification
Enumerate all 4x4 arrays whose rows are permutations of 0,1,2,3 and whose columns each contain 0,1,2,3 once. Such arrays all have identical row class multisets and position (column) class counts. Build an undirected graph: an edge swaps any pair of entire rows or any pair of entire columns. These moves preserve both margins. Enumerate connected components exactly. Positive control: order-3 Latin squares are connected under combined row/column permutations (12 states); negative control: 2x2 checkerboard moves have zero edges on order-3 Latin squares. No random draws, no p-values, no held-out folios: these are exhaustive finite synthetic cases.

## Independent reproducibility (Python standard library only)
```python
from itertools import permutations, product
from collections import Counter

def latin(n):
    p = list(permutations(range(n)))
    return {rows for rows in product(p, repeat=n)
            if all(len({rows[r][c] for r in range(n)}) == n
                   for c in range(n))}

def orbit_sizes(n):
    unseen = latin(n)
    sizes = []
    while unseen:
        seed = unseen.pop()
        stack = [seed]
        count = 0
        while stack:
            a = stack.pop()
            count += 1
            for i in range(n):
                for j in range(i+1, n):
                    b = list(a)
                    b[i], b[j] = b[j], b[i]
                    b = tuple(b)
                    if b in unseen:
                        unseen.remove(b); stack.append(b)
                    b = tuple(tuple(row[j] if c == i else
                                    row[i] if c == j else row[c]
                                    for c in range(n)) for row in a)
                    if b in unseen:
                        unseen.remove(b); stack.append(b)
        sizes.append(count)
    return Counter(sizes)
assert orbit_sizes(3) == Counter({12: 1})
assert orbit_sizes(4) == Counter({144: 4})
print(orbit_sizes(3), orbit_sizes(4))
```

## Observations and falsification
**VERIFIED (synthetic scope):** exactly 576 order-4 Latin squares, separated into four connected components of 144 states each by combined row/column permutations. The earlier order-3 positive control is one component of 12. Thus the universal connectivity prediction is **CONTRADICTED** even after adding both whole-row and whole-column swaps. This does **not** establish whether more general alternating cycles connect the four components or whether a real Voynich four-class table has this structure.

## Interpretation boundaries
The arrays are synthetic classes, not manuscript images, visible glyphs, EVA/IVTFF readings, tokens or observed frequencies. No linguistic, coded, nonlinguistic or mixed origin hypothesis is selected or rejected. No held-out material, no CV Markov scores, no convergence test and no statistical significance. The canonical SRC-0007 owner-provided Yale snapshot is not independently live authenticated; no live manifest request was made. The rights status of full transcription ingestion remains separate and unresolved.

## Decision / next step
EXP-0020 remains **BLOCKED** for inferential use. Test margin-preserving alternating-cycle moves on an independently pinned *real* four-class line/position table; first enumerate small reachable subspaces and prove connectivity or explicitly diagnose components before any Markov-chain significance test. No new decipherment gate passed.
