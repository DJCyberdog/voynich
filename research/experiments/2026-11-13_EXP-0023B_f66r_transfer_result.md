# EXP-0023B — f66r source-blind list-rule transfer: negative result and data-layer correction

**Executed:** 2026-11-13 Europe/Berlin. **Workflow:** RESEARCH_COMPLETED / WATCHING for a new independent physical image/transcription witness. **Evidence scope:** VERIFIED only for exact locally SHA-pinned ZL3b-n IVTFF editorial entries, script and stated controls; no cryptographic decipherment gate passed.

## Chronology: frozen before target content

1. User explicitly requested a genuine, predeclared target after the retrospective f57v/f49v experiment EXP-0023A.
2. Repository `main` at initial delta check: `c22853a259ef207514be3e538372bff4db1d153e`. Existing draft PR #38 selected as the single write destination; competing open PRs #27/#37 were inspected.
3. **Protocol commit before reading target values:** `26a031e396d781c713abc97be993332bb7128e4e` — `research/experiments/2026-11-13_EXP-0023B_f66r_transfer_prereg.md`. Fixed primary f66r, fallback f66v/f67r/f67v only if no eligible list, exact acceptance/rejection rules and 10k deterministic nulls.
4. **Executable script committed before reading target values:** `02ef00bc41716e759bf8e3404d9ef92feb5324e1` — `research/scripts/exp0023b_f66r_sourceblind_transfer.py`, Git blob `66f53fbdf2c1026fa7bdfa86f8fdc3ab0eba7c31`. Locally executed byte-exact same script, independently checked with `git hash-object`. No code changes after viewing target.
5. Source: owner-supplied original ZL3b-n v3b (2025-05-13; Zandbergen/Landini), **local SHA-256** `bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc`. The owner-canonical IIIF copy SRC-0007 is distinct from live Yale authentication; this study did **not** download images or access Yale's live manifest.

## Fixed target and initial executable result

Script automatically found an eligible `[@*+]L0` sequence on **the first and only tested folio, f66r** (source IVTFF line indices 1, 4–36, 39–49), 45 exact editorial units. It did not inspect fallback folios. Strict filter excludes units with explicit `[…]` uncertain-readings and preserves `@NNN;` as literal editorial labels, not decimal numbers.

The preregistration defined `[a-z]+` or `@NNN;` as a single standalone editorial *unit*, accidentally allowing **multi-character Voynich words**. This matters for the strength of the conclusion (next section); raw numerical results remain valid for the defined token list.

| Source-frozen prediction, f66r L0 units | Test | Accuracy | Negative control / comparative baseline |
|---|---|---:|---|
| R17 rigid cycle from f57v slots 18–34 | all 45 L0 units | **1/45** (2.22%) | 10,000 fixed-target-multiset permutations, 8,044/10,000 >= observed, p=0.804420 |
| R17 same positions 2–45 | 44 positions | **1/44** | Copy previous symbol **1/44**, global training-mode **1/44** |
| M5 five-unit motif from f49v first 14 values | 4 observed `o` anchors produce 16 subsequent positions | **0/16** | Copy previous on same 16 positions 0/16; conditional shuffle p=1.0 |
| Predeclared gate | R17 >70%, +3 hits vs BOTH baselines and p<=0.05; M5 >=8 predicted slots, >=75%, +2 vs copy and p<=0.05 | **Both FAIL** | Not a source-blind decipherment or a positive encoding signal |

Three in-program synthetic sanity checks passed. The preregistration also required a negative synthetic constant target; a separate independent post-result invocation of the **unchanged frozen evaluator** verified R17 34/34 on two exact copies of its 17-unit training template (positive) and 0/34 on 34 symbols absent from that template (negative). This supplement does not change decision thresholds or source-target results.

## Crucial audit: f66r is a three-column table, not a homogeneous glyph ring

A subsequent, honest reading of the folio's editorial layout showed that its 45 qualifying `L0` units are not 45 isolated glyphs. The initial part of f66r L0 contains full several-character Voynich tokens (e.g., source lines 1–15); only the later part represents mainly single glyphs and ligatures. The **Voynich Information Browser f66r description** explicitly reports three columns: leftmost single word/blank, middle single character or ligature, and right normal text: <https://vib.tamagothi.de/index.php?id=f66r&show=page>. René Zandbergen's writing-system inventory independently classifies f66r as marginal sequences of words **and** characters: <https://voynich.nu/writing.html>. More importantly, paleographic hand attributions differentiate f57v and f66r even though they share a bifolium. The structural mismatch is real and material.

**ERROR / LIMIT:** The preregistered matcher classified `[a-z]+` as a single `symbol`, conflating whole-word source units with single visible glyphs. Therefore **do not claim that the 45-unit negative result falsifies a glyph-wise universal key across physical folios.** It falsifies only this *specified, heterogeneous editorial L0-unit predictor*. This interpretation correction was made after the blinded numerical evaluation and is not a revised preregistration.

## Posthoc structural sensitivity — clearly not source-blind

After identifying the distinct column layout, isolate f66r IVTFF `[@*+]L0` entries whose original line index is >=16, using precisely the already-frozen source-symbol exclusion and *unchanged* R17/M5 model. **This was selected after inspecting f66r structure, so it is EXPLORATORY and cannot be counted as a second independent blind test.**

- 32 eligible entries (27 single-letter EVA units; 2 `@NNN;` editorial special symbols; 3 multiletter units/ligatures), within source region f66r.16–49, omitting uncertain readings.
- **R17**: 2/32 predictions correct; position-compatible score 2/31 versus 1/31 from copy-previous and 1/31 from global mode. The 10,000-shuffle upper-tail p = **0.472753** (null mean 1.564, max 7). No gate passed.
- **M5**: four observed anchors, 16 subsequent predictions, **0/16** correct; conditional shuffle p=1.0. No gate passed.
- The negative direction is unchanged but not independent confirmatory evidence; the revised layer is closer to a glyph/ligature column, still requiring direct manuscript images and independent editorial witnesses to validate segmentation.

## Alternative models and epistemic boundary

- **VERIFIED:** Exact SHA-pinned user-held source, script identity, fixed numerical results and synthetic controls for this IVTFF filter. Specific R17/M5 cross-list transfer criteria failed, even after unblinded data-layer sensitivity.
- **DOCUMENTED:** Manuscript specialist descriptions of f66r's three distinct columns and the distinction between word and sign sequences, cited above. Different page-hand assignments on f57v vs f66r are documented at site level, not independently palæographically authenticated in this run.
- **CONTRADICTED:** The *narrow model claim* that the f57v's 17-unit sequence and f49v's specific 5-symbol motif apply unchanged to f66r L0 editorial sequence with prescribed accuracy and coverage; **not** the existence of codes, local cyclic rings or natural language.
- **INFERRED:** Copy-and-edit, scribal layout, and change of section/hand/representation are credible explanatory alternatives. No specific generator is proven by this failure.
- **UNKNOWN:** True manuscript-level glyph identities at uncertain positions, independent transcription agreement, reversible key, semantics, manuscript origin and any accepted decipherment gate (still **0/5**).

**Next independent gate:** Before looking at another genuinely unseen list, require physically comparable *single-glyph* regions identified from images by independent readers, freeze alternate-transcription alignment, choose a separate withheld folio and a nonsemantic matched-parameter copy-edit comparator. Do not rescue this result by selecting only flattering parts of f66r, switching codings post-hoc or retesting the same folio as if still blind.

No full original transcript, glyph image, font or third-party code redistributed. No new package/install or paid API used. No other repository or automation modified. This report is Draft PR #38 only, unmerged; main progress ratios remain 213/213 owner-canonical canvas IDs and 0/5 accepted decipherment gates.
