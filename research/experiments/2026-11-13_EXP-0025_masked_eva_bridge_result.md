# EXP-0025 — Folio-held-out EVA interior-bridge prediction

**Status:** RESEARCH_COMPLETED / TESTED / VERIFIED **only for one owner-held editorial transliteration**.  
**Executed:** 2026-11-13 after frozen pre-registration `1ab87e82cc13408ff8dca68c2370954e89f1da4f`, and frozen repository implementation `9d1bb16c1a2e5c2b80730ab5ce37eda6085e0637`.  
**Design:** `research/experiments/2026-11-13_EXP-0025_masked_eva_bridge_prereg.md`; repository implementation `research/scripts/exp0025_eva_bridge.py`; machine-readable aggregate `research/results/2026-11-13_EXP-0025_eva_bridge.json`.

## 1. Exact hypothesis, corpus, source strata

**Question:** Can a missing *single EVA ASCII transcription character* in the interior of a word be recovered from its immediate flanking characters `L _ R` better than from `L` only, across previously withheld entire folio IDs and word types absent from the training folios? This is a graphotactic **two-sided bridge**; it is not decryption or a word translation.

**Input:** Owner-library `ZL3b-n.txt`, IVTFF Eva- 2.0 M5, Zandbergen/Landini 3b, dated 2025-05-13, byte SHA256 `bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc`; owner-provided file locally checked against SHA256 (not independently live-origin authenticated). The primary published IVTFF convention clearly treats dot as a confident word space and comma as uncertain; this protocol included only `P0` paragraph main-text loci and `[a-z]{4,}` complete dot-separated segments; markup, uncertain readings and uncertain-comma segments excluded. No scanner originals, raw IIIF images, full transcriptions or user-supplied protected corpus bytes re-hosted.

**Parser output:** 3,885 P0 loci, 31,588 nonempty dot-separated candidate segments, **24,351 accepted whole words**, 7,237 rejected segments. **203 eligible folio IDs**; SHA-frozen folio split **160 TRAIN / 43 TEST**. Training uses 69,448 interior positions in 4,799 exact wordtypes; heldout uses one deterministically masked interior character per eligible word, **5,369 TEST word tokens**, of which **991 were completely unseen exact wordtypes**. No TEST folio's accepted word tokens used for fitting. *Important:* folio IDs are transcription-page/surface IDs, not unique physical leaves: a recto could be in TRAIN while its verso is in TEST; other folios in the same section/scribe also occur on both sides. Accordingly `unseen` means **unseen by this model at the folio-ID unit**, NOT historically unknown to investigator or absolutely isolated from all material provenance.

## 2. Frozen models and genuine target result

- **P0:** global EVA-character counts, training only.
- **B1 LEFT:** smoothed conditional `P(x | left)` (10 pseudo-observations to global).
- **M2 BRIDGE:** smoothed conditional `P(x | left,right)` (15 pseudo-observations back to B1). **Preregistered primary contrast M2 minus B1 on heldout OOV words**.
- **M3 BRIDGE+SLOT:** M2 with near-start, near-end, or middle word position; 30 pseudo-observations back to M2 (**secondary only**).
- **B4 COPY:** near-exact training word memorization by all other letters plus smoothed B1 fallback (5 pseudo-observations); **stronger than a frequency-only baseline**, yet not a full trained nonsemantic generator.

| Masked unit test set | B1 top-1 | M2 top-1 | M3 top-1 | B4 copy top-1 | M2 vs B1 gain |
|---|---:|---:|---:|---:|---:|
| **Exact new word types, 991 targets / 43 folio IDs (PRIMARY)** | **43.2896%** | **63.0676%** | 63.8749% | 41.9778% | **+0.6594583087 nats/target** |
| **All heldout words, 5,369 targets / 43 folio IDs (secondary)** | 57.2732% | **77.3887%** | 78.0220% | 75.2654% | **+0.5763486995 nats/target** |

The primary OOV M2 mean log likelihood `-1.0673248433` vs B1 `-1.7267831520`; M2 also exceeds B4 on this restricted OOV set, but that **does not** establish superiority over a different, well-tuned copy/edit or generative process. B4 baseline specifically memorizes training words and backs off when the full form is novel.

**Predeclared uncertainty/gates (ALL MET):**
- 991 OOV targets from 43 heldout IDs, 63.2694% of OOV right-context values exchangeable in the predeclared matched null (minimum 100, 5 folios, 50% mobile).
- Required `M2 - B1 >= +0.020` nats/target: **+0.659458 > 0.020**.
- **400 TEST-folio cluster-bootstrap draws**, fixed RNG: 95% empirical percentile **[+0.6043683,+0.7244655]** nats/target, excludes zero.
- **199 within-(folio,left,slot) right-neighbor permutations**, fixed RNG: null mean **-0.01055975**, maximum **+0.14036729**, **0/199** as large as observed. Empirical one-sided `p=(0+1)/200=0.005` <= 0.01.
- Synthetic self-controls: positive conditional bridge gain **+1.03115798**; independent-right negative control **-0.0002105254**. Both code gates PASS. These synthetic controls demonstrate detector behavior, not Voynich causality.

**An independently written minimal Python spot-check** re-parsed the exact owner-held bytes and recomputed training/test folio counts, OOV denominator, two model likelihoods and top-1 accuracies with distinct source code: **43/160**, **991**, **+0.659458308679125**, **0.4328960645812311**, **0.6306760847628657** matched precisely. This checks primary arithmetic independently, but is not an independent manuscript or editorial witness.

**Implementation provenance caveat:** The exact frozen GitHub implementation `research/scripts/exp0025_eva_bridge.py` was committed **before scoring**, as prescribed. However, direct raw GitHub file transport into the offline local execution container was unavailable. Actual scoring executed a **separately written algorithmically equivalent stdlib Python implementation**, local SHA256 `023b7b2fae106c4c2e6b96663c5c20c7c1d01de3d6630057761bdbb52aae6f28`; a third concise implementation independently checked the core arithmetic (local SHA256 `7748657f70d6abc4c05e719b4f5e664dde9c35f20c2dbde9faed39e9926f724c`). These **do not constitute a byte-identical execution check of the repository script**. Repo script should still be executed by another reviewer on the same SHA-pinned bytes before acceptance as reproducible multi-environment software.

## 3. Explicit interpretable train-only candidate rules (exploratory)

Rules were selected exclusively on TRAIN count >=80, majority fraction >=0.65, ranked by `n*(majority_share - B1_baseline_probability)`, before inspecting target positions. These are **EVA CHARACTER sequences**, and *not yet manuscript-glyph or semantic rules*. The full ranked eight in aggregate JSON include the following useful differentiators:

| TRAIN-only selected bridge | TRAIN support / dominant fraction | Heldout **OOV** direct hits | LEFT top-1 on same targets | Comment |
|---|---:|---:|---:|---|
| `k _ i → a` | 1076 / 97.77% | **13/13** | **0/13** | Strong local editor-symbol combination; small independent OOV support |
| `h _ l → o` | 897 / 86.18% | **11/13** | **0/13** | Generalizable two-sided context |
| `k _ h → c` | 779 / 82.41% | **8/11** | **0/11** | May be tied to EVA compound/gallows segmentation |
| `c _ e → h` | 3160 / 99.968% | **46/46** | **46/46** | Highly predictable but **adds nothing beyond LEFT** in those examples; classic editorial `ch` concern |

These are **not four independent significance findings**: selected rules are correlated, the eight were chosen on TRAIN, and these small heldout denominators do not establish historic sound values. The modest-confidence or failing patterns are also recorded in aggregate JSON (no cherry-picking as overall rule proof).

**Post-hoc ablation (exploratory, NOT a new preregistered success):** On OOV targets excluding an EVA `ch/sh` pair *touching the masked position*, **n=775**, gain **+0.630699** nats, M2 top-1 **55.74%** vs B1 **35.87%**. More restrictive, dropping all `c/s/h` in the masked triple, **n=539**, gain **+0.631416** nats, M2 **60.11%** vs B1 **39.52%**. This argues the observed bridge prediction is **not solely** a `ch/sh` ASCII encoding artifact. The analyst chose these exclusions **after** observing the primary result; do not retroactively attach p-values, bootstrap or confirmatory claims. Other multi-character EVA symbols and editorial conventions remain confounds.

## 4. Falsification logic and limitations

**VERIFIED (narrow local numeric scope):** with one exact SHA-pinned ZL3b-n v3b *editorial* source and an unaltered fixed folio-ID split, bidirectional character context improves cross-entropy and top-1 predictions of masked inner characters over LEFT. Positive/negative synthetic controls and independent arithmetic spot-check agreed.

**DOCUMENTED:** source version/format and IVTFF uncertainty conventions; original manuscript pages remain distinct from this transcription. **INFERRED:** a *reusable local graphotactic constraint* exists in that transliterated string distribution; common `k_ai`, `h_o l` and `k_ch` neighborhoods have nontrivial restricted predictability.

**UNKNOWN:** whether the same effect persists on independently reviewed parchment glyphs, compound-EVA-grapheme segmentation, second transcriber, entirely unseen **physical leaves**, different hands/sections, a genuinely independent source, or whether it reflects actual language, encryption, a nonlinguistic generator or mixed mechanism. This is a common property of structured strings in many systems; **a large statistical gain is not a decipherment**.

**Strongest competing explanation:** A rule-based nonsemantic copy/edit generator, scribal template, or human-written gibberish can produce the same `P(x|L,R)` conditional distribution without language or semantic content. The B4 lexicon is only one operational proxy and cannot exclude these richer alternatives. The within-folio shuffle null rejects conditional independence in this model, **not** all alternative generators. This work differs from EXP-0018/22 by its single masked interior EVA character and train-vocabulary OOV target, but is based on their same long-studied source.

**Next genuine external gate:** (1) independently run frozen repository script and compare hashes/results; (2) group **physical leaves and folio pairs** in heldout folds, preventing opposite-side leakage; (3) rerun on an independently rights-checked EVA/IVTFF witness and on a manuscript-image-backed atomic/ligature glyph segmentation with blind human verification; (4) pit against matched-complexity **heldout copy/edit and encrypted natural-language control corpora**, rather than a simplistic language-versus-random null; (5) only then test a fixed compact orthographic `L_R` grammar and compare across Currier/hand/section. No invented translation or new decipherment gate.

**Status:** one successful **bounded** phonotactic/graphotactic *transcription prediction* experiment; EXP-0025 `VERIFIED (scoped)` / `ACTIVE`, no manuscript decipherment acceptance gate, still **0/5**. This is **Draft-PR only, unmerged**, original A/W 40-claim queue unchanged (3/40 scoped-complete integrated).
