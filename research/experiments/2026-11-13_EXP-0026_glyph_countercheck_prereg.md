# EXP-0026 preregistration — adversarial composite-EVA, leaf-grouped heldout character/glyph prediction

**Freeze date:** 2026-11-13; author selected the complete protocol BEFORE running this EXP-0026 target calculation. **Purpose:** genuine countercheck of EXP-0025's 63.07% masked single-*ASCII*-character prediction, particularly leakage from composite EVA conventions and a too-weak left-only baseline. Prior exploratory analysis of same owner-held transcript and EXP-0025 outcomes means NOT a historically never-seen source, a new independent transcription witness, or a full independent manuscript glyph validation.

## Pinned source and boundary
Owner-held user Library `ZL3b-n.txt` = IVTFF ZL 3b 2025-05-13; SHA256 `bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc`. No raw transcript or any scanned manuscript image in Git. Accept source lines with regexp `^<(f[0-9]+[rv][0-9]?)\.([0-9]+),([^>]*)>\s*(.*)$`; P0 locus only; convert certain `<->` and `<~>` to dot; other markup to dot; split only dot; accept `[a-z]{4,}` complete raw ASCII tokens, reject uncertain-comma/bracketed/other segments. Exactly the original EXP-0025 parser to avoid posthoc corpus improvement.

## Maximal-match compound units
Greedy left-to-right separate **six compound EVA labels** `ckh,cth,cph,cfh,ch,sh` before individual lowercase ASCII letters; these are **operational transcription units**, NOT proven single medieval manuscript glyphs, phonemes or semantic atoms. Predeclared sensitivity segmentation `ch,sh` only, with others broken into elementary letters except ch/sh; no other segmentation chosen from results. Token must have >=3 segmented units; interior i in [1,len(units)-2]. Fixed outcome inventory 26 lowercase ASCII singletons + 6 compound strings, even if some zero train observations. Same word type is literal exact ASCII word, not inferred normalized meaning.

## More conservative physical-leaf grouped holdout
Map a locus ID `fNNNr`, `fNNNv`, `fNNNv1` etc to grouped physical base `fNNN` (prefix from folio number), so all recto/verso/panels with that number are in the **same** partition; not claiming every foldout/quire layout resolved. Hold out where first 8 SHA256 bytes of `EXP0026-leaf-v1|fNNN` modulo 5 == 0. Entire other leaves train. **Never choose test IDs after seeing target results.** Mask exactly one internal EVA unit per heldout word, `i=1+[sha256("EXP0026-mask-v1|folio|lineid|dotsegmentordinal") first8 % (len(units)-2)]`. Training uses all internal unit positions in TRAIN leaves. Report total eligible leaves/panels/tokens and whether f57v/f49v/f66r (already studied) appear. Cannot claim section/hand/quire leakage solved by leaf grouping.

## Models frozen before scoring
Let fixed `A` be all 32 possible units. Hierarchical Jeffreys global `P0(x)=(count(x)+0.5)/(N+16)`.

Baseline **B1** left-only `P1(x|L) = (n(L,x)+10P0(x))/(n(L)+10)`.

For each masked position, define S = START when i=1, else END when i=len(units)-2, else MIDDLE; length bin T = SHORT when n<=4, MED when n<=7, else LONG. **B2 SLOT** `P2(x|L,S,T)=(n(L,S,T,x)+25P1(x|L))/(n(L,S,T)+25)`.

Static roles for **Stolfi-inspired proxy**, explicitly NOT his original grammar implementation: `G` for gallows `k t p f` or composite gallows `ckh cth cph cfh`; `M` for `ch sh e`; `C` for `q d l r s x i m g`; `O` for `a o y`; `U` otherwise. **B3 CLASS-SLOT** `P3(x|role(L),role(R),S,T)=(n(role(L),role(R),S,T,x)+40P2(x|L,S,T))/(n(role(L),role(R),S,T)+40)`. This is an executable *proxy for Stolfi's documented layered letter and word-position preferences*, NOT his 2000 exact word grammar. Historical original paper: https://www.voynich.nu/hist/stolfi/grammar.html (public, directly reviewed); linked raw grammar `word.grx` was unavailable at the publisher's original path in this session. **No numerical comparison to the authentic Stolfi grammar may be claimed**.

Challenger **M4 BRIDGE** `P4(x|L,R,S,T)=(n(L,R,S,T,x)+30P2(x|L,S,T))/(n(L,R,S,T)+30)`. Positions and word length now matched in M4 and B2, unlike EXP-0025. M4 is the primary challenger vs **B3** and **B2**.

**B5 COPY/EDIT exact single-mask** counts training masked signatures `(position, segmented word length, other units)`; `P5(x|signature)=(n(signature,x)+5P2(x|L,S,T))/(n(signature)+5)`. Captures memory/copy-one-character behavior, but not full generator or fuzzy edit distance; do NOT say this excludes all nonlanguage generators.

**M6 SECONDARY** bridge without slot `P6(x|L,R)=(n(L,R,x)+15P1(x|L))/(n(L,R)+15)`, allows comparison with EXP-0025 at the different segmentation/partition, but this is not a matched headline accuracy comparison.

Each model trained **exclusively on TRAIN leaves**, no hyperparameter tuning on TEST. Fixed lexicographic tie-break of units, top-1 accuracy and full heldout log likelihood reported. Apply to (i) all heldout word tokens and (ii) primary previously unseen complete word forms (OOV relative to all TRAIN tokens); OOV avoids direct word memorization but can still have a partially repeated edit signature.

## Primary hypotheses and statistical gate
**H0:** For masked internal compound-EVA units in OOV words from unseen physical leaves, right-neighbor unit identity contributes no robust extra prediction beyond the strong Stolfi-inspired role-and-word-slot baseline B3. **H1:** M4 improves full heldout log probability.

Primary `G = mean(log P4(true) - log P3(true))` nats per OOV target. Also report `M4-B2`, `M4-B5`, all-OOV/all-target top1 and absolute number correctly predicted.

**Success requires ALL:** >=200 OOV targets across >=10 heldout leaf groups; `G>=0.02` nats; fixed-seed 400 leaf-cluster bootstrap empirical 95% lower percentile >0; 199 fixed-seed **stratified right-neighbor permutation** nulls within (leaf,L,S,T) with >=50% OOV rows in a stratum of size >=2, and empirical p=(1+nulls>=G)/200 <=0.01. Seeds bootstrap=260026, permutation=260027. These controls preserve leaf, L, relative slot and length bin while disrupting extra identity R. Note CLASS baseline B3 also uses role(R); shuffled null must re-evaluate **BOTH M4 and B3** at shuffled R. Null is only valid if right-neighbor shuffling can move >50% rows. If failure, report NOT_MET or INCONCLUSIVE, **do not change the thresholds**.

**Sensitivity:** `ch/sh`-only segmentation under same partition and masks recomputed deterministically; report in separate table. If full compound segmentation fails but split-to-ASCII succeeds, prioritize EVA digraph artifact explanation. If strong B3 wins, accept previous result was not novel predictive discovery. If M4 wins, no claim of original glyph decipherment until actual manuscript image / another independent editorial witness / historical source and robust generator comparison.

**Synthetic positive and negative controls:** produce 10,000 independently seeded triplets of units with X determined by L,R class (positive, expected bridge model improves vs slot baseline), and 10,000 with X depending only on L (negative, expected G ~0 or <=.05). These test implementation's basic detection, not manuscript semantics. If positive fails or negative strongly positive, report failed implementation / no real-data acceptance.

**Prereg exact Stolfi limitation:** Original 2000 grammar's specific `NormalWord` rule frequencies were derived from manuscript text and are neither a fresh train-only model nor obtainable from the historical raw grammar URL at freeze. Thus do not claim complete direct published Stolfi benchmark; mark exact historical-vs-modern comparison **BLOCKED** until original rules/version and data-leakage boundaries are traceable. A proxy is a *stronger structural baseline* for the current within-corpus contrast only.

**Citation/provenance:** Zandbergen https://www.voynich.nu/transcr.html and https://www.voynich.nu/extra/sp_transcr.html explain EVA conventions, edition dependence and subjective word breaks. All numbers are on a named editorial transcription (NOT visible physical glyphs); manuscript glyph segmentation, alternate independent transcriber and semantic decoding UNKNOWN. No full scan or source copy. No third-party code, software installations or paid services.

## Reproducible sequence
1. Commit this protocol alone on isolated branch before running target evaluation.
2. Commit fixed standard-library Python implementation before scoring; execute with locally SHA-pinned user text; include independent arithmetic spot-check, aggregate machine JSON and bounded source-critical report in follow-up commit.
3. Validate JSONL memory IDs/README current *integrated* state, actual main SHA and PR overlaps; Draft PR only, no unauthorized merge.
