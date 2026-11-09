# EXP-0020 directed-edge and sampler audit (2026-11-09)

**Scope:** independent standard-library rerun of the exact Python snippet in PR #30, `research/experiments/2026-11-09_EXP-0020_three-row-cycles.md`. Synthetic four-symbol 4×4 Latin squares only. No manuscript transcription, new source authentication, or inference.

## Question and falsifiable prediction
Does the move graph documented as 9,216 directed edges actually have reciprocal edges, as implied by the report's statement that inverse rotations are themselves allowed? H1: every edge i→j has j→i. Strong alternative H0: one or more directed edges lack a direct reverse move. Rejection: exhibit a nonreciprocal edge and exhaustively count all such edges. The original 576-state enumeration is a positive reproduction control; whole-row two-way exchanges are a negative control for detecting a false asymmetry.

## Reproduction
Execute the **unchanged** code block in the PR #30 report (Python standard library only), then append:

```python
from collections import Counter
degrees = Counter(map(len, adj))
nonreciprocal = [(i,j) for i, neighbors in enumerate(adj)
                 for j in neighbors if i not in adj[j]]
print(len(S), sum(map(len,adj)), sorted(degrees.items()))
print(len(nonreciprocal), nonreciprocal[:1])
```

## Independent observation
`576` states, `9216` directed edges, out-degree distribution `[(14,432),(22,144)]`; **2,304 directed edges lack a direct reverse**. First witness `(0,397)` under the source enumeration: state 0 rows `(0123),(1032),(2301),(3210)`; state 397 rows `(2301),(1032),(3210),(0123)`. Thus the report's direct-inverse assertion is **CONTRADICTED** in its actual implemented move graph, even though its reported connectivity counts reproduce.

## Interpretation and limits
A forward-reachable directed graph does not by itself prove the transition kernel has a uniform stationary distribution. The documented snippet constructs an asymmetric directed graph; its 3-row rotation generator iterates only ascending 3-row combinations and one cyclic orientation. Inverse rotation edges are **not** all present. Variable out-degree (14 versus 22) also means uniform-neighbor proposals require a separate detailed-balance/stationarity audit, even if inverse moves are subsequently added. No stochastic sampler was executed, so no measured sampling bias or mixing time is claimed. No manuscript-level hypothesis changes.

**Evidence:** VERIFIED for the independent finite synthetic enumeration; CONTRADICTED for the assertion that every directed move has an allowed direct inverse; UNKNOWN for any future actual Markov kernel's stationary distribution. **Workflow:** ACTIVE for generator correction; BLOCKED for inferential deployment.

## Next
Explicitly include both cyclic orientations; verify reciprocal edges and connectedness; specify a self-loop/rejection or Metropolis-Hastings transition rule; prove/verify stationarity and aperiodicity on enumerated spaces. Then repeat on a real, rights-reviewed, SHA-pinned heterogeneous four-class table and assess independent-chain convergence before held-out folio inference.
