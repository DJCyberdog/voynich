# EXP-0017 — Full-corpus reproduction and permutation-output audit (2026-11-05)

## Question and precommitment
Do the owner-reported five-fold, folio-held-out four-class suffix Markov gains in EXP-0015 reproduce byte-for-byte and exceed the already preregistered within-folio and within-line order-shuffle nulls? This experiment does **not** test language, semantics, or decipherment. Prior preregistration: EXP-0015; this audit does not retroactively define a new confirmatory threshold.

## Inputs and provenance
Owner-uploaded ZL3b-n.txt, SHA-256 `bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc`, IVTFF EVA 2.0 M5, version 3b 2025-05-13; owner-uploaded `voynich_full_corpus_cv(1).py` and `voynich_full_corpus_results.json`. Local source bytes are **VERIFIED for this uploaded artifact**, not independently retrieved/authenticated from the origin server; attribution and rights remain artifact-scoped. No source corpus or third-party image copied into GitHub.

## Method
Original Python 3 baseline rerun locally using the uploaded input, and JSON structurally compared to the uploaded baseline: exact equality for every field, policy and fold. The previous run's `voynich_exp0017_results_final.json` was audited in this cycle: for each of three tokenization policies and two permutation families, 1,000 stored raw null gains were counted and their arithmetic mean independently recomputed with Python standard-library `statistics.mean`. The original audit verified the stored null arrays without rerunning their generator. A same-day continuation **subsequently independently executed** the composition-preserving generator using the owner's frozen input/parser, validated the per-block class count preservation, and obtained the same six 0/1000 exceedance conclusions. The more complete independent execution is documented below. Folio-held-out train/test assignment is preserved in baseline. Null tests shuffle class order, preserving the multiset within each folio or line, respectively.

## Observations (nats per transition)
| Policy | Observed | Folio null mean | Line null mean | Exceedances in each family |
|---|---:|---:|---:|---:|
| exclude | 0.0184408372 | 0.0057707803 | 0.011078995 | 0 / 1000 |
| join | 0.0182680248 | 0.005653853 | 0.010390422 | 0 / 1000 |
| split | 0.0168464198 | 0.004936300 | 0.009328956 | 0 / 1000 |

All six stored arrays contain exactly 1,000 values; the exceedance counts and stored one-sided p=(exceedances+1)/1001=0.000999000999 agree. This is a **Monte Carlo resolution bound**, not a proof of zero tail probability. Six related tests are not independent and no language-model selection claim follows. Different held-out units in f3r EXP-0014 explain why its negative pilot cannot be silently pooled with this full-corpus analysis.

## Falsification and controls
Prediction: the observed cross-validated advantage should exceed frequency-preserving randomized order. Positive control: the uploaded baseline reproduces exactly. Negative controls: within-folio and within-line shuffles; both yield smaller stored gains. Strongest alternative: position-dependent generation, line-boundary effects, editorial segmentation, or a nonlinguistic generative process can produce order dependence. Such alternatives are **not falsified** by these nulls. Null-generator source and independent execution have now been supplied and tested (same-day addendum); transcript-witness sensitivity, position-aware nulls and glyph-level verification remain open.

## Evidence assessment
**VERIFIED**: local uploaded-file hash, exact baseline JSON reproduction, six stored-array lengths/means/exceedance accounting. **DOCUMENTED**: owner-session permutation output and declared method. **INFERRED conditional on implementation**: order structure beyond these two shuffle families. **VERIFIED in same-day continuation**: independent permutation execution and blockwise class-frequency preservation. **UNKNOWN**: external origin byte identity, language, semantics, decipherment, physical glyph reading. No acceptance gate passed (0/5).

## Next
Independent generator execution and code archival have been completed in the same-day continuation. Next compare independent transcription witnesses and preregister stronger position-preserving nulls. Do not interpret the six tests as six independent discoveries.


## Same-day independent permutation execution (additional verification; same EXP-0017)

This supplements rather than duplicates the initial stored-array audit. The owner-supplied ZL3b-n v3b was locally SHA-256 checked: bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc. Original Python evaluator SHA-256: 7acf5cb70b6197549d71cd2f1b91bda3a72d1c7885d63db76522454083017e89. Re-executing the original evaluator produced **exact JSON value equality** with the owner-uploaded results, including all five folds under all comma policies. An independent NumPy sufficient-statistics scorer reproduced all original average losses/gains within 1e-12.

An independently executed permutation evaluator (repo: research/scripts/exp0017_permutation_nulls.py) ran deterministic SplitMix64 Fisher–Yates with initial state 150377 and **1,000 permutations in each of six policy/null cells**. Folio and line folds remained fixed (seed 377). Each randomized sample retained the exact four-class counts within its respective folio or line; positive unshuffled baseline verified, frequency preservation controls verified for all 226 folio blocks and 5,109/5,146/5,149 nonempty line blocks. Raw null draws are available in the analysis artifact (SHA-256 81c5fc9997f7429a71cee772194c966b4ba4d335c8cf98a912ef74f05c3abd68); a machine-readable numerical summary is committed at research/results/2026-11-05_EXP-0017_null_summary.json. No large transcription or images copied.

| Policy | Observed | Folio mean / 2.5–97.5% | Folio >= observed / p | Line mean / 2.5–97.5% | Line >= observed / p |
|---|---:|---|---|---|---|
| Exclude (primary) | 0.0184408372 | 0.0057707803 [0.0044405536, 0.0072852064] | 0/1000, **0.000999** | 0.0110789954 [0.0095031072, 0.0128286769] | 0/1000, **0.000999** |
| Join | 0.0182680248 | 0.0056538526 [0.0043912978, 0.0070535259] | 0/1000, **0.000999** | 0.0103904215 [0.0089096499, 0.0119518124] | 0/1000, **0.000999** |
| Split | 0.0168464198 | 0.0049363004 [0.0038370772, 0.0060704879] | 0/1000, **0.000999** | 0.0093289558 [0.0079631147, 0.0106577567] | 0/1000, **0.000999** |

**Updated finding:** VERIFIED that original suffix-class order has held-out predictive information greater than either specified frequency-preserving exchangeability null on this frozen source/parser. HYP-0017 conditional exchangeability is CONTRADICTED. This evidence does **not** decide whether the mechanism is linguistic, cryptographic, diagrammatic, editorial or nonlinguistic. Within-line permutations also alter positional profiles; a position- and section-conditioned null is the next important falsifier. The six tests share source data/folds and are not independent manuscripts. The p-values are Monte Carlo resolutions, not exact probability zero. All five decipherment gates remain unmet (0/5).

Reproduce (with independently rights-reviewed source ZL3b-n.txt; installed NumPy and Numba):

~~~bash
python research/scripts/voynich_full_corpus_cv_owner.py --input ZL3b-n.txt --output baseline_rerun.json
python research/scripts/exp0017_permutation_nulls.py --input ZL3b-n.txt --original-cv research/scripts/voynich_full_corpus_cv_owner.py --baseline-json research/results/2026-11-05_EXP-0015_owner_baseline.json --output exp0017_all_draws.json --permutations 1000 --seed 150377
~~~

Input identity is verified for the owner's upload, not independently attested live at the external origin. Rights for redistributing original transcript not considered established. Owner-canonical Yale manifest D-0005 remains unchanged.
