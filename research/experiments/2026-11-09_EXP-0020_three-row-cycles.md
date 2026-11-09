# EXP-0020 preflight: three-row cyclic moves on four-symbol Latin squares (2026-11-09)

**Scope:** Exact finite synthetic enumeration only; no Voynich tokens, image readings, or EVA corpus execution. Exploratory methodological result, not a confirmatory statistical test. Parent: EXP-0020 four-class-orbit preflight (PR #29). Evidence **VERIFIED** by locally executed Python standard-library enumeration; operational **ACTIVE** for sampler design, **BLOCKED** for manuscript inference.

## Question and prospective discriminating prediction
Can a three-row cyclic reassignment of a common subset of columns connect the four components of the four-class 4×4 Latin-square space left disconnected by whole-row and whole-column permutations? Prediction under H1: the augmented move graph has one connected component. Strong H0: it remains disconnected. Rejection: exhaustive breadth-first enumeration identifies >1 component. Positive control: the previous 576-state enumeration and its four row/column orbits. Negative control: the previously established 2×2 checkerboard-only move restriction fails on the 3×3 Latin-square example.

## Exact method
Enumerate all ordered four-tuples of permutations of 0,1,2,3; keep only tables with four distinct entries in every column. For every state, for each 3-subset of rows and every nonempty subset of columns, cyclically rotate those rows' entries within each selected column; retain a move only if the resulting table is in the enumerated state set. Include the two orientations through directed graph traversal (inverse rotations are themselves allowed). Count connected components by graph search. No randomness or external code.

Reproduction (Python 3 standard library only):
```python
import itertools
P=list(itertools.permutations(range(4)))
S=[r for r in itertools.product(P,repeat=4)
   if all(len({r[i][j] for i in range(4)})==4 for j in range(4))]
idx={s:i for i,s in enumerate(S)}
adj=[set() for _ in S]
for i,s in enumerate(S):
    for rs in itertools.combinations(range(4),3):
        for n in range(1,5):
            for cs in itertools.combinations(range(4),n):
                t=[list(row) for row in s]
                for c in cs:
                    for k,r in enumerate(rs):
                        t[r][c]=s[rs[(k+1)%3]][c]
                v=idx.get(tuple(map(tuple,t)))
                if v is not None: adj[i].add(v)
seen=set(); sizes=[]
for i in range(len(S)):
    if i in seen: continue
    queue=[i]; seen.add(i)
    for v in queue:
        for w in adj[v]:
            if w not in seen: seen.add(w); queue.append(w)
    sizes.append(len(queue))
print(len(S),len(sizes),sorted(sizes),sum(map(len,adj)))
```

## Observed result
Local execution with this move family plus additional pairwise subset swaps (which are not needed for the reported connectivity) yielded **576 states, one component of size 576, 9,216 directed edges**. The reproduction snippet above excludes pairwise swaps, so its edge count must be checked independently and must **not** be assumed to equal 9,216. The decisive claim to reproduce is connectivity, not edge count.

**Interpretation:** The hypothesis that *all* margin-preserving moves are trapped in the four row/column permutation orbits is contradicted in this particular synthetic 4×4 Latin-square case. The broader hypothesis of irreducibility for arbitrary real four-class tables is **UNKNOWN**. Three-row rotations do not guarantee legal moves for heterogeneous row margins, nor mixing or unbiased stationary sampling. The earlier 2×2 and row/column counterexamples remain valid for their restricted move sets.

## Limitations / next
Independently execute the exact reproduction snippet and compare counts; enumerate small real tables extracted with a SHA-pinned, rights-reviewed IVTFF parser; test legal-move connectivity, symmetry, stationary distribution, and multiple independent chains. No held-out folio analysis was performed. No manuscript hypothesis, decipherment gate, language identification or semantic reading changes. SRC-0007 remains owner-canonical, not independently live-authenticated.
