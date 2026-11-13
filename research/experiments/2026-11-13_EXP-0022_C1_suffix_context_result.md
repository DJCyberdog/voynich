# EXP-0022 continuation — held-out residual suffix/context prediction

**Date:** 2026-11-13 (Europe/Berlin). **Status:** RESEARCH_COMPLETED within orthographic test scope, draft PR unmerged. Pre-observation test freeze: `research/experiments/2026-11-13_EXP-0022_C1_suffix_context_prereg.md`, commit `2cea658be7992e08ac23f8e90a74e3a0acb47d6a` **before executing the targeted calculation**. Earlier C1 descriptive/f4r experiments examined the same source witness, so this is not a fresh independent-manuscript confirmation.

## Nonduplicate question
Does the ending of a target EVA token depend predictively on the immediate two-sided word context **after controlling for the target's first three characters, length bin and first/middle/last line position**? C1 constructed language with optional context-driven sense markers predicts *some* contextual suffix regularity but never predicts that Voynich contains its invented DAK, EN, LI or SU meanings. EXP-0018 in unmerged PR #26 measured a position+previous-suffix effect but **did not control for the target prefix/body proxy or both neighbors jointly**. The current experiment extends the conditional observable; it does not independently replicate EXP-0018.

## Data and operational layers
- **Transcription:** owner-held exact `ZL3b-n.txt` IVTFF Eva 2.0 version 3b dated 2025-05-13, attributed to René Zandbergen/EVMT; SHA256 verified locally `bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc` (this exact source also used in EXP-0015/17/18). The hash verifies owner-held bytes, not live upstream bytes or physical MS 408 glyphs. No Yale IIIF live authentication attempted; owner SRC-0007 continues as canonical project snapshot only.
- Fixed conservative parser from `c1_context_model.py`: 226 IVTFF folio identifiers, 5039 nonempty parsed lines; excludes uncertain commas, markup and rejected tokens. Eligible targets require >=4 ASCII letters and at least one neighbor: **26,611 target tokens across 225 distinct eligible folio identifiers**. Folio IDs are not physical leaf counts.
- Five suffix-class outcomes: literal EVA ending `dy`, `ey`, `ol`, `in` or OTHER. These are NOT proven morphemes, grammar, or meanings. First three letters are used as a *body proxy*, not a validated stem.
- **Baseline B1:** training-only smoothed P(suffix class | target prefix3, target length bin, line position). Global Jeffreys pseudo-count 0.5, hierarchical prefix/backoff masses 20 and 20. **Context C2:** B1 plus preceding and succeeding token's suffix class (boundary sentinel allowed), pseudo-count backoff mass 30.
- Frozen folio-held-out 5-fold SHA-based partition; source transcript previously inspected in other experiments, no retuning on this measurement. Raw transcript not committed.

## Reproduced code outputs (actual execution)
- Pure Python standard library; script `research/experiments/c1_suffix_context_test.py`, input verified against exact SHA-256.
- Self-tests **PASS**. Positive artificial 5,500-example context-dependence control (90%-rule) yields mean C2-B1 gain **+0.1007482931 nats/target**, all five synthetic held-out folds positive. This verifies expected detector function, not Voynich semantics.
- Held-out real ZL data: **+0.01294245145 nats per eligible target** total C2 over B1, five folio-held-out fold gains: +0.01156179551 (n=6347), +0.00933094909 (5172), +0.01304051057 (4579), +0.01672763402 (5463), +0.01419279767 (5050).
- Folio bootstrap (500 fixed-seed samples), percentile 95% interval **[+0.01031656573, +0.01545918605] nats/target**, conditional on this witness, parser, model and sampling scheme.
- Negative permutation control: **199** fixed-seed shuffles of ordered (left,right) context pairs *between tokens of the same held-out folio, target length bin and line-position stratum*; 26,433/26,611 context assignments movable (99.331%). Baseline model untouched. Null mean gain **+0.00321524560**, 95th percentile +0.00464983971, maximum +0.00523497265. None exceeded observed: one-sided empirical **p=1/200=0.005**.
- Prespecified necessary signal threshold **PASSED**: gain >0.01, 5/5 positive folds, bootstrap lower bound >0, and observed >95th percentile of shuffled controls.
- Exact numeric machine-readable output `research/results/2026-11-13_EXP-0022_C1_suffix_context_heldout.json`. No original copyright-protected transcript text included.

## Interpretation and strongest counterhypotheses
**VERIFIED (bounded to the exact user-held transcription and parser):** target suffix classes have additional within-line **predictive** dependencies on immediate orthographic context after fixed target prefix/length/line-position controls, and exceed this specified contextual-shuffle null. Neither a decoded word, a semantic link, nor a causal explanation follows.

**DOCUMENTED:** source version, checksum, and prior related finding EXP-0018 in separate unmerged PR #26. **INFERRED:** original toy C1B motivation has a necessary *formal analogue* but neither the two variants C1A/C1B nor their semantic marker mechanisms can be distinguished by this test. **UNKNOWN:** actual manuscript glyph ambiguities, true word segmentation, interpretation of suffixes, language and historic origin; 0/5 decipherment acceptance gates.

**Strongest alternatives:** natural morphology and syntax, transformed natural language or cipher, mechanical repetition with neighboring dependency, line/section/scribe-conditioned word generation and hybrid models. The null conditioned on folio, word length and coarse line position **does not preserve exact manuscript section, writer, target-prefix/context joint distribution or individual-line composition**; a stronger matched control may explain the gain. Five heldout folds share the same transcription source, not five independent replications. The owner-held source was already examined in earlier C1 work, and all numeric thresholds are scoped to this analysis. There is no justification to label Voynich a lingua franca, secret language, or synthetic artlang.

## Next scientific gate
Do **one** independent witness sensitivity after provenance/rights review (ZL versus independently produced GC; not copied relatives), and/or compare against a **matched-parameter** nonsemantic suffix-context generator plus within-line composition and line-position-aware controls on untouched folios. Do not tune invented DAK/EN words to EVA endings and then back-infer meaning. Do not merge prior stacked PRs #25–31 or this PR without Owner authorization and memory collision reconciliation.

## Reproduce
Provide the same user-held file separately (not in GitHub); from repository root:

`python research/experiments/c1_suffix_context_test.py --input /path/to/ZL3b-n.txt --shuffles 199`

Machine results are in the JSON path above. No new hypotheses, source files, automations, or services installed.
