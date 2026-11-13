# EXP-0025 preregistration — predict masked internal EVA letters on folio-held-out material

**Date and stage:** 2026-11-13; FROZEN DESIGN BEFORE implementing or running the manuscript target scoring. This project already knows and has analyzed the same source witness in earlier EXP-0017/18/22/23/24. Therefore this is a **new protocol-frozen within-corpus folio holdout**, NOT an entirely unseen manuscript, independent transcription witness or independent historic script validation. **No target results may be used to change these rules.**

## Question

Can a single **EVA ASCII transcription character** (not necessarily a physical glyph; e.g. EVA `c`+`h` can form a ligature) hidden at a deterministic interior position of a word, be predicted better using its immediate visible **left and right neighbors** than by the left neighbor alone, especially on **word types absent from the training folios**? This tests a narrowly specified graphotactic *bridge constraint*, not language, cryptography or meaning.

## Immutable input and parser

- Owner-library `ZL3b-n.txt` source bytes, SHA256 `bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc`; header `#=IVTFF Eva- 2.0 M 5`, ZL version 3b, 2025-05-13. Publisher: https://www.voynich.nu/data/ZL3b-n.txt . Read-only, no transcript content in Git, no external code, only Python standard library.
- Match IVTFF page/locus lines with `^<(f[0-9]+[rv][0-9]?)\.([0-9]+),([^>]*)>\s*(.*)$` and require type `P0` in the locus tag (paragraph main text, including modifiers). Discard all comments and other locus types.
- Replace documented certain `<->` and `<~>` boundaries with `.`. Replace other angle-bracket markup (including `<%>`, line-end, annotations) with `.`. Split only on the *certain* IVTFF `.` separator; do not treat uncertain `,` as certain. Accept **only complete segments `[a-z]{4,}`**, reject bracketed alternatives, `?`, ligature markup, comments, uncertain comma pieces, digits, capitals and whitespace, rather than silently resolving them. Rejected segments are counted. Use token ordinal in full dot-split list as token ID. All EVA single ASCII letters remain **editorial transcription characters**; no physical glyph, semantic or phonetic claim.
- Name the folio exactly as in the captured locus ID. No rejoin between folios, no Currier/hand labels used for predictions.

## Fixed, nonleaking split and mask

- Freeze folio holdout: `sha256(b"EXP0025-split-v1|" + folio.encode()).digest()[:8]` interpreted unsigned big endian modulo 5 == 0 => **TEST**, all others **TRAIN**; no hand selection or alternate seed. The split cannot be modified even if unfavorable. Report heldout folio IDs/count and known exclusion counts *after scoring*, but never retune to them.
- Training: every interior position `i = 1..len(word)-2` in each TRAIN token supplies `(left=word[i-1], target=word[i], right=word[i+1])`. Training tokens themselves may be repeated.
- Heldout: exactly **one** masked interior position per eligible TEST word, at `i=1+ (uint64first8(sha256(b"EXP0025-mask-v1|" + folio + "|" + locus_number + "|" + split_segment_index)) % (len(word)-2))`. The unmasked target is NEVER used in training. Other letters of the masked word are visible; full word only used after prediction to check exact target and OOV status. For this task, a complete unknown folio means all accepted words on it are kept out of model fitting, not that the historical manuscript has never previously been viewed by anyone.

## Models fixed BEFORE heldout scoring

Alphabet **26 ASCII lowercase letters** (even if zero count in TRAIN). For training set N interior positions, `P0(x) = (n(x)+0.5)/(N+26*0.5)`; hierarchical smoothing:
- **B1 LEFT:** `P1(x|L) = (n(L,x)+10*P0(x))/(n(L)+10)`.
- **M2 BRIDGE (primary):** `P2(x|L,R) = (n(L,R,x)+15*P1(x|L))/(n(L,R)+15)`.
- **M3 BRIDGE+SLOT (sensitivity ONLY):** `P3(x|L,R,S) = (n(L,R,S,x)+30*P2(x|L,R))/(n(L,R,S)+30)`, where S is `NEAR_START` if index=1; otherwise `NEAR_END` if index=len-2; otherwise `MIDDLE` (for length 3 not eligible). No other features.
- **B4 COPY/EDIT (strong countermodel):** Count all TRAIN word types; for each heldout word, mask its selected char, search training words of same length whose other letters match *exactly*. For candidate target char x, `P4(x) = (n(masked_signature,x)+5*P1(x|L))/(n(masked_signature)+5)`. This embodies lexicon memorization/copy/edit with local backoff, no semantic assumption.
- B0 global `P0` descriptive; B1 is the **predeclared statistical baseline**; M2 primary; M3/B4 comparisons descriptive secondary. No hyperparameter search, no model selection from TEST.

## Test endpoints and decision criterion

**Primary evaluation population:** TEST words whose complete exact word type was absent among all TRAIN words (**OOV**); secondary all TEST words. Primary metrics: `gain_OOV = mean[log P2(actual target) - log P1(actual target)]` nats per OOV target, and paired top-1 accuracy difference, with ties resolved alphabetically. Additional comparison M2 against B4 copy model and M3 vs M2; return empty/INCONCLUSIVE if fewer than 100 OOV targets or fewer than 5 TEST folio groups contribute.

**Predeclared success threshold:** (a) `gain_OOV >= +0.020` nats/target; (b) **95% TEST-folio cluster bootstrap** with 400 fixed-seed samples has lower percentile > 0; (c) **199 within-folio, (left,slot)-stratified right-neighbor permutations** of the TEST rows yield zero or at most one null gain >= observed, i.e. one-sided `p <= 0.01` by `(1+exceedances)/200`. Use seed 250125 for shuffle/bootstrap; if too few movable rows, report null invalid rather than silently claim significance. Accuracy improvement is reported **but not** a fourth gate, since probabilistic prediction is primary. Report all categories/denominators and gaps, including non-OOV results, even if test fails.

**Illustrative bridge rules extracted only from TRAIN:** for each observed pair `(L,R)` with training count >= 80 and majority empirical frequency >= 0.65, compute `score = n(L,R) * (majority_freq - P1(majority|L))` and select top 8 sorted descending score then lexicographic ties. Publish for each rule `L _ R -> x` its TRAIN support, training precision, heldout OOV support, heldout top-1 precision and B1 comparator on same rows. These are *not* separately preregistered hypotheses; exploratory legibility aids. No hard-coded predicted actual values or Voynich words.

**Negative control:** for 199 draws shuffle *visible right neighbors* of OOV rows within identical folio, left and slot strata, fixing target, left, slot, word and TEST membership. Track the fraction with movable context and measured gain distribution. **Positive code control:** synthetic generated triplets with a target determined ~90% by a deterministic L,R mapping but not recoverable from L alone, split by synthetic document ID. Must yield M2 > B1; if not, implementation FAIL, target result not scientific. **Secondary confound audit:** direction-dependent long word copy/edit, Currier/section/hand and transcript edition not controlled here; no claim that M2 reveals a special Voynich-only mechanism. In absence of a matched nonlanguage synthetic *manuscript generator*, reject exclusive-language inference even if significant.

**Falsification:** if primary conditions fail, the frozen specific M2 threshold claim is **NOT MET/CONTRADICTED IN THE TEST SCOPE**, not proof no character rules; if masks/parser/folds are ineligible, BLOCKED. If all conditions pass, claim only robust **within this particular EVA/IVTFF witness and heldout folio partition**. Do not count as script/language/semantics/decipherment acceptance gates (0/5). Report limitations before discussion of any concrete rules.

## Source and leakage gate

The entire transcription's SHA256 was independently verified in the working container before freezing this design. **No new target labels or outcomes inspected by the experimenter prior to this commit.** Prior exploratory work on same full witness means test is prospective to this frozen computation **only**. The source is an editorial transcribed layer (EVA ASCII != manuscript glyphs); human-independent original imaging, alternate witnesses, Manuscript IIIF source and historical semantic interpretation remain UNKNOWN. No raw transcript or image can be added to Git without separate rights review.

**Gate sequence:** commit this prereg to a new branch; only THEN implement fixed stdlib script in a second commit; only THEN execute/test (outcomes never retroactively modify protocol); commit script, machine-readable aggregate results, bounded report and consistent memory updates to same branch; PR only after verifying actual main, IDs, PR collisions. No direct main writes or automatic merge. This is separate from unmerged EXP-0024 of PR #38 and does not duplicate EXP-0018 / EXP-0022 (their targets are **word-ending classes**, not one masked inner EVA character).
