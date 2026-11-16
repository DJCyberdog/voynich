# A-08 — Baseline-vs-variant source audit (2026-11-16)

**One bounded source-level research step, not a manuscript experiment.** Verified project main at start: `5ca7cfc9b43ec820d99292d87c784990e0266c64`; zero open PRs. No author code copied, installed or executed. This report extends, without double-counting, A-08 audits from 2026-11-09, 11-13 and 11-15.

## Question

Can the author's publicly shown `naibbe.py` and `naibbe_cv_vc_reuse.py` be treated as *the same default cipher generator* when comparing predicted Voynich-like statistics?

Primary author-controlled sources inspected as GitHub browser text on 2026-11-16 (no immutable external commit SHA yet pinned):
- Michael A. Greshko, [baseline `naibbe.py`](https://github.com/greshko/naibbe-cipher/blob/main/naibbe.py)
- Greshko, [variant `naibbe_cv_vc_reuse.py`](https://github.com/greshko/naibbe-cipher/blob/main/naibbe_cv_vc_reuse.py)
- Original study: *Cryptologia*, online 2025-11-26, DOI [10.1080/01611194.2025.2566408](https://doi.org/10.1080/01611194.2025.2566408).

## Result of static, source-only falsification

**Testable prediction:** If the two files have interchangeable default generators, their default plaintext segmentation and ciphertext generation/duplication controls must agree.

**DOCUMENTED:** Baseline `naibbe.py` uses `RESPACING=17`, assigning unigram or bigram by a random `RESPACING/36` draw; six named substitution tables with 52-card defaults 20/8/8/8/4/4; `SPACE_REMOVAL_RATE=0.03`. The variant also retains `RESPACING=17` and the same six tables/deck weights, but its actual default `RESPACING_MODE="cv"` selects consonant-vowel bigrams instead of invoking the random branch; its `ENABLE_SHORT_RANGE_REUSE=True` (attempt rate `0.004`, max lag 9) and `ENABLE_LONG_RANGE_REUSE=True` (attempt rate `0.006`, max lag 20000) add conditional ciphertext-token copying aligned to plaintext. Source comments explicitly label alternative random/CV/VC respacing modes. Both files visibly import `pandas` and reference `references/naibbe_tables.csv`.

**Narrow result:** Default-model interchangeability is **CONTRADICTED** by author-source parameter and mechanism differences. **INFERRED:** Any test that pools both as a single unmodified Naibbe model would confound segmentation and repetition mechanisms. This does **not** disprove the cipher class, the author's reported results or the legitimacy of the separately named variant.

**Strongest counterhypothesis:** Both are intentionally separate, valid variants of one cipher family; their deliberate naming and comments support that interpretation. No author error or misconduct inferred.

**Source-level controls:** Positive—six table IDs and 52-card weights match. Negative—the additional default CV segmentation and enabled short-/long-range copying occur in the variant. Null—equal default production mechanisms; contradicted within this inspected source scope. **Held-out:** none; no manuscript folios, ciphertext or plaintext scored.

## Not-yet-executed discriminatory test

Freeze author commit/blob SHAs, exact table CSV, per-file license, version-specific preprocessing and random seeds. Predeclare three comparison arms: baseline random-respacing Naibbe, CV/VC without reuse, CV/VC with reuse. Verify roundtrip on independently selected known Latin/Italian plaintexts as a positive control; use shuffled assignments and equal-tuning self-copy / natural-language-orthographic / hybrid generators as negatives. Fix independent source-rights-checked manuscript transcription and whole-folio/section heldout, folio/hand/line-layout stratification, score, effect size and multiplicity thresholds **before** test. IMPORTANT: author's table affixes were fitted using Voynich B; unspecified Voynich B folios are not a pristine holdout. Require a leakage audit, not nominal “held-out” labels.

**Blockers:** External source not immutably pinned; separate Zenodo rights unresolved (record not retrieved here); installation/execution of third-party code not authorized; underlying Yale imagery and third-party transcriptions not covered by author-source grants. SRC-0007 is owner-canonical but never independently live-Yale authenticated. No test executed, no p-values/translation invented.

**Status:** A-08 **DOCUMENTED** source differences; **INFERRED** control necessity; manuscript mechanism **UNKNOWN / WATCHING**, queue **SOURCE_REVIEWED / OPEN**. No new HYP/EXP/SRC, no A/W closure increase (3/40); indexed canonical Canvas IDs 213/213, not verified mapping; decipherment 0/5. **Next:** exact author-version freeze and rights-safe, executable separate-variant control test; if blocked, select another A/W candidate rather than repeating this audit.
