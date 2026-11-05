# Retrospective chat-research inventory — 2026-09-16 to 2026-10-05

**Imported 2026-11-05 from retrieved summaries of earlier user/assistant conversations.** This is a *historical lead register*, NOT an independently authenticated transcript, recovered source dataset, fresh experiment, manuscript observation, or confirmatory preregistration. Some numbers below are claims made by an earlier assistant, not independently rerun here. Do not silently upgrade CLAIMED to VERIFIED. The original run artifacts and complete message histories were not retrieved in this import. Avoid duplicating integrated EXP-0001–EXP-0008.

## September 16–17: q / qo, positional constraints and medieval abbreviations

- Observation reported in earlier discussion: EVA `q` / `qo-` appears frequently at the beginning of running-text tokens and less often in illustration labels. **Status: CLAIMED (earlier chat observation); frequency counts, transcription version, sampling and labels definition NOT recovered.** EVA is a transcription convention, not a proved phoneme or medieval Latin q.
- Competing interpretations: (A) language-like bound prefix/morpheme; (B) historical scribal abbreviation/function sign (candidate analogues *quod, que, qui, quia* discussed, NOT identified); (C) cipher/code marker; (D) positional surface-emission or nonlinguistic text-generation constraint; (E) mixed mechanisms. **All remain UNKNOWN as explanatory mechanisms.** Do not assert q=quod/que.
- Earlier discussion also considered whether line and word position or line endings encode structural functions analogous to punctuation. No quantitative demonstration recovered.
- Suggested discriminating tests: source/version-pinned EVA position counts; running text vs labels with matched sampling and explicit uncertainty; word-initial versus internal transition probabilities; compare language/grammar-transition models against surface-emission/positional nulls; preserve alternative transcription segmentation, folio and scribe strata; held-out folios and synthetic negative controls. **Prospective proposals, not tests run by this import.**

## September 17: reported Burchard abbreviation calibration

- Earlier assistant **reported** a Burchard experiment of **200 paired windows and 3,703 tokens per representation**, comparing synthetic contraction and historically grounded medieval abbreviation against Voynich-like positional/repetition properties.
- Reported outcome: real abbreviation moved H1/H2 *farther* from Voynich, positional binding *closer*, repetition unchanged; a reported predeclared summary was **1/4**, labeled `synthetic_contraction_historical_realism_weakened`; artificial `first2+α+last2` effect reportedly did not replicate.
- **Status: CLAIMED, historical conversation summary only.** No original scripts, corpus, pairing, metric definitions, source licenses, output tables, preregistration timestamp or numerical results independently recovered. The historical claim of preregistration is NOT treated as a new preregistered test. No statistical inference or acceptance threshold is imported as verified.
- **Strong alternative:** effects depend on window selection, tokenization, representation, abbreviation-expansion conventions, or unmatched genre and writer strata.
- **Falsification plan (not executed):** recover immutable original inputs, source provenance, exact H1/H2 metrics and preregistered rules; rerun paired comparison and null controls; assess robustness to transcript variation, token count and held-out writers.

## September 17: Nürnberg historical-scribal external control

- Earlier assistant reported a *planned* control using Nürnberg books 2–5 (1408–1423), described as 1,711 pages, 10 writers, with writer IDs and expanded/unexpanded abbreviations. A pilot was described as 180 texts / 505.8 kB.
- A previous run identifier **35164870476** reportedly failed before analysis after four HTTP-504 responses downloading `labels.zip` (~262 MB). **No Nürnberg outcome was obtained**; counts, dates and file sizes are unverified historical claims, not independently checked project data.
- Proposed role: writer-stratified medieval abbreviation comparison, separate diplomatic versus expanded forms, rights and provenance audit before any ingestion. Do not infer a Voynich match or mismatch from the failed run.

## October 5: earlier research architecture and objective

- User requested an autonomous, shared-repository, six-Hermes-agent investigation starting from scratch after an earlier Voynich GitHub project became unavailable; the intended long-term deliverable was a defensible English translation, **not** a presumption that one exists.
- An earlier `IDEA.md` was described as separating image/glyph -> transcription -> script/decipherment -> language -> English translation, with H001–H006, evidence metadata, controls and held-out passages. **Original IDEA.md and hypotheses H001–H006 have not been recovered; do not recreate their exact content or treat their IDs as the current HYP register.**
- These are historical workflow requirements, not additional scientific findings. Current repository governance, D-0005, source rights and `docs/DECIPHERMENT_CRITERIA.md` take precedence.

## Reconciliation and actionable next test

1. Existing project EXP-0001–EXP-0008 already covers codicology, owner-canonical manifest, Franke parser/transcript provenance and IVTFF comma semantics. This historical import adds **no duplicate experiment ID or independent source verification**.
2. Highest-value new prospective experiment: preregister whether EVA q/qo word-initial enrichment survives stratification by running-text versus labels, manuscript section, transcription witness and uncertain segmentation, and whether a simple positional emission null predicts it without semantic operators. Define effect size, baseline, sample split and rejection thresholds **before** data inspection.
3. Separately attempt recovery of the Burchard run artifacts and original preregistration; until then retain the numerical report only as historical CLAIMED.
4. No Yale live manifest authentication was attempted. The owner-provided SHA-256-pinned SRC-0007 is the canonical *working* IIIF source; it was not independently live authenticated. No images or transcription corpus are copied here.

**Operational status:** q/qo test WATCHING pending rights-reviewed version-pinned corpus; Burchard replication BLOCKED pending artifacts; Nürnberg control BLOCKED pending original data/rights. These operational labels are separate from evidential CLAIMED/UNKNOWN.
