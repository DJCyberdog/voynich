# EXP-0021 / A-05 — exact q-initial line-edge pilot on f3r and preregistered f8r

**Date:** 2026-11-10. **Question:** In ZL3b-n v3b IVTFF transliteration, are tokens beginning with EVA `q` depleted at the start of a transcribed line versus random token order **within that same line**? This is one deliberately narrow A-05 prediction, not a test of all line-edge effects.

## Baseline, duplicate audit and provenance

- Live verified `main` at start and before writing: `eee6721615098918cce02bf76e4fdda26db60176`, identical to prior main. Ten open Draft PRs #25–#31 and #33–#35; #25–#31 and #33–#35 overlap README/memory. This work augments existing Draft PR #35 and **must not be merged without owner authorization and collision reconciliation**. Integrated main remains EXP-0016.
- All 14 mandatory README/docs/memory files read first, plus queue/protocol and prior A-05 source audit from PR #35. EXP-0014 tests suffix-order prediction on 20 f3r lines, **not** this token-initial `q` positional test. EXP-0018 in unmerged PR #26 concerns a different suffix-class conditional test and is **not** independent evidence here.
- Input origin: René Zandbergen / Gabriel Landini, `https://www.voynich.nu/data/ZL3b-n.txt`; header `IVTFF Eva- 2.0 M 5`, version 3b of 2025-05-13, inspected 2026-11-10. Source `SRC-0016`; IVTFF uncertainty conventions `SRC-0019`; site permission `SRC-0017`, plus current public origin notice `https://www.voynich.nu/roadmap.html#cop` (transliterations described as CC0, source acknowledgment requested; no image/font license inferred).
- Only f3r lines 1–20 and f8r lines 1–21 were copied into a **temporary local extraction**, not into GitHub; exact local manual-extract text SHA256: `06bc49cf50fb8b0ba3281d50b2a6e8ed7794050983589ae44b1a20f37db628f6`; alternative local IVTFF-tagged extract SHA256: `c7dcea29a48ed9e105da6806c902cf089a05f7e4debfc4ad696c8e2d09da067b`. **Original full-file SHA256 was not recomputed** because container download failed; owner-reported `bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc` remains **CLAIMED**, not verified in this cycle. Hand-transcription fidelity across all characters is not cryptographically established.
- Source page describes both folios as herbal, Currier A, hand 1. No Yale images, visible strokes, ligatures, physical spaces, independent scribe assignment or manuscript dating were authenticated. SRC-0007 remains owner-designated canonical for canvas indexing, **not independently live-Yale authenticated**; no routine 403 retry.

## Preregistration and test design

Before inspecting any f8r lines, the locally written protocol `voynich_A05_prereg_2026-11-10.md` had SHA256 `8e02f8bd3fabf06cb9393633d76a1510dbcf823396380a1f99ebe7c783a71eb4`. This is an **in-session local preregistration**, not an independently timestamp-certified repository preregistration. f3r had already been viewed; f3r therefore exploratory. f8r was selected and its scope frozen **before** looking at its data; no feature or threshold changed thereafter.

**Prediction H1:** The count of lines whose first retained certain EVA token starts with `q` is **smaller** than under random within-line token order. **H0:** Line-level tokens are exchangeable conditional on each line's retained token multiset and length; for line i, `p_i = q_i/n_i`; the count has an exact Poisson-binomial distribution. Exact directional left-tail CDF, fixed `alpha=0.05`; report f3r and f8r **separately**, no pooled or post-hoc directional significance.

**Parsing:** select only P0 paragraph-text lines, not labels or right-justified `=Pt`; remove `<%>`, `<$>`, editorial comments; treat `<->` as an editorial split inside the same line; period is a confident boundary. **Primary comma rule: drop the whole comma-containing uncertain segment.** Drop any token containing non-ASCII-letter uncertainty notation rather than guessing glyphs. If the original first segment is uncertain, exclude its whole line rather than promoting the next word to line-start. Retain manuscript line boundaries. No claim of physical word segmentation. Eligible f3r: 20 lines, 104 tokens (also reproduces EXP-0014's reported **exclude-policy token count**, but not its statistical model); f8r: 16 lines, 111 tokens, after excluding `=Pt` lines 8/13/21 and ambiguous first segments 12/14.

**Strongest counterhypothesis:** word-length, paragraph opening, line filling, scribe/section/layout, tokenization and editorial choices cause the effect without an independent generator rule. Prespecified descriptive sensitivities: exclude paragraph-initial lines; exact conditional candidate tokens restricted to the observed first-token length. Neither sensitivity is an independent confirmatory family. Positive control: a 50-line synthetic construction with per-line null probability 0.5 and forced non-q first tokens; negative control: two independent fair events must give PMF [0.25, 0.50, 0.25], and all probabilities sum to one. These do **not** validate real-data exchangeability. Folio f8r is held out relative to f3r exploration only; two folios from one hand/section are not an independent historical or transcription-witness replication.

## Executed, reproducible results

One independently written Python-standard-library implementation (no external code, packages or installations) on manually extracted source lines gave:

| Contrast | Eligible lines | Retained tokens | Observed q-first lines | Exact H0 expected | One-sided left-tail p |
|---|---:|---:|---:|---:|---:|
| f3r exploratory | 20 | 104 | 2 | 3.8341269841 | 0.1893782349 |
| f8r predetermined holdout | 16 | 111 | 1 | 0.2361111111 | 0.9861111111 |

Additional **sensitivity** results, not new tests of independent hypotheses:

| Folio | Nonparagraph observed / expected / p | Same-first-word-length observed / expected / p |
|---|---|---|
| f3r | 2 / 3.2341269841 / 0.3058996825 (16 lines) | 2 / 1.8666666667 / 0.75 |
| f8r | 1 / 0.2361111111 / 0.9861111111 (14 lines) | 1 / 0.3333333333 / 1.0 |

**Positive synthetic control:** p=8.881784197001252e-16 for 0/50 forced non-q starts, each line's null q-first probability 0.5. **Negative synthetic control:** PMF [0.25,0.5,0.25] exactly reproduced. Numerical total-mass error <1e-12. These controls confirm elementary implementation behavior, not adequacy of the observational null.

**Decision:** The narrow directional q-line-start depletion prediction **did not pass** the predeclared alpha level on either folio; in f8r the observed count exceeds the null expectation. This is **not proof of no edge effect**, and non-significance does **not contradict** the broad A-05 claim. Word-length matching also removes the apparent exploratory depletion direction in f3r. No independent glyph reading or full-corpus inference; no translation, plaintext, linguistic identity, semantics or dating. No gate 1–5 passed.

## Scope and status

- **VERIFIED conditional on manually extracted lines:** deterministic Poisson-binomial arithmetic, synthetic controls, f3r matching the already reported 104-token exclude-policy count.
- **DOCUMENTED:** original header/line loci as visible on origin URL, rights notice and IVTFF editing policy; computation was actually performed (not merely planned).
- **CLAIMED:** owner-provided full-origin SHA256 not independently recomputed.
- **INFERRED:** this particular q-first depletion is not supported in the scoped samples; length and paragraph sensitivity matters.
- **UNKNOWN:** whether the original full-file bytes exactly match the local selection, independent second witness, physical glyphs, stronger conditional nulls, whole-book edge effects and meaning.
- **Workflow:** A-05 stays ACTIVE; audit stage TESTED for **this single narrow subclaim**; 40-claim parent `completed=false`. This report is an EXP-0021 **draft until owner-authorized integration**, not a new independent source or manuscript-language solution.

**Reproduction:** `python research/scripts/a05_line_start_q_exact.py /path/to/ZL3b-n.txt` (source file to be fetched by the investigator under origin usage terms). Script embeds **no** manuscript transcription. Compare full input's computed SHA256 to the owner-reported reference if available; only then consider source-byte provenance independently verified. No raw manuscript image or corpus copied.

**Next discriminating step:** obtain and locally hash the original full IVTFF bytes, cross-check f3r/f8r positions against independent EVA/IVTFF witnesses and image-linked folio regions, then preregister substantially larger, hand/section/word-length/paragraph-controlled folio-held-out edge tests. Do not repeat q-first on these same two folios as a new discovery.


## Independent source-line reproduction 2026-11-10 (bounded audit, NOT a new discovery test)

**Question / pre-existing falsification target:** Do the earlier EXP-0021 line-selection counts, q-initial proportions, and Poisson-binomial left-tail probabilities survive an independent re-extraction of the *same original ZL3b-n v3b transcription witness* and an independently programmed exact enumeration? The already recorded figures, parser scope and exclusion policy above were immutable targets before this check. This is a reproduction of previous results, not an independently new held-out or preregistered test.

**Original transcription source:** https://www.voynich.nu/data/ZL3b-n.txt, header IVTFF Eva- 2.0 M 5, Version 3b of 2025-05-13. Its original-site rights notice https://www.voynich.nu/roadmap.html#cop identifies transliterations under CC0. No transcript bytes, manuscript images or fonts are copied into the repository. Original full-file SHA256 **NOT** computed (direct container-network download failed); the owner/registry complete-file hash remains CLAIMED. Manual transcription of sampled visible web lines is not an independent second witness or an independent digital full-file hash.

**Sample:** f3r.1–20 and f8r.1–21 (41 original records examined); remove the three f8r right-aligned =Pt entries 8,13,21 and the two rows 12,14 with ambiguous first token. Use the previously frozen EXP-0021 comma policy, paragraph handling and ASCII token acceptance. Eligible 20 f3r and 16 f8r lines. The original-source header describes both as Currier A, hand 1; this is edition metadata, not independent physical-script verification.

**Independent per-line counts (line: accepted token count: accepted q-initial token count; no text bytes):**

- f3r: 1:5:1; 2:5:1; 3:5:1; 4:6:0; 5:5:1; 6:4:0; 7:5:1; 8:5:0; 9:5:0; 10:2:0; 11:5:0; 12:3:1; 13:4:3; 14:4:2; 15:8:0; 16:9:2; 17:5:1; 18:5:2; 19:7:3; 20:7:0.
- f8r: 1:8:0; 2:7:0; 3:7:0; 4:9:1; 5:8:0; 6:6:0; 7:4:0; 9:8:0; 10:8:0; 11:7:0; 15:7:0; 16:4:0; 17:8:1; 18:7:0; 19:8:0; 20:5:0.

**Execution and independent control:** One fresh standard-library-only parser calculated per-line p_i = q_i/n_i. The exact lower tail was recomputed both by iterative Poisson-binomial convolution and by exhaustive enumeration of binary events among lines with p_i>0. The latter involves 2^12 = 4096 binary outcomes for f3r, and 2^2 = 4 for f8r. Negative toy control: fair two-event distribution [0.25, 0.5, 0.25]. No third-party executable, new source corpus or model tuning. This duplicate calculation is an arithmetic control, not independent author/folio validation.

| Folio | Eligible lines | Tokens | Observed q-initial starts | Null expected | Exact p, convolution | Exact p, enumeration |
|---|---:|---:|---:|---:|---:|---:|
| f3r | 20 | 104 | 2 | 3.8341269841269843 | 0.18937823492063505 | 0.1893782349206353 |
| f8r | 16 | 111 | 1 | 0.2361111111111111 | 0.9861111111111109 | 0.9861111111111110 |

**Result: REPRODUCTION PASS** for all listed sample sizes, totals, observed counts, null expectations and one-sided probabilities within floating-point tolerance. Independently recalculated word-length-matched sensitivities also agree: f3r null expectation 1.8666666667 and p=0.75; f8r expectation 0.3333333333 and p=1.0. This is a **material numerical provenance/implementation check**, not a new independent significant manuscript observation.

**Evidence / workflow:** VERIFIED arithmetic conditional on manually extracted original-site lines; DOCUMENTED source header, line loci, IVTFF/editing and original-site rights notice; CLAIMED full origin file SHA-256; UNKNOWN byte-identity of full file, independent transcription witness, visible glyph mapping, global line-edge generator and meaning. A-05 stays ACTIVE, audit stage TESTED for this narrow subclaim only, completed=false. All five decipherment gates remain unpassed.

**Strongest counterhypothesis:** The conditional within-line exchangeability null ignores word length, paragraph starts, line filling and scribal/section/layout confounds. A natural-language model, cipher, nonsemantic generator or hybrid may reproduce this same small-sample result. f8r was used already in EXP-0021 and MUST NOT be claimed as a fresh heldout in this audit.

**Next:** Independently obtain and hash exact original full-file bytes (if available), check a separate transcription edition and region-to-glyph correspondence, then preregister genuinely unused larger folio-heldout, hand/section/length/paragraph-controlled tests. Do not rerun this sample as a new discovery.
