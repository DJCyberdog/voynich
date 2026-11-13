# A-10 — Hauer/Kondrak primary-publication discrimination (2026-11-10)

**Cycle type:** ONE source-level audit; no Voynich data experiment, no semantic decode. Integrated main `eee6721615098918cce02bf76e4fdda26db60176` (EXP-0016), open Draft PRs #25–31 and #33–35. Existing A-10 queue entry is retained; no new HYP/EXP/SRC ID and no claim closure.

## Primary source and rights

Bradley Hauer and Grzegorz Kondrak (2016), *Decoding Anagrammed Texts Written in an Unknown Language and Script*, Transactions of the Association for Computational Linguistics **4**, pp. 75–86, DOI **10.1162/tacl_a_00084**, publisher/ACL original https://aclanthology.org/Q16-1006/ and PDF https://aclanthology.org/anthology-files/pdf/Q/Q16/Q16-1006.pdf . Published April 2016 (media publicity 2018 is NOT publication year). Publisher labels paper **CC BY 4.0**. Only paraphrase and minimal data facts, no source PDF/code copied into repo.

## Original study's actual units and results

* Section 3.4 Table 1: **97.1% top-1 language identification on synthetic substitution ciphers of UDHR samples from 380 languages** (trial-decipherment method), NOT 97.1% identification accuracy on Voynich.
* Sections 4.4 and Table 2: **93.8% mean word accuracy on 50 artificial anagrammed substitution ciphertexts** across five languages, NOT 93.8% correct Voynich translation.
* Section 5.1: Voynich analysis uses **43 Currier-B transcription pages**, 17,597 words / 95,465 characters, 35-symbol Currier transcription obtained from Reddy and Knight; this is NOT the project's ZL3b-n v3b EVA corpus. Its original precise 43-page folio IDs, exact bytes and source rights have not been independently pinned here.
* Section 5.2: Hebrew leads the **decomposition-pattern** similarity among tested languages (reported Bhattacharyya distance **0.020**, second Malay in Arabic script **0.048**); **letter-frequency** ranking instead favors Mazatec, and **trial-decipherment** rankings are sensitive to parameter changes (Hebrew and Esperanto near top). Thus it is NOT three convergent independent language identifications.
* Section 5.4: First ten pages of Currier-B subset, 3,726 words, produce no syntactically correct or semantically consistent decipherment according to authors. An illustrative attempted Hebrew reading of **the manuscript's first line** is separately presented; no independent cross-regime validation of applying Currier-B-trained evidence to first-folio text is shown. Native speaker judges example not fully coherent, and English gloss follows spelling corrections plus machine translation. Authors explicitly allow that their results could be **artifacts of anagramming and language models** (p. 85).
* Alphabet ordering/low alphagram distance is a **structural** observation, not evidence of actual letter permutation or Hebrew plaintext; a positional grammar, nonsemantic generator, hybrid, or alternative language with different word lengths can mimic such signatures.

## Narrow preregisterable falsification design (NOT EXECUTED)

**Question:** Is the Hebrew decomposition-pattern ranking robust to manuscript transcription witness and Currier regime under fixed equal-budget controls, rather than a byproduct of word lengths, segmentation and the flexible anagram search?

**Prediction:** Freeze original 43-page Currier-B sample and its language-model/corpus normalization, map equivalent loci independently to ZL3b-n v3b, then test unseen Currier-B folios and separately Currier-A folios; Hebrew should retain a preregistered rank and margin under source-witness perturbations if claimed inference generalizes. Fix exact rank threshold/margin using development only before any heldout inspection.

**Best counterhypothesis/null:** A language-neutral generator preserving **token-length and repeated-letter decomposition patterns**, plus non-Hebrew language models with equal training budgets, produces equally favorable rankings. **Positive control:** independent synthetic substitution+anagram text with known Hebrew plaintext and known non-Hebrew plaintext, run without training leakage. **Negative control:** matched-length synthetic or within-word character reshuffling preserving the relevant patterns; note this control is intentionally invariant for the decomposition-pattern score, so it diagnoses non-identifiability rather than a significant rejection. **Heldout:** previously unused folios segregated by Currier A/B and source witness, with no model-selection tuning on them. **Falsifier:** Hebrew advantage disappears under matched nulls or fails fixed heldout rank/margin, or independent decode fails to recover consistent syntax/semantics. This would refute the *specified predictive strength*, not categorically disprove Hebrew as a possible historical language.

**Prerequisite gates:** original 43-page folio inventory, exact source transcription bytes and legal access; compatible Currier↔EVA symbol/witness mapping; fixed normalization and candidate-language corpora; independent implementation or authorized software; non-overlapping heldout. No third-party code run, no images or transcription corpus copied, no Yale live manifest retry. D-0005 SRC-0007 is owner-canonical, not live-Yale-authenticated.

## Disposition

**DOCUMENTED:** bibliographic original, synthetic benchmarks, Voynich input regime, three nonconvergent methods, author caveats and absence of grammatical Voynich solution. **CLAIMED:** Hebrew/anagram as explanatory account. **INFERRED:** word-length/segmentation and language-model-selection confounding are testable alternatives. **UNKNOWN:** source-byte reproducibility, cross-witness ranking, heldout semantic validity. **Workflow:** A-10 **WATCHING / SOURCE_REVIEWED**, not TESTED, no acceptance gates passed (0/5), no new hypothesis, no broad rejection. Avoid duplicate source-review cycles; next A-10 only when original transcription mapping and equal-budget control corpora become available.
