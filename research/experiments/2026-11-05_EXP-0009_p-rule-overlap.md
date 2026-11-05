# EXP-0009 — Targeted P-rule overlap test (2026-11-05)

Question: Are seven selected published P-rule predicates pairwise exclusive on eight deliberately chosen input tokens?

Source: Franke, P-01 to P-20 formal rule table v1.1, 2026-10-04, https://celler-presse.de/forschung/dokument/das-formale-maschinenlesbare-regelwerk-p-01-bis-p-20/ (existing SRC-0011). Worked example: existing SRC-0012.

Independently executed JavaScript regex and exact lookup predicates: P-02 starts qo; P-03 equals y/kor/ol; P-09 equals ar/ataiin/aiin/daiin; P-12 ends ol/ory/edy; P-14 equals iin/aiin/chol; P-17 equals shol/otch; P-19 equals olsh/rorain. All matching predicates were enumerated without short-circuiting.

Results:
- shol: P-12, P-17
- aiin: P-09, P-14
- qokedy: P-02, P-12
- chol: P-12, P-14
- otch: P-17
- rorain: P-19
- ol: P-03, P-12
- shory: P-12

5/8 selected test cases exhibit overlap; this is NOT an estimate of manuscript prevalence or statistical significance. In particular P-09 neutralizes aiin while P-14 classifies it as a vessel target. P-12 maps shol to qokedy while P-17 assigns catalysis status. These predicates are not pairwise exclusive (VERIFIED within stated scope). The author did NOT necessarily claim exclusivity; a defined priority, pipeline or multi-output contract could resolve these intersections. Complete decoder behavior remains UNKNOWN.

Alternative hypotheses: ordered first match; multi-label outputs; stages; exceptions. No decoder source code or UI execution, no manuscript images, corpus or semantic evaluation. No claim of historical decipherment or actual decoder nondeterminism.

Reproduction: test each listed token against every listed predicate; retain every matching rule ID. Next: freeze complete parser and compare outputs for shol, aiin, chol and ol with a published rule-precedence contract.
