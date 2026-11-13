# K-series: Kushan-inspired methodological test register (2026-11-13)

Status: **DESIGN ONLY / NOT EXECUTED**. K-0001…K-0005 are methodological work packages, **not** five confirmed hypotheses, independent manuscript observations, or additions to the EXP register. A K item becomes a confirmatory EXP only after separate preregistration, source/rights clearance, deduplication and frozen holdout. No decipherment claim; all five acceptance gates remain unmet.

## Source and transfer limits

Bonmann, Halfmann, Korobzow & Bobomulloev (2023), *A partial decipherment of the unknown Kushan script*, Transactions of the Philological Society, DOI: https://doi.org/10.1111/1467-968X.12269 . **CLAIMED** as literature-method precedent pending direct full-text source audit in this repository. Historical Kushan decipherment benefited from multilingual inscriptions and identifiable royal names; Yale MS 408 has no comparably verified bilingual text or proper-name anchor. This is methodological analogy, **not** an assertion of shared script, language, date or mechanism. Subsequent work must independently verify exact source and scope before using it as evidence.

Data chain for all tests: manuscript image/region → visible strokes with uncertainty → allograph/ligature decisions → named/version-pinned transcription (EVA/IVTFF etc.) → segmentation → statistic → separately assessed interpretation. SRC-0007 is **owner-canonical** and SHA-256 pinned for the project, **not** independently live-authenticated at Yale. No scans or transcription corpora are copied into this register. Rights, witness versions, exact folio mappings and split integrity are gates.

## K-0001 — grapheme inventory and variant stability
**Question:** Do uncertainty-aware visual grapheme classes retain reproducible identity across folios, independently of EVA editorial conventions?
**Priority:** P0, prerequisite for all downstream tests. **Locus:** preselected folio/region images mapped through SRC-0007; exact regions to be fixed before execution.
**Prediction:** independently blinded annotators agree above a preregistered chance-corrected threshold on held-out regions and resulting classes survive alternative transcription conventions.
**Strong alternative:** apparent classes reflect scribal allographs, ligatures, image quality or EVA choices.
**Positive control:** duplicate image regions with blinded relabeling. **Negative:** independently selected ambiguous/poor-quality strokes. **Null:** chance agreement preserving annotator class frequencies. **Holdout:** disjoint folios and scribal/section strata, frozen in advance.
**Falsification:** below-threshold held-out agreement or unstable mapping across witnesses rejects the *specific* class scheme, not the existence of writing. **Status:** UNKNOWN / BLOCKED (image annotation, rights and sampling protocol absent). Overlaps transcription-policy work; do not duplicate existing glyph audit.

## K-0002 — positional environment prediction
**Question:** Do immediate glyph neighbors and token/line positions predict unseen glyphs beyond copy and positional baselines?
**Priority:** P0; directly tests manuscript-linked generalization. **Locus:** version-pinned IVTFF folio-line-token-glyph coordinates, no semantic labels.
**Prediction:** frozen conditional model outperforms preregistered frequency-only, token-position, line-position and local-copy baselines on unseen folios under identical scoring and data budget.
**Strong alternative:** local copying, layout and transcription conventions explain all predictive gains.
**Positive control:** a known synthetic dependency injected only into a separate control corpus. **Negative:** within-stratum permutations that destroy local adjacency while preserving relevant margins. **Null:** strongest admissible position/copy model, not only iid glyphs. **Holdout:** entire folios/quires, stratified by section/scribe; prevent near-duplicate leakage. Score held-out log loss and uncertainty, multiplicity corrected.
**Falsification:** no preregistered improvement over strongest null or instability across transcription witnesses. **Status:** UNKNOWN / WATCHING; overlaps EXP-0014/0015/0018 and Q-004; first audit those results before registering EXP. Not a claim that predictive success means language or cipher.

## K-0003 — repeated sequence as potential anchor
**Question:** Are recurrent glyph sequences associated with independently specified manuscript locations/visual categories beyond layout and frequency?
**Priority:** P1; weaker than bilingual Kushan proper-name anchors. **Locus:** frozen folio/region pairs and independent image annotations.
**Prediction:** anchor candidates chosen solely in training predict predefined held-out region categories better than layout-, section- and length-matched controls.
**Strong alternative:** topical/layout clustering or scribal templates generate the association without stable meaning.
**Positive control:** predeclared synthetic matched image/text labels. **Negative:** shuffled image-region labels within matched section/layout strata. **Null:** region and folio-class-only prediction. **Holdout:** disjoint folios and blinded image annotators.
**Falsification:** loss of predictive association in heldout or after layout matching. **Status:** UNKNOWN / BLOCKED; independent image labels and rights missing. No inferred proper names, recipes or translation.

## K-0004 — competing grapheme-to-sound / cipher models
**Question:** Can a compact *frozen* mapping model produce falsifiable unseen predictions without choosing a language from illustrative readings?
**Priority:** P1 conditional on K-0001/K-0002. **Locus:** explicit glyph units and versioned transcription.
**Prediction:** fixed mapping and complexity penalty yield preregistered held-out predictions robust to alternate witnesses and better than equally flexible nonlinguistic/copy baselines.
**Strong alternative:** unconstrained substitution/phonetic assignments overfit any sample; nonlanguage or mixed production also fits.
**Positive control:** known enciphered synthetic corpus with disclosed ground truth. **Negative:** shuffled mappings and random-label controls. **Null:** complexity-matched statistical, copy and hybrid models. **Holdout:** untouched folios/sections with model frozen before scoring.
**Falsification:** mappings require post-hoc retuning or fail heldout/alternate witness; retire only that mapping. **Status:** UNKNOWN / BLOCKED. No actual phonetic values assigned; does not satisfy decipherment gates.

## K-0005 — independent validation and cross-model adjudication
**Question:** Do any K-0001–K-0004 claims survive genuinely independent material, transcription and annotator choices?
**Priority:** P0 as release gate, executed only after candidate is frozen. **Locus:** separately held-out folios/sections, alternate version-pinned witnesses, blinded annotations.
**Prediction:** effect direction and predefined minimum magnitude persist under independent evaluation and survive controls.
**Strong alternative:** exploratory leakage, witness dependence, multiple testing, section confounding or selection effects.
**Positive control:** known synthetic signal with blind scorer. **Negative:** permuted/label-randomized and matched null datasets. **Null:** strongest preregistered baseline per claim. **Holdout:** sealed folio split plus independent annotator/transcription witness. **Falsification:** failed predeclared threshold or sensitivity tests blocks promotion to any decipherment gate.
**Status:** UNKNOWN / BLOCKED until upstream tests, provenance and rights are ready.

## Cross-model interpretation and deduplication

Keep natural-language, cipher, nonlanguage copying/generation and hybrid models alive; evidence for local predictability alone discriminates none of them. K is a **methodological queue** separate from A/O/W claim audits and EXP experiments. No numerical outcomes, frequencies or confidence percentages are asserted. Reuse rather than duplicate EXP-0014/0015/0018 and existing 40-claim queue. If a K work package overlaps an open PR, reconcile before any further registration. Any manuscript test requires a new explicit preregistration with exact folios, witnesses, licenses, parser version, thresholds, holdout, and expected outputs. No code installation, image ingestion, or third-party copying authorized here.
