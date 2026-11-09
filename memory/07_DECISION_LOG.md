# Decisions

## 2026-11-05 D-0001 — repository-only provenance
First empty-repository README commit on main; subsequent changes require PRs. Prefer smaller material deltas to automatic volume.

## 2026-11-05 D-0002 — initial research priority
Start by separating material dating from inscription dating, then audit Yale image and transcription provenance. No glyphs independently measured.

## 2026-11-05 D-0003 — physical foliation vs digital identity
Yale pre-1600 catalog SRC-0006 documents folds, missing/unnumbered leaves. Preserve physical and digital identity. EXP-0002.

## 2026-11-05 D-0004 — user-provided manifest received
A user provided a hash-pinned IIIF snapshot, parsed in EXP-0003.

## 2026-11-05 D-0005 — owner accepts user manifest as canonical working reference
The user-supplied SRC-0007 is canonical for research mapping; routine live HTTP 403 attempts SATURATED. Provenance and rights claims remain distinguished.

## 2026-11-05 D-0006 — owner prioritizes broad hypothesis survey and severe fair testing of Eschede proposal
Owner asks to survey German/English/other Wikipedias, Voynich.net and to attack the 2026 Eschede decipherment proposal from every plausible direction, seeking to establish whether proposed explanations survive *genuine* attempted falsifications. This does not justify confirmation bias or pre-deciding a successful decipherment. Preliminary sources and proposed protocol documented in research/hypotheses/2026-11-05_landscape_eschede_protocol.md. No semantic claim yet elevated beyond CLAIMED; corpus verification and held-out evaluation pending. Avoid cycling back to URL-access concerns.

## 2026-11-05 D-0007 — distinguish reading validation from semantic criticism
EXP-0004 compares Franke 2v literal-word claims with the Currier C f2v.P.1–P.8 VIB witness. Source-level literal mismatch is documented, but not elevated to universal disproof without raw transcription/image and other witnesses. Next effort should seek best rescue interpretation (e.g., different EVA witness or segmentation), without overriding evidence. Prioritize literal image-linked provenance above speculative medical meaning.

## 2026-11-05 D-0008 — correct layer confusion in EXP-0004; refocus on parser reproducibility
Franke's published Oct 4 method correction (SRC-0010) says his parameter chains are **derived parser outputs**, not raw EVA. The previously observed Currier C mismatch remains a correct witness-level observation, but cannot be promoted to a refutation of generated system tokens. Worked f1r example SRC-0012 maps raw shol to qokedy. Parser table SRC-0011 has at least one overlapping match, shol triggering P-12 and P-17, for which precedence was not visible in the inspected table. EXP-0005 records this constrained concern, not an assertion of no solution. Ask for deterministic full trace then blind test. Owner's canonical manifest status unchanged; task unchanged.

## 2026-11-05 D-0009 — Keep archived P parser separate from later G1.7 morphology; pin FDM corpus
EXP-0006 verifies that G1.7's ORY>EDY>OL>OTHER priority classifies orthographic suffixes, not collisions between the archived P-12 qokedy and P-17 catalysis functional rules. Do not invent a cross-model bridge or assert missing code. Franke's October 5 methodology explicitly names ZL3b-n v3b (2025-05-13) as FDM reference. Only a version-pinned rights-checked transcript and complete P functional parser resolve the original f2v output question. Keep strongest alternative that a separate implementation may implement precedence or multiple outputs. Canonical owner-supplied Yale manifest unchanged; no task change.

## 2026-11-05 D-0010 — Correct f2v source-witness scope using the designated origin transcription
EXP-0007 directly observes `cheo,pchor` in ZL3b-n v3b f2v.1 (SRC-0016), contrary to generalizing the older VIB contiguous `cheopchor` witness. Treat comma as editorial notation pending primary IVTFF punctuation and image check; neither raw literal presence nor a medical interpretation is thereby proven at manuscript level. Origin rights statement SRC-0017 permits use with attribution but is not an image/font license; no corpus copied. Independent source-byte hash still pending, registry SHA is CLAIMED. Owner manifest and task unchanged.

## 2026-11-05 D-0011 — EXP-0008 referential-integrity review
Before merging PR #10, register HYP-0008 and SRC-0019/SRC-0020 explicitly. Certain-boundary inference contradicted by IVTFF 2.x normative comma definition; physical gap remains unknown. This is a documentation repair of EXP-0008, not an independent second manuscript experiment. No Yale live authentication or automation change.

## 2026-11-05 D-0012 — retrospective chat leads imported without evidence promotion
The owner requested integration of earlier Voynich chats. Retrieved September 16–17 and October 5 conversation summaries were archived in research/history/2026-11-05_prior-chat-voynich-inventory.md as CLAIMED historical leads, not primary manuscript observations or new preregistered experiments. The reported Burchard 200-window/3,703-token comparison and Nürnberg blocked control lack recovered original artifacts; q/qo word-initial and label distribution is a testable hypothesis, not an established frequency. Added RM-008; no new HYP/EXP/SRC identifiers or decoding claims. No Yale live authentication or automation change.

## 2026-11-05 D-0013 — EXP-0010
Synthetic P-06 ordering probe shows aiin lookup sensitivity; not proof of author decoder error. Owner manifest and automation unchanged. EXP-0009 remains prior overlap exploration.

## 2026-11-05 D-0014 — retrospective EXP-0013 register integrity
Audit of main 791023a71b17a01ba6969db9d9f8e8d591fcd5ac found EXP-0013 report integrated in PR #18 but absent from canonical hypothesis/experiment registers and project state. Register existing evidence without promoting it to manuscript observation or inventing a new experiment. Synthetic odd-run underdetermination remains scoped to published R1 prose; author implementation UNKNOWN. Canonical user-supplied SRC-0007 unchanged; independent live Yale authentication not performed; automation unchanged.

## 2026-11-05 D-0015 — owner-directed README progress reporting and automation amendment
Owner added an explicit requirement to the existing hourly `Voynich Autonomous Research` automation: update root README.md on material research deltas with dated integrated status, numerator/denominator-defined percentages, visible progress bars, evidence/workflow status, blockers, next steps and open-PR scope. Never fabricate a percentage of decipherment; do not generate commits for unchanged research. **Prompt change (exact appended block):**

> VERBINDLICHE OWNER-ANWEISUNG — README-FORTSCHRITT (2026-11-05): Aktualisiere bei jedem Forschungszyklus die README.md im Repository-Stammverzeichnis um den aktuellen integrierten Forschungsstand, eine gut lesbare Fortschrittsanzeige und Prozentwerte mit ausdrücklich definierten Nennern (z. B. überprüfte Entzifferungskriterien 0/5, geprüfte Canvas-Zuordnungen x/213). Trenne Fortschritt einzelner überprüfbarer Arbeitspakete strikt von einer nicht messbaren Gesamt-Entzifferungswahrscheinlichkeit; erfinde keine Prozente. Nenne Standdatum, Evidenz-/Workflowstatus, Blocker, nächste Schritte und PR-Status. Bei NO_CHANGE ohne veränderten integrierten Stand keine künstlichen README-Commits; prüfe die Aktualität und aktualisiere nur bei realem Delta. Änderungen ausschließlich via isoliertem Branch und PR, mit Konflikt-/Scope-Prüfung und autorisiertem Merge. Dokumentiere diese Aufgabenänderung mit alter und neuer Fassung bzw. exaktem Prompt-Diff und unverändertem stündlichen Zeitplan in memory/07_DECISION_LOG.md, sobald Repository-Schreibzugriff möglich ist. Die bestehende Aufgabe und alle anderen Anforderungen bleiben unverändert; keine anderen Automationen ändern.

Previous prompt = original full research prompt including D-0005 and **without** the quoted appended block; new prompt = previous prompt **plus** exactly the quoted block. Task ID `6aec6d9a7ef081919efadf866cb67de3`; schedule before/after `BEGIN:VEVENT\nDTSTART:20261105T130000\nRRULE:FREQ=HOURLY;INTERVAL=1\nEND:VEVENT` (Europe/Berlin); task remains enabled. No other automation modified. README metrics are scoped to owner-supplied snapshot and five acceptance gates; not a claim of decipherment or independently authenticated Yale source.

## 2026-11-05 D-0016 — reconcile already merged EXP-0014 and EXP-0015
After PRs #20 and #21 were merged, canonical memory remained at EXP-0013. Record their existing reports in experiment register, project state and roadmap, and update README without presenting an independent new corpus experiment. EXP-0014's f3r-only shuffled controls were nonsignificant; EXP-0015's full-file positive gains were owner-reported, with permutation nulls not yet executed. No new source authentication, translation, or manuscript image observation. D-0005 owner-canonical manifest policy unchanged.

## 2026-11-05 D-0017 — limited aggregate-count audit
EXP-0016 checks the necessary line-local adjacency identity on already merged EXP-0015 aggregates. Preserve distinction between VERIFIED arithmetic and DOCUMENTED owner-reported input. No new glyph, parser reproduction, permutation significance or semantic result. No changes to D-0005 or automations.


## 2026-11-09 D-0011 — EXP-0020 synthetic sampler preflight (draft)
On main c639d6ea52c784ce2f60c9e5143dde580c96fa17, a bounded independent enumeration found 12 three-class 3x3 Latin squares, all isolated under elementary 2x2 checkerboard moves, with a positive 2x2 AB/BA control. Universal irreducibility of this move family is false. Do not treat this as a real four-class corpus experiment or infer any manuscript meaning. Reconcile stacked PRs #25–#27 before merge; no automation change. The 2026-11-05 README-progress owner instruction remains in force; full historical automation prompt diff remains to be recorded when a verified old prompt is available, not invented here.


## 2026-11-09 D-0018 — EXP-0020 exploratory alternative move graph (draft)
Within existing PR #28, test longer margin-preserving whole-row/whole-column transpositions against the 3x3 Latin-square counterexample. Exact enumeration gives components 6+6 for either family separately and 12 connected when combined; this is a scoped synthetic constructive result, not evidence of four-class corpus irreducibility or decipherment. Keep EXP-0020 inferential BLOCKED, reconcile overlapping #25–#27 before any authorized merge, do not change automations, and do not promote unintegrated draft status to main.

## 2026-11-09 D-0019 — EXP-0020 four-class synthetic orbit falsification (draft)
A separately reproduced exhaustive order-4 Latin-square enumeration (576 states) has four 144-state connected components under whole-row/whole-column swaps. Order-3 positive control remains connected (12 states). Therefore do not infer universal irreducibility from the order-3 case or use the restricted sampler for corpus significance without a real-table connectivity audit. No manuscript, rights or decipherment claim; no changes to automations or owner-canonical SRC-0007. This draft is stacked on PR #28 and is not integrated. Report: research/experiments/2026-11-09_EXP-0020_fourclass-orbits.md.


## 2026-11-09 — EXP-0020 combined move-family preflight (draft)
Independently enumerated 576 synthetic four-class 4x4 Latin squares. Three-row cycles alone: 48 components; combined with legal pairwise subset swaps: one component. Documented in a stacked Draft PR based on #29; no main merge, no corpus inference. Owner README-progress instruction retained without changing the hourly automation; prior prompt unchanged and no other automation touched.

## 2026-11-09 D-0020 — require reciprocal EXP-0020 moves and stationary-kernel audit (draft)
Independent exhaustive rerun of PR #30 exposes 2,304 nonreciprocal directed edges among 9,216, despite the claim that inverse rotations are included. Do not deploy the move graph as a uniform sampler without explicit reverse orientations, reciprocal-edge tests and stationary/aperiodicity validation. This is a synthetic method correction, not manuscript inference. Preserve owner-canonical SRC-0007, 213/213 and 0/5 package denominators, hourly automation, and stacked PR review; no merges or automation changes.
