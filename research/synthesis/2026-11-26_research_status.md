# Project Voynich — Research status, 26 November 2026

**Public research progress report · Working synthesis · Not peer reviewed**

Research baseline: [main at 2527585](https://github.com/DJCyberdog/voynich/tree/2527585fe2b83ed5c1f57c46451b907bad387170), integrated through EXP-0038g. EXP-0038g1 is reported separately as an unmerged result. The software-development branch is separate. This document synthesizes existing evidence; it does not register, rerun or adjudicate a new experiment.

## Executive summary

We investigate the structure and possible origin of the Voynich manuscript (Beinecke MS 408) through explicit, falsifiable tests of transcription-derived statistics and independently adjudicable image-text correspondences. Our most promising result is a reproducible incremental predictive benefit from compositional subword models across multiple transcription witnesses, including native STA1 as well as EVA. This supports statistical regularity in the tested representations, not a demonstrated linguistic morphology or a decipherment.

Higher-level lexical and sequential tests have yielded mixed results, with several preregistered predictions failing. No independently accepted semantic anchor or manuscript-level plaintext has been established. Natural-language, cipher, mechanical/nonlanguage and hybrid explanations remain open.

## Measurable progress

| Scope | Status |
|---|---|
| Experiment register | 49 unique entries, some containing grouped subexperiments; not 49 independent replications |
| Internal hypothesis register | 13 entries, narrow evidence statuses retained |
| External claim audit | 4/40 scoped completions (A-03, A-11, A-14, W-20); 36 open |
| Canonical digital canvas inventory | 213/213 unique IDs; not authenticated physical folios |
| Independent glyph pilot adjudication (deprioritized) | 0/20 |
| Decipherment gates | 0/5 |
| Guided ink proposal gate EXP-0038g | 59/74 passed; 60 required; NOT_MET |

The audit completion count includes methodological retirement and scoped source/claim dispositions, not a count of disproved theories. No overall decipherment percentage is defensible. See the [experiment register](../../memory/06_EXPERIMENT_REGISTER.jsonl), [internal hypothesis register](../../memory/03_HYPOTHESIS_REGISTER.jsonl), [research state](../../memory/02_RESEARCH_STATE.json) and [scoped audit disposition](../hypotheses/2026-11-24_s_tier_scoped_disposition.md).

## 1. Structural evidence

### Local organization and competing generators

Earlier suffix-class order experiments EXP-0017/0018 reject specific exchangeability nulls within the pinned EVA corpus, including controls for folio, line length and position. These are constrained statistical observations, not evidence of a particular language or generative mechanism. EXP-0027's joint context/position model fails its frozen incremental gate (0.001722 vs 0.005 nats/token). EXP-0028's fixed edit-copy augmentation passes its narrow primary criterion (+0.014087 nats/token), while its position-dependent extension fails. Alternative model specifications may reverse individual comparisons.

The unlimited-template learning-curve experiment EXP-0032c fails its late-growth criterion. More templates do not establish unlimited improvement or a historical template-based mechanism.

Sources: [EXP-0027](../experiments/2026-11-22_EXP-0027_report.md), [EXP-0028](../experiments/2026-11-22_EXP-0028_report.md), [EXP-0032c](../experiments/2026-11-24_EXP-0032c_report.md).

### Compositional prediction across transcriptions

| Test | OOV cohort | Incremental negative log-likelihood gain (nats/word) | Frozen gates |
|---|---:|---:|---|
| EXP-0035 EVA ZL | 984 | +0.292200 | 4/4 PASS |
| EXP-0036 EVA Takahashi refit | 1,166 | +0.295139 | 8/8 overall PASS |
| EXP-0036 EVA ZL to Takahashi transfer | 1,144 | +0.764650 | same experiment |
| EXP-0036a native STA1 ZL refit | 1,086 | +0.829385 | 12/12 overall PASS |
| EXP-0036a native STA1 GC refit | 1,379 | +0.774442 | same experiment |
| EXP-0036a native STA1 ZL to GC transfer | 1,301 | +7.296881 | same experiment |

Positive gain means lower negative log-likelihood for the fixed compositional augmentation relative to its specified comparator, conditional on observed word length. OOV means out-of-vocabulary under the respective protocol. Cross-witness transfer uses a common OOV cohort. The unusually large STA1 transfer increment is partly attributable to weak cross-witness baseline/code support; its absolute performance remains worse than the target-witness refit. The native STA1 prescan includes test-only code types for syntax support. Do not compare absolute likelihoods across alphabets or interpret these gains as decipherment progress. Witnesses represent the same manuscript and share editorial conventions, source images and repeatedly exposed root partitions; they are not independent manuscripts. No equal-complexity or exhaustive generator comparison was established.

Sources: [EXP-0035](../experiments/2026-11-24_EXP-0035_report.md), [EXP-0036](../experiments/2026-11-24_EXP-0036_report.md), [EXP-0036a native](../experiments/2026-11-24_EXP-0036a_native_report.md).

### Higher-level organization

EXP-0037g–j passes only 1/4 subtests, limiting claims about core/frame structure. EXP-0037k passes 5/12 gates: conditional bigram gain is negative in both native STA1 transfer directions (-0.168483 and -0.120626 nats/target); matched-shuffle residuals are small and one direction misses the permutation threshold. This does not demonstrate absence of syntax.

EXP-0037l–t passes 3/9 subtests overall. Distributional clustering agreement exceeds the specified length-stratified null (ARI 0.307165; alternate split 0.317540, both p=.005). The prepared sequences compress better than matched shuffled sequences (ZL +0.376587, GC +0.459322 bits/word), with both positive decisions retained in an alternate split. These are conditional descriptive signals; compression is not theoretical entropy, and cluster agreement does not establish grammatical classes. Other word-class/context, layout, folio and boundary tests fail their frozen criteria. Six test roots overlap between splits.

Sources: [EXP-0037g–j](../experiments/2026-11-24_EXP-0037_gj_report.md), [EXP-0037k](../experiments/2026-11-24_EXP-0037k_report.md), [EXP-0037l–t](../experiments/2026-11-24_EXP-0037_lt_report.md).

## 2. Visual and semantic evidence

The EXP-0038 editorial image-label proxy test fails (4/16 gates); editorial label classes are not independent visual ground truth. EXP-0038b conditional identifiability fails, EXP-0038c provides partial visual feature support, and EXP-0038d strict vessel attachment fails. EXP-0038e inventories 101 provisional botanical drawing candidates, with 74 provisionally unique attachments. Numeric support passes but is sensitive to a single candidate. EXP-0038f prepares a blind packet of 74 IDs and a pool of 113 candidate Lf loci (93 strict dual single-word forms, 59 exact reader-string agreements); **zero accepted region-to-locus matches**. These are not translations.

EXP-0038g evaluates 74 guided crops. 59 pass all frozen ink-readiness criteria; the minimum is 60. Preserve NOT_MET. Three synthetic sanity controls pass; 16 shifted crops also pass, but the shifted set is not certified blank. Components represent ink blobs, not verified glyphs.

**Pending integration — EXP-0038g1, [PR #92](https://github.com/DJCyberdog/voynich/pull/92).** Twelve synthetic non-writing parameter settings (rings, leaves, squares) pass every original gate; three of four synthetic writing settings pass. This is a counterexample to universal sufficiency of the ink heuristic as a writing detector, not a manuscript specificity estimate. Correlated synthetic settings are not independent samples. The original EXP-0038g result remains NOT_MET. Report: [pinned pending evidence](https://github.com/DJCyberdog/voynich/blob/ca91b70f054be6b524fb31e900cb9acdd64acac1/research/experiments/2026-11-25_EXP-0038g1_report.md).

Sources: [EXP-0038](../experiments/2026-11-24_EXP-0038_report.md), [b](../experiments/2026-11-25_EXP-0038b_report.md), [c](../experiments/2026-11-25_EXP-0038c_report.md), [d](../experiments/2026-11-25_EXP-0038d_report.md), [e](../experiments/2026-11-25_EXP-0038e_report.md), [f](../experiments/2026-11-25_EXP-0038f_report.md), [g](../experiments/2026-11-25_EXP-0038g_report.md). No restricted reviewer key or annotations are reproduced here.

## 3. What the evidence does and does not establish

- **Documented:** constrained order-associated effects, predictive subword gains across several transcription witnesses, and both successful and failed frozen tests.
- **Inferred:** the tested transcriptions contain recurring structure that is not fully explained by the particular simpler baselines.
- **Not established:** physical glyph inventory, actual word boundaries, linguistic morphology, grammatical syntax, original language, historical cipher, writing mechanism, botanical referents or semantic interpretation.
- **Reproducibility boundaries:** repeated byte-identical runs are computational repeatability, not independent external replication. Root partitions are not verified independent physical leaves and have been exposed. Source bytes and code are hash-pinned where specified; the owner-canonical manifest is not independently authenticated live. The raw source rights are not established for redistribution. Some public result files are aggregate extracts rather than the full local output.
- **External decoder audit:** EXP-0019 demonstrates that published aggregate totals alone do not uniquely recover the reported 176-folio membership. This is an identifiability limitation, not a falsification of the original author's actual selection procedure or decoder. Missing original artifacts remain a reproduction boundary.

## 4. Research infrastructure (separate from scientific results)

Voynich Research Studio v0.12.1 is under development on [PR #109](https://github.com/DJCyberdog/voynich/pull/109) and its parent stack, not a released product or merged main branch. It adds local proposal/classification and human exception review, explicit model selection and rollback, controlled cohort evaluation, local module execution, and guarded repository reporting. Most technical evidence is local/synthetic; native Windows/CUDA, real-manuscript recognition calibration, live GitHub acceptance and integrated release gates remain open. The actual historical EXP-0037k replay through the SDK reproduced the full original result hash, retaining NOT_MET. See [the pinned software milestone report](https://github.com/DJCyberdog/voynich/blob/23072e732c2154655a17b5c07a7237c6ecb6aa98/worker/VRS-123-125.md). No software milestone changes a scientific gate.

## 5. Next research requirements

1. Obtain independent blinded script/non-script and attachment annotations with certified positive and negative controls; retain all rejected candidates.
2. Establish independently verified physical region-to-transcription locus mappings, with ambiguous alternatives and disagreement accounting.
3. Freeze physical-leaf-disjoint calibration and holdout cohorts and genuinely prospective predictions before evaluation; account for cross-edition and near-duplicate leakage.
4. Test competing explanations on matched, prospectively defined controls and independently sourced comparison corpora rather than retuning on exposed roots.
5. Reproduce original external decoder artifacts when legitimately available and obtain external methodological scrutiny.

No new experiment is initiated by this report. The historical thresholds and negative findings remain in force. Independent evidence and criticism are welcome, particularly regarding transcription provenance, comparison models, leakage control and image-text mapping. Please cite the exact protocol and result rather than treating a software PASS or statistical association as a decipherment.

## How to cite this status report

Project Voynich. *Research status, 26 November 2026*. GitHub working research report, DJCyberdog/voynich. Cite the exact commit for a stable version. This is a project-authored synthesis, not a peer-reviewed publication or an independently verified discovery.
