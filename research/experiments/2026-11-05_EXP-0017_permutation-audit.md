# EXP-0017 — Full-corpus reproduction and permutation-output audit (2026-11-05)

## Question and precommitment
Do the owner-reported five-fold, folio-held-out four-class suffix Markov gains in EXP-0015 reproduce byte-for-byte and exceed the already preregistered within-folio and within-line order-shuffle nulls? This experiment does **not** test language, semantics, or decipherment. Prior preregistration: EXP-0015; this audit does not retroactively define a new confirmatory threshold.

## Inputs and provenance
Owner-uploaded ZL3b-n.txt, SHA-256 `bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc`, IVTFF EVA 2.0 M5, version 3b 2025-05-13; owner-uploaded `voynich_full_corpus_cv(1).py` and `voynich_full_corpus_results.json`. Local source bytes are **VERIFIED for this uploaded artifact**, not independently retrieved/authenticated from the origin server; attribution and rights remain artifact-scoped. No source corpus or third-party image copied into GitHub.

## Method
Original Python 3 baseline rerun locally using the uploaded input, and JSON structurally compared to the uploaded baseline: exact equality for every field, policy and fold. The previous run's `voynich_exp0017_results_final.json` was audited in this cycle: for each of three tokenization policies and two permutation families, 1,000 stored raw null gains were counted and their arithmetic mean independently recomputed with Python standard-library `statistics.mean`. The stored null-generator claims SplitMix64 / Numba Fisher-Yates; **this cycle did not independently rerun or inspect its implementation**. The permutation output is therefore a secondary, owner-session computation with independently checked internal summary, not a second independent Monte Carlo reproduction. Folio-held-out train/test assignment is preserved in baseline. Null tests shuffle class order, preserving the multiset within each folio or line, respectively.

## Observations (nats per transition)
| Policy | Observed | Folio null mean | Line null mean | Exceedances in each family |
|---|---:|---:|---:|---:|
| exclude | 0.0184408372 | 0.0057707803 | 0.011078995 | 0 / 1000 |
| join | 0.0182680248 | 0.005653853 | 0.010390422 | 0 / 1000 |
| split | 0.0168464198 | 0.004936300 | 0.009328956 | 0 / 1000 |

All six stored arrays contain exactly 1,000 values; the exceedance counts and stored one-sided p=(exceedances+1)/1001=0.000999000999 agree. This is a **Monte Carlo resolution bound**, not a proof of zero tail probability. Six related tests are not independent and no language-model selection claim follows. Different held-out units in f3r EXP-0014 explain why its negative pilot cannot be silently pooled with this full-corpus analysis.

## Falsification and controls
Prediction: the observed cross-validated advantage should exceed frequency-preserving randomized order. Positive control: the uploaded baseline reproduces exactly. Negative controls: within-folio and within-line shuffles; both yield smaller stored gains. Strongest alternative: position-dependent generation, line-boundary effects, editorial segmentation, or a nonlinguistic generative process can produce order dependence. Such alternatives are **not falsified** by these nulls. The null generator's source and independent execution, transcript-witness sensitivity and glyph-level verification remain open.

## Evidence assessment
**VERIFIED**: local uploaded-file hash, exact baseline JSON reproduction, six stored-array lengths/means/exceedance accounting. **DOCUMENTED**: owner-session permutation output and declared method. **INFERRED conditional on implementation**: order structure beyond these two shuffle families. **UNKNOWN**: independent permutation rerun, corpus origin byte identity, language, semantics, decipherment, physical glyph reading. No acceptance gate passed (0/5).

## Next
Freeze and publish a small independently reviewable permutation implementation (without corpus redistribution); rerun controls independently, then compare independent transcription witnesses and stronger position-preserving nulls. Do not interpret the six tests as six independent discoveries.
