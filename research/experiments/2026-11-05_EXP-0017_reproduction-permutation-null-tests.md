# EXP-0017 — full-corpus reproduction and permutation nulls (2026-11-05)

## Scope and prior registration
**Question Q-006:** Are the five-fold folio-held-out four-suffix-class Markov improvements in EXP-0015 greater than two composition-preserving nulls? The full protocol (primary uncertain-comma policy exclude; join/split sensitivity; 1,000 permutations within folio and 1,000 within line per policy; seed 150377; fold seed 377; alpha 0.5; one-sided empirical p=(1+#(null>=observed))/1001) was recorded **before testing** in merged EXP-0015 PR #21. Hypotheses: exchangeability of class order conditional on folio composition and line lengths (first null), or conditional on each line's composition and length (stricter second null). Alternative: observed predictive advantage exceeds null draws.

Owner-supplied ZL3b-n v3b transcription (13 May 2025) and original Python evaluator were actually received, read and executed locally. Dataset SHA-256: **bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc**. Original evaluator SHA-256: **7acf5cb70b6197549d71cd2f1b91bda3a72d1c7885d63db76522454083017e89**. Owner-uploaded baseline JSON raw-byte SHA-256 **f80136b043747f526fc34cde45504e16114529a0f2e99f02ff65f247a8958776** (its repository archive has normalized line endings). Complete permutation results local JSON SHA-256 **81c5fc9997f7429a71cee772194c966b4ba4d335c8cf98a912ef74f05c3abd68**.

Re-running the exact original owner CV on uploaded corpus produced a **JSON-equal reproduction** of all totals and 15 fold-policy results. The independent vectorized evaluator agreed with the original loss calculations within 1e-12. Corpus: 5,225 matched lines and 226 distinct IVTFF folio identifiers (not physical parchment leaves); no-token lines 116/79/76 for exclude/join/split. The original manuscript's glyphs were not audited and direct live origin bytes were not authenticated.

## Controls and method
The evaluator imports the exact owner baseline script for original line and fold construction, but computes held-out likelihood via independently vectorized transition sufficient statistics. The **within-folio** control shuffles 4-class labels over all accepted token slots of each folio, keeping each folio's class frequencies and line lengths. The **within-line** control shuffles only each line, preserving each individual line's class counts. A separate positive/negative control checked preservation of every block's 4-class composition for all six policy/family combinations (226 folio blocks and 5,109/5,146/5,149 nonempty line blocks). The original unshuffled result was reproduced. There were 1,000 null draws per cell using explicit deterministic SplitMix64 Fisher–Yates, seed 150377; no new packages installed (installed NumPy 2.3.5 and Numba).

## Observations (nats per within-line token transition)
Each percentile interval below is from 1,000 null draws. One-sided empirical p and exceedance count are reported **separately** for each null/policy, never pooled.

| Comma policy | Observed Markov advantage | Folio null mean | Folio null 2.5–97.5% | Folio exceed / p | Line null mean | Line null 2.5–97.5% | Line exceed / p |
|---|---:|---:|---|---|---:|---|---|
| **Exclude (primary)** | **0.0184408372** | 0.0057707803 | [0.0044405536, 0.0072852064] | **0 / 0.000999** | 0.0110789954 | [0.0095031072, 0.0128286769] | **0 / 0.000999** |
| Join | **0.0182680248** | 0.0056538526 | [0.0043912978, 0.0070535259] | **0 / 0.000999** | 0.0103904215 | [0.0089096499, 0.0119518124] | **0 / 0.000999** |
| Split | **0.0168464198** | 0.0049363004 | [0.0038370772, 0.0060704879] | **0 / 0.000999** | 0.0093289558 | [0.0079631147, 0.0106577567] | **0 / 0.000999** |

**Finding:** Under the frozen local ZL3b-n v3b + exact owner's four-class parser and folio-held-out model, both frequency-preserving exchangeability nulls are CONTRADICTED. The reported gain is robust to these three alternative comma treatments. VERIFIED numerical reproduction and null sampling, conditional on identified bytes and code. This is **not** evidence of specific grammar, language, cipher, medical meaning, translation, or a successful decipherment. The Monte Carlo resolution 1/1001 does not assert theoretical p=0. Five folds and the three policies are correlated, not independent manuscripts or replications.

## Adversarial alternatives and limitations
The stricter within-line permutation also disrupts positional patterns (line-initial and line-final class profiles); order-sensitive results may reflect **position dependence** rather than a specific neighboring-token mechanism. Further falsification requires position/length/section-conditioned controls and a distinct transcription witness. The parser accepts only lowercase ASCII tokens, simplifies IVTFF editorial line/interruption notation and drops uncertain glyph tokens. Neither alternative transcription versions, original folio images, Currier/hand stratification, copyright of full transcription, nor Franke's separate semantic decoder were audited. The known original site attribution and rights explanation is SRC-0017. The full transcription was **not committed**; local uploader SHA does not independently verify live source provenance; Yale owner-canonical manifest remains unaltered under D-0005.

## Reproduction and next decision
Repository files: research/scripts/voynich_full_corpus_cv_owner.py (verbatim owner script), research/scripts/exp0017_permutation_nulls.py (executable permutation evaluator), research/results/2026-11-05_EXP-0015_owner_baseline.json (numeric owner baseline). With the separately rights-reviewed source file named ZL3b-n.txt and preinstalled NumPy/Numba:

~~~bash
python research/scripts/voynich_full_corpus_cv_owner.py --input ZL3b-n.txt --output rerun.json
python research/scripts/exp0017_permutation_nulls.py --input ZL3b-n.txt --original-cv research/scripts/voynich_full_corpus_cv_owner.py --baseline-json research/results/2026-11-05_EXP-0015_owner_baseline.json --output exp0017_all_draws.json --permutations 1000 --seed 150377
~~~

Evidence state: VERIFIED scoped computational results; DOCUMENTED user-uploaded text/header; UNKNOWN glyph concordance, external source authenticity, manuscript-level linguistic interpretation, decipherment acceptance gates (still **0/5**). Operational: this single bounded EXP-0017 cycle completed; RM-009 remains ACTIVE for *new preregistered* position-preserving controls, RM-005 remains SATURATED. Do not infer a global decipherment probability.
