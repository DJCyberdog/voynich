# EXP-0018 — Does the suffix-class Markov gain disappear after controlling word position? (2026-11-06)

## Pre-specified question and strict position-aware null
**Question Q-020:** Is the held-out four-suffix-class Markov advantage reported by EXP-0017 explained solely by class frequency variations at different absolute positions within transcription lines, including line-length dependence?

The owner requested this targeted falsification test on 2026-11-06, before its null draws. Primary condition: for each of the 226 IVTFF folio IDs, preserve the four-class frequency distribution at **every exact (accepted-token line length, absolute token offset)**. Randomly permute tokens only among different lines in the same (folio, exact length, exact offset) stratum. The null therefore preserves every original line length, exact position-specific margins (conditioned on line length and folio), folio class totals, folio-held-out five-fold split (seed 377), original class mapping, and original token parser. It disrupts local dependencies among neighboring classes within each line. **H0:** Conditional on those position/length/folio margins, token classes are exchangeable across lines; any original Markov advantage is explained by those margins. **H1:** The original held-out advantage exceeds this null. The second, less restrictive sensitivity shuffles within (folio, absolute position) but does not match exact line length.

For each of exclude (primary), join and split (sensitivity) comma policies, run 1,000 permuted realizations of each null, initial RNG state 180377, deterministic SplitMix64 / Fisher–Yates; original scorer and five original folio-held-out folds remain unchanged. Report the observed held-out gain, mean/2.5–97.5% null percentiles, largest draw, number of draws >= observed and one-sided empirical p=(1+exceedances)/1001. **Exploratory:** exact null refinement and seed selected before these new draws, after EXP-0017 was known. Interpret only within source/parser/folds, not a general confirmatory language claim.

## Inputs and controls
Owner-uploaded ZL3b-n v3b bytes SHA-256: **bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc**. Original owner evaluator SHA-256: **7acf5cb70b6197549d71cd2f1b91bda3a72d1c7885d63db76522454083017e89**. EXP-0017 vectorized evaluator SHA-256 of the locally executed file: **24bebe12f1e214636122f0bf90351bcaa36584b1d86e9ba8f04c7d34acea97d3**. These are local byte identities; no independent live source authentication or manuscript glyph reading.

All three original five-fold held-out results were reproduced to within 1e-12 before shuffling. Each of 6 null distributions contained exactly 1,000 scored permutations. Position/length/folio stratum class counts and folio class totals were checked for exact equality before/after shuffling on the first and last draws. In the strict null, movable token positions = 27,196/32,147 (84.6%) exclude; 29,294/34,415 (85.1%) join; 31,000/37,105 (83.5%) split. Pairs whose both positions were in strata of size >=2 = 22,708/27,038 (84.0%); 24,743/29,269 (84.5%); 26,512/31,956 (83.0%). Nonmobile positions remained fixed and were not silently discarded.

## Primary test — exact folio, line length and absolute token position preserved

| Comma policy | Observed advantage (nats/edge) | Strict null mean | Null 2.5–97.5 percentile | Null maximum | exceedances / empirical p |
|---|---:|---:|---|---:|---|
| Exclude (primary) | **0.0184408372** | 0.0099884381 | [0.0085752060, 0.0116157494] | 0.0129163072 | **0/1000; p=0.000999** |
| Join | **0.0182680248** | 0.0096878920 | [0.0083805824, 0.0112034088] | 0.0122888830 | **0/1000; p=0.000999** |
| Split | **0.0168464198** | 0.0095498234 | [0.0082881531, 0.0109196736] | 0.0117086208 | **0/1000; p=0.000999** |

The observed minus strict-null mean residuals are 0.0084523991 / 0.0085801329 / 0.0072965965 nats per transition. In all three policies the observed gain exceeded the **largest** permuted gain. The less restrictive (folio, position) null also had zero exceedances each: means exclude 0.0072064624, join 0.0069997585, split 0.0061739458.

## Independent secondary predictive check (exploratory)
Using the same five **held-out folio groups**, compare **position-only** class prediction P(next class | exact line length, exact next-token position) to **position + previous-class** prediction P(next class | same features, previous class). Both models share the same length/position strata and use hierarchical smoothing from training folds only (baseline shrinkage 20, Markov prior strength 20). No held-out target labels enter fitting; exact line length and position are known features. This secondary model is not a second p-value.

| Comma policy | Position-only held-out loss | Position + preceding class loss | Extra held-out gain |
|---|---:|---:|---:|
| Exclude | 0.6726569316 | 0.6613052963 | **+0.0113516353** |
| Join | 0.6658549278 | 0.6553486658 | **+0.0105062620** |
| Split | 0.6575330123 | 0.6479428444 | **+0.0095901679** |

All 15 fold/policy cells had positive gain under this parameterization. Sensitivity to fixed prior strengths 5 and 100 was checked; positive gains persisted for all three policies (additional gain ranges exclude 0.007966–0.009463; join 0.006168–0.009306; split 0.006039–0.008036). These alternatives were also calculated after the primary null result and are **exploratory**, not model selection on held-out data.

## Scientific conclusion and remaining falsifiers
**VERIFIED within scope:** the local four-class suffix-order predictive gain **does not disappear** after matching each folio's exact token-position and line-length marginals. The strict position-only/exchangeability explanation is CONTRADICTED for this frozen source and pipeline. Position-aware held-out models independently show added predictive benefit from the previous class. **Still UNKNOWN:** the underlying cause of the dependence, independent transcription-witness stability, original manuscript stroke/space fidelity, evidence for natural language vs cipher vs nonlinguistic generative process, and all five decipherment gates (0/5).

**Important loophole:** The strict null preserves exact position and line-length frequencies, but **does not preserve each individual line's multiset of classes** while permuting its position alignment. Different within-line class compositions (topics, line templates or scribal mechanisms) might still yield apparent adjacent dependence. A further null with simultaneous position-and-line composition constraints, and independent held-out sections/transcription witnesses, is necessary. Neither a small Monte Carlo p-value nor the five correlated folds proves semantics or decipherment. The 3 comma policies share data, and the six tests are correlated; p=1/1001 is finite Monte Carlo resolution, not theoretical p=0.

## Reproduction and evidence provenance
Original raw 6,000-null-draw output local SHA-256: **b73b77861c5a2f5d7acbc22a87862ea1c4046a4a09f89becc1ad250ec9100fcd** (full result JSON retained in conversation, not source corpus or scans). Script SHA-256: **0b3abea7a06a7c65c746d95f679a0c35a7243af452e1637810363cfa5c6a860b**. Secondary position-aware CV script SHA-256: **9ff2bb2f9a00abbbf352cc8cac395efafade3fa0d8e670fd9b77c66ca429600b**; result JSON SHA-256: **9c9f02b635f50d55ef30469198d391e148f64fc98876caba47d5cd0adb1e084f**. All calculations run locally; no new software installed, no live Yale manifest retry, no full transcription redistributions.

EXP-0018 follows EXP-0017, whose draft PR #25 was not merged when this test began. Place this report and program in a separate **stacked draft PR based on the EXP-0017 research branch**, then retarget to main only once PR #25 is approved/merged and cross-references are rechecked. Do not merge without owner authorization. Owner-canonical manifest D-0005 remains SATURATED for routine URL retries.


## Independent re-execution — 2026-11-13
A fresh Python/NumPy/Numba implementation of the same stratified Fisher–Yates and held-out sufficient-statistics scorer was run against the SHA-256-identified owner-uploaded ZL3b-n v3b and original evaluator. For all three comma policies, 1000 strict (folio x exact line length x exact offset) and 1000 weaker (folio x offset) permutations reproduced all six reported null means and maxima to displayed precision, all with zero exceedances. Primary strict mobilizable positions exclude/join/split = 27196/29294/31000, exact. No new software installation, rights expansion, primary image observations, translation, or decipherment gate. Q-020 identifies the antecedent positional question; new Q-021 tracks line-specific joint-margins/witness controls. This is a validation addendum, not independent semantic evidence.
