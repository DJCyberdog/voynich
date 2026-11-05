# EXP-0015 — Full-transcription baseline and preregistered permutation follow-up

Date: 2026-11-05. Scope: independently designed four-suffix-class baseline; **not** an execution of Franke's decoder or VGM-377 implementation. This record documents user-executed Python output and a **future** test plan. EXP-0014's single-folio result must not be generalized.

## Input provenance and run configuration

The owner supplied complete PowerShell stdout from `python .\voynich_full_corpus_cv.py --input .\ZL3b-n.txt` (Python 3.13 on Windows). The program reported input SHA-256 `bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc`, IVTFF header `#=IVTFF Eva- 2.0 M 5`, `# Version 3b of 13/05/2025`, seed 377, Laplace/Dirichlet alpha 0.5, 5 shuffled folio-held-out folds. These are **owner-reported machine results** (DOCUMENTED), not independently re-run from authenticated bytes here. Exact script bytes and data file have not been committed or independently verified; the hash is a recorded identity claim, not an external authenticity certification.

The baseline maps suffixes ORY, EDY, OL, otherwise OTHER, keeps within-line adjacent-token transitions, compares unigram against first-order Markov predictive log loss (natural log). It uses three IVTFF uncertain-comma policies: exclude comma-containing segments, join across commas, or split at commas. It accepts only lowercase ASCII token strings. All three policies use the same folio assignment seed, but may produce different transition counts.

## User-reported whole-file results

| Comma policy | Folios | Lines matched | Accepted tokens | Transitions | Unigram loss | Markov loss | Markov gain (nats/transition) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Exclude | 226 | 5225 | 32147 | 27038 | 0.6793626773 | 0.6609218402 | +0.0184408372 |
| Join | 226 | 5225 | 34415 | 29269 | 0.6735264211 | 0.6552583962 | +0.0182680248 |
| Split | 226 | 5225 | 37105 | 31956 | 0.6646246319 | 0.6477782121 | +0.0168464198 |

Per-fold Markov gains, in fold order 1–5:
- Exclude: 0.02240418296, 0.00451524278, 0.01704937227, 0.02496645826, 0.02574419467
- Join: 0.02219085135, 0.00534955871, 0.01768143470, 0.02340278814, 0.02473610292
- Split: 0.02073733251, 0.00547177167, 0.01650776049, 0.01896186825, 0.02408640852

**Interpretation:** all 15 reported fold-policy cells show positive gain, contrasting with the previous f3r-only pilot. This supports predictive usefulness of class order under this baseline and sampling; it is not a medical-semantic result, not a whole-manuscript glyph audit, and not a matched replication of the author's 176-folio experiment. The 226 figure is regex-matched folio identifiers in this transcription, not a physical leaf count. Five folds are correlated, not independent manuscripts. No permutation p value or confidence interval is yet available.

## EXP-0015 preregistered next experiment — NOT EXECUTED

**Question:** Is the observed class-order gain greater than expected under a frequency-preserving, meaning-free random-order control?

**Primary dataset:** SHA-256-pinned ZL3b-n v3b above; the `exclude` uncertain-comma policy is primary; `join` and `split` are sensitivity analyses. Keep all folio IDs, line lengths, folds (seed 377), 4-class mapping and alpha=0.5 fixed. Archive source file and script after rights review; no silently altered normalization.

**Null H0:** Conditional on each folio's observed class composition and the preserved line lengths, token-class order is exchangeable. Shuffle all accepted class labels *within each folio* and reassign to original line slots; this destroys both within-line and across-line local order but preserves folio-level counts and line sizes. Note this null also changes per-line class composition, so a significant result does not uniquely isolate within-line order. A stricter secondary null shuffles *within each line*, preserving line class counts.

**Alternative H1:** The observed held-out Markov-minus-unigram predictive gain exceeds the null gains.

**Test:** 1,000 fixed-seed (e.g. 150377) independent permutations, rerun the identical 5-fold folio-held-out scoring for each; report observed gain, null mean, null 2.5/97.5 percentiles, and one-sided empirical p=(1+#{null gain >= observed gain})/1001. The 95% threshold is an exploratory decision rule, not a preregistered confirmatory claim until source and implementation are frozen. Report both null families separately; no p-value pooling across three token policies. Preserve individual fold outputs and execution metadata. An exact source-version and parser audit must precede any confirmatory status.

**Positive control:** Original unshuffled sequence should reproduce the owner-reported gains within numeric tolerance. **Negative controls:** Within-folio and within-line shuffles. **Rejection condition:** If original gain does not exceed the chosen null threshold, no claim of additional sequential dependence under that null. **Limitation:** Even a positive result demonstrates order-sensitive statistics only; no medical meaning, language identification, or decipherment follows.

## Subsequent work (not executed)

1. EXP-0016: predefine manuscript section/Currier-hand mapping with source provenance; stratified and cross-section held-out checks to test distribution shift.
2. EXP-0017: obtain frozen Franke parser and lexical semantic mapping; preregister blind held-out predictions and matched nonsemantic controls; evaluate coverage and specificity before looking at folio imagery.
3. Audit original parser: the current IVTFF line regex and ASCII-only filter can silently omit or transform evidence. Compare accepted line counts, unknown marks, token boundaries, and folio definitions against documented IVTFF semantics before publication.

Evidence level: DOCUMENTED owner-reported computational output; INFERRED narrow interpretation; UNKNOWN semantic significance.
