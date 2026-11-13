# EXP-0022 (proposed) — C-1A/B context-composition vs MS 408 morphology
Date: 2026-11-12. Status: experimental report on an isolated branch; not integrated. No decipherment, translation or semantic reading of Voynich.

## Pre-observation freeze
Frozen protocol: research/experiments/2026-11-12_C1_context_frozen_protocol.md, pre-data commit 6e0fca75897be843af7d230f36b9ba285c3b48d4.
Frozen program: research/experiments/c1_context_model.py, commit b2280d11717bc167a03cab7eb675e67fc778179b. The full original source witness and selected f4r text had not been examined in this cycle at either freeze.
Version C1-2026-11-12-freeze-1; seed 421307; 25 fictional semantic stems. EN+DAK is ambiguous (animal-derived liquid LI versus animal in water SU); DAK+EN is a nonambiguous reverse form. C1A appends LI/SU if the intended sense's context vote advantage is under two, C1B if under one. 640 scenario design split, last 160 held out (no fitted coefficients). Writer and decoder share rules. Mechanical comparison copies/edits nearest-four words with frozen 70 percent mutation probability, also drawing on the same 25 artificial roots.

## Provenance and rights
Input is an existing user Library file ZL3b-n.txt, NOT a new authenticated fetch from the external origin. Original attribution René Zandbergen / EVMT, source URL https://www.voynich.nu/data/ZL3b-n.txt and overview https://www.voynich.nu/transcr.html . File header is IVTFF Eva- 2.0 M 5, version 3b of 13/05/2025. Local independent checksum: SHA-256 bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc; 411671 bytes, 8510 lines. This independently reproduces the earlier owner-reported digest from EXP-0015, but is NOT independent live verification that the online origin currently serves the same bytes. No large external transcription or Yale images committed; per-artifact rights review before redistribution remains open. Separate owner-canonical manifest SRC-0007 not reauthenticated.

The preregistered primary manuscript target was f4r. A provisional manual 13-line excerpt was compared with the identical loci in the recovered full user file: parsed tokens agree exactly. Primary f4r sample: 13 nonempty lines, 54 accepted tokens.

## Executed synthetic controls on held-out artificial scenarios
160 scenes, of which 135 use ambiguous ENDAK.
C1A: 79 markers / 135 = 58.52%; intact-context recovery 100%; recovery after shuffled contexts 74.07%.
C1B: 34 markers / 135 = 25.19%; intact-context recovery 100%; shuffled-context recovery 54.81%.
Self-tests PASS. The 100% is a built-in encoder/decoder consistency check, NOT predictive performance on Voynich. Negative context shuffle deliberately disrupts information.

## Descriptive surface checks — no language model fit or semantic label assignment
                                        C1A      C1B      mechanical  f4r       full ZL
tokens                                  1429     1429     1429        54        31531
mean token length                       3.5948   3.5318   2.9412      5.3333    5.2715
local previous-4 edit distance <= 1     0.1710   0.1710   0.7510      0.1220    0.1190
two most frequent final-bigrams share   0.2127   0.2260   0.1260      0.5370    0.3587
local previous-4 prefix-two recurrence  0.1584   0.1584   0.3042      0.3171    0.2797

The subsequent full-witness extension is explicitly exploratory, not a new preregistered confirmatory test. It parsed 226 folio identifiers, 5039 lines with at least one accepted word, 31531 accepted words. Its parser excludes comma-uncertain segments, digits, brackets/allographic uncertainty, markup and one-character groups; it does not reproduce EXP-0015's 5225 matched lines and differently defined 32147 accepted tokens. It provides stable evidence for this exact implementation/transcription policy only. The frozen C1 toy fails to reproduce basic Voynich word length and ending concentration, so those toy parameterizations are inadequate. The mechanical model grossly overproduces nearby one-edit variants. Neither is a matched-alphabet, matched-vocabulary likelihood model; no winning language hypothesis is identified.

## EXTRA exploratory posthoc permutation control (NOT pre-registered)
After f4r observation, a new, clearly labeled script c1_secondary_null.py was independently executed. It shuffles word order within each source line while retaining that line's tokens, boundaries and lengths; seed 425121. The diagnostic is previous-4 local edit distance <= 1.

f4r: observed 0.121951; 1000 shuffles null mean 0.116927; empirical upper-tail p = 0.794206.
all ZL parsed lines: observed 0.119017; 200 shuffles null mean 0.110716; empirical upper-tail p = 0.004975.

The all-file signal means extra local proximity only relative to this simple token-order exchangeability null, NOT relative to language, cipher, positional, scribal, section, tokenization, and hybrid controls. These p-values are posthoc exploratory, uncorrected for multiple looks; no confirmatory claim. One small f4r alone provides no evidence of excess.

## Classification, alternatives, and next entry
VERIFIED: synthetic self-tests, deterministic parser calculations on user-held exact bytes, SHA-256 match to previous claimed file digest (within this local file's scope).
DOCUMENTED: transcription source version/header/site attribution and prior owner report.
INFERRED: these unfitted toy generators are structurally mismatched; not a rejection of general constructed languages.
UNKNOWN: words' real meanings, whether manuscript has compositional morphology, historical writing process, all five decipherment gates.
Workflow: exploratory ACTIVE in this proposed EXP-0022 only. A-13 original self-citation generator is different, not tested or confirmed by this result.
Strongest alternatives: unknown natural language, cipher or altered orthography, position-conditioned nonsemantic generator, realistic self-copy, and hybrids.
Next: independently preregister a matched-length/suffix/lexicon-budget, folio-heldout comparison; audit ZL/GC independent witness and rights; avoid tuning artificial morphemes on manuscript and claiming confirmation.

Reproduce with Python stdlib, with the input file supplied separately:
python research/experiments/c1_context_model.py --self-test
python research/experiments/c1_context_model.py --input ZL3b-n.txt --folio f4r --expected-sha256 bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc
python research/experiments/c1_secondary_null.py --input ZL3b-n.txt --folio f4r --permutations 1000
python research/experiments/c1_secondary_null.py --input ZL3b-n.txt --permutations 200
No automation change; no Owner-authorized merge.
