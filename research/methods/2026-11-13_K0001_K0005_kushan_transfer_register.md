# K-series: Kushan-inspired methodological test register (2026-11-13)

Status: **DESIGN ONLY for confirmatory K-tests; K-0001 includes nonblind, limited source-image pilot inspection**. K-0001…K-0005 are methodological work packages, **not** five confirmed hypotheses, independent manuscript observations, or additions to the EXP register. A K item becomes a confirmatory EXP only after separate preregistration, source/rights clearance, deduplication and frozen holdout. No decipherment claim; all five acceptance gates remain unmet.

## Source and transfer limits

Bonmann, Halfmann, Korobzow & Bobomulloev (2023), *A partial decipherment of the unknown Kushan script*, Transactions of the Philological Society, DOI: https://doi.org/10.1111/1467-968X.12269 . **CLAIMED** as literature-method precedent pending direct full-text source audit in this repository. Historical Kushan decipherment benefited from multilingual inscriptions and identifiable royal names; Yale MS 408 has no comparably verified bilingual text or proper-name anchor. This is methodological analogy, **not** an assertion of shared script, language, date or mechanism. Subsequent work must independently verify exact source and scope before using it as evidence.

Data chain for all tests: manuscript image/region → visible strokes with uncertainty → allograph/ligature decisions → named/version-pinned transcription (EVA/IVTFF etc.) → segmentation → statistic → separately assessed interpretation. SRC-0007 is **owner-canonical** and SHA-256 pinned for the project, **not** independently live-authenticated at Yale. No scans or transcription corpora are copied into this register. Rights, witness versions, exact folio mappings and split integrity are gates.

## K-0001 — grapheme inventory and variant stability
**Question:** Do uncertainty-aware visual grapheme classes retain reproducible identity across folios, independently of EVA editorial conventions?
**Priority:** P0, prerequisite for all downstream tests. **Locus:** preselected folio/region images mapped through SRC-0007; exact regions to be fixed before execution.
**Prediction:** independently blinded annotators agree above a preregistered chance-corrected threshold on held-out regions and resulting classes survive alternative transcription conventions.
**Strong alternative:** apparent classes reflect scribal allographs, ligatures, image quality or EVA choices.
**Positive control:** duplicate image regions with blinded relabeling. **Negative:** independently selected ambiguous/poor-quality strokes. **Null:** chance agreement preserving annotator class frequencies. **Holdout:** disjoint folios and scribal/section strata, frozen in advance.
**Falsification:** below-threshold held-out agreement or unstable mapping across witnesses rejects the *specific* class scheme, not the existence of writing. **Status:** ACTIVE / EXPLORATORY_PILOT_DOCUMENTED / EXHAUSTIVE_GLYPH_INVENTORY_NOT_MET / CONFIRMATORY_NOT_RUN (independent image annotation, rights and full-region coverage absent). Overlaps transcription-policy work; do not duplicate existing glyph audit.


### Owner-mandated exhaustive glyph universe (2026-11-13)

OWNER REQUIREMENT: K-0001 must attempt recognition of **ALL, REALLY ALL** visible, potentially script-bearing glyph occurrences in the ENTIRE manuscript, not just basic EVA, popular glyphs, 12 font samples, or common textual regions. The scope includes every physical folio/side/foldout/panel; prose, labels, diagrams, radial/rotated writing, unusual contexts, marginal/later writing (kept apart from the original hand), corrections/erasures/retracing, detached strokes, dots, possible diacritics/abbreviation signs, ligatures, scribal allographs, singleton/hapax symbols, severely damaged forms, ambiguous marks and unreadables. No arbitrary minimum frequency and no silent drop of unknowns.

Two independent targets: **complete observation inventory** (all script-like marks have source-backed occurrence IDs or a documented unresolved status) and **verified grapheme interpretation** (separate base signs, ligatures, modifiers, allographs, marks and alternative parses). An unreadable mark may be exhaustively recorded but cannot truthfully be called recognized. Never classify as done merely because all discovered marks got a guessed name, all 213 snapshot canvas IDs were listed, or the user's PDF has 214 pages. Use complete image-to-physical-folio concordance, versioned pixel/stroke locations, disputed region accounting, blind independent annotators, rare-form missed-mark audits, leaf-heldout tests, a second independent image or transcription witness and a frozen end-condition. Rights and uncertainty are binding gates.

**Bounded pilot actually inspected:** 214-page user-supplied MS408 PDF SHA-256 d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c. The 12 v0.2 font slots VY001..VY012 were cropped on f16r (PDF p.32) and compared non-blind with f2r, f8r, f18r, f20r, f24r and f26r from the SAME PDF. Preliminary assessments: 4 visually recurring (VY002/004/007/008); 3 plausible (VY001/005/011); 1 undecided (VY003); 4 apparent multi-mark/composite (VY006/009/010/012). Computer-vision scores caused demonstrable plant illustration false positives; not proof. ZERO independently verified grapheme classes, ZERO independently validated EVA mappings. No confirmatory glyph experiment run.

**Owner VY001 override:** Three similar upper cross-loop candidates from f16r/f24r/f20r show DIFFERENT lower-left terminal curves. Treat as three separate occurrences (A/B/C), never as one confirmed class or one proven EVA p. Separate equally live hypotheses: distinct grapheme; scribal/position allograph; neighbor ligature; base plus reusable diacritic/abbreviation modifier; ink/cropping artifact. No classic two-dot trema was proven, no phonetic umlaut inferred. Earlier f16r first-word EVA p from pocheody is a TENTATIVE alignment only; not transferred to the other images. Test stroke connections to left/right neighbors, the same modifier on other bases, role in word, hand and leaf-heldout, against independent image sources and image-matched negative controls. **All classes currently UNRESOLVED**.

Source/provenance, coverage gates and counterexamples: research/glyphs/2026-11-13_K0001_all_glyphs_scope.md. Machine-readable image-reference records: research/glyphs/2026-11-13_K0001_v02_samples.jsonl (12) and research/glyphs/2026-11-13_K0001_VY001_triad.jsonl (3). Metadata ONLY; no user PDF, Yale manuscript photo crops, font binaries or third-party transcripts copied to GitHub before rights review. O-01 correction hypothesis and EXP-0025 EVA-only predictor are research inputs, not glyph ground truth. **K-0001 OPEN / CONFIRMATORY_NOT_RUN; 0/5 decipherment gates unchanged**.

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
