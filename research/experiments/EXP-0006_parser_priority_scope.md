# EXP-0006 — Does published later model priority resolve the archived P-12/P-17 collision?

Date 2026-11-05. One bounded documentary specification-compatibility test. Not glyph-level, quantitative, semantic or decipherment test.

## Question and novelty
Can the explicit suffix-class priority in later G1.7 be used as the missing tie-breaker for the **archived functional decoding parser** P-01..P-20, particularly overlapping P-12 and P-17 matching `shol`? EXP-0005 documented this overlap but did not inspect the later model-family separation or the exact pinned input variant.

## Sources / immutable reference leads
- SRC-0011: October 4 2026 archived rule table v1.1, https://celler-presse.de/forschung/dokument/das-formale-maschinenlesbare-regelwerk-p-01-bis-p-20/ . P-12 matches `(ol|ory|edy)$` producing `qokedy`; P-17 exact lookup `[shol, otch]` producing catalysis status. Both match `shol`. No global tie-break found in the **inspected published table**.
- SRC-0012: archived worked f1r parsing v1.2, https://celler-presse.de/forschung/dokument/das-deterministische-parsing-protokoll-beispiel-folio-1r-zeile-1/ ; resolves that **particular example** in favour of P-12 (`shol` → `qokedy`), without specifying universal tie handling.
- SRC-0013: Franke, 'Methodische Präzisierung der Transkriptionsgrundlage ... ZL3b-n v3b als Referenzkorpus', v1.0, published 2026-10-05, https://celler-presse.de/forschung/dokument/methodische-praezisierung-der-transkriptionsgrundlage-des-functional-decoding-model-zl3b-n-v3b-als-referenzkorpus/ . Names **ZL3b-n version 3b of 2025-05-13** as reference for current FDM validation. Distinguishes manuscript glyphs, EVA transliteration convention, concrete transcript, derived FDM normal forms and semantic interpretation. Says older source forms not directly evidence for current reference.
- SRC-0014: Franke, 'Voynich Manuscript — Provisional Integrated Model G1.7: Scientific Interim Report', v1.0, published 2026-10-18, https://celler-presse.de/forschung/dokument/voynich-manuscript-provisional-integrated-model-g1-7-scientific-interim-report/ . Introduces a deterministic primary class K(w) priority **ORY > EDY > OL > OTHER**; states G1.7 orthographic class model and historical V54 folio model were developed separately and not validated as one integrated system. Semantics not confirmed.
- SRC-0015: Franke research project index, https://celler-presse.de/forschung/projekt/voynich-manuskript/ ; lists P-01..P-20 and its f1r worked example under **Archive/Earlier versions**, whereas ZL3b-n and G1.7 have separate current entries.

## Prespecified competing claims and falsification
- HYP-0006: The later *G1.7 suffix class precedence* fully and explicitly decides the **archived P-12/P-17 functional output conflict** for `shol`.
- Strongest alternative: same visible endings are represented in distinct model layers, and a specified P-parser precedence or multiple-output policy remains separately necessary; a later suffix class can still be useful as **new** orthographic classification but does not uniquely pick `qokedy` versus catalysis.
- Prediction: if HYP-0006 is valid, the later document must explicitly apply class priority to the P-rule IDs or provide a specified conversion from K(w) to the functional P-12/P-17 output with conflict resolution.
- Positive control: G1.7 **does** specify an unambiguous exclusive ORY/EDY/OL/OTHER *main class*. `shol` ends `ol`, thus K(`shol`) = OL by this later classification.
- Negative control: P-12 and P-17 concurrently apply to `shol` under the old table; an ending-only classification does not express their competing *functional* outputs.
- Null: a class-labeling transformation alone conveys no selection rule or medical meaning; no inference across model families unless a published bridge is demonstrated.
- Sampling: complete relevant short rule table and specified model architecture sections, no text corpus, no held-out folios; conceptual source-scope test, not confirmatory manuscript test.

## Direct observations, outcomes
The later G1.7 report gives the ordered suffix decision and explicitly warns that separate model paths may not be combined as though validated together. The October 5 reference-source clarification explicitly pins ZL3b-n v3b (2025-05-13); this materially improves the next independent transcript source choice. The October 4 P table still has the explicit `shol` overlap and the worked f1r example resolves only one token without stating general precedence. No examined later publication formally bridges G1.7 class precedence to P-12/P-17 outputs.

**CONTRADICTED (narrow claim):** The inspected G1.7 class-priority rule *by itself* resolves the P-12/P-17 **functional** collision. It does not: K(`shol`)=OL is compatible with both archived P-12 and P-17 matching. **DOCUMENTED:** the published priority and pinned transcription source. **UNKNOWN:** whether a complete unretrieved FDM implementation defines a stable P-rule precedence or output composition, and whether any individual f2v proposed derived reading succeeds.

No new corpus or image was copied; no executable third-party software installed; no authored translation. Next discriminating step: obtain an accessible ZL3b-n v3b source with checksum/rights and a frozen P-parser priority/multi-output contract. Compare f2v independently at raw, normalized, parsed and semantic layers; only then use held-out folios and nulls.
