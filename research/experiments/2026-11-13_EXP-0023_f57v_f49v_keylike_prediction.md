# EXP-0023 — f57v/f49v: do key-like glyph lists predict unseen positions? (2026-11-13)

**Status:** RESEARCH_COMPLETED for a *retrospective, algorithmically masked* transcription test; **NOT** blind manuscript decipherment. Workflow **WATCHING** pending independent glyph/witness replication. No accepted decipherment gate (0/5).

## Question and potential falsifiers

Can the sequence structure visible in the ring of MS 408 f57v and in f49v's marginal column predict characters *not supplied to the algorithm during fitting*? Competing mechanisms: a rigid periodic code/template, local copying of an exemplar, nonsemantic circular/onomantic notation, editorial transcription effects, and unknown linguistic/cipher/hybrid constructions. **Do not interpret a repeated glyph inventory as a byte encoding, numeric radix, alphabet key, word translation or semantic mapping.**

This is **not a newly preregistered confirmatory analysis**: both lists had been publicly described, and the investigator saw full source descriptions before fixing these code tests. The locked computational splits protect the program from outcome leakage but not the researcher's choice of candidate mechanisms. The figures are diagnostic and falsify *these fixed operational rules only*.

## Data and provenance

- Manuscript: Yale Beinecke MS 408; f57v circular glyph ring and f49v column. Owner-designated canonical working IIIF snapshot SRC-0007 (SHA-256 pinned in project), **not independently live-Yale authenticated**. No live manifest retry.
- Full independent local byte hash of previously owner-provided Zandbergen/Landini ZL3b-n v3b IVTFF (13 May 2025) **bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc**, already indexed as SRC-0101. No manuscript transcription or images redistributed.
- ZL3b-n locus `<f57v.3,+Cc>`: **68 dot-delimited transcription units**, arranged as **4 × 17** when grouped at the four repeated starts. Several symbols use editorial `@NNN;` forms, and `[d:j]` is an ambiguous reading. **These are transcription units, NOT 68 independently authenticated manuscript glyphs.** A 2026 secondary study describes 4 × 18, a segmentation discrepancy requiring a direct image/independent witness adjudication.
- f49v `@L0`/`*L0`: **26** marginal symbols alongside 26 text lines. The separately written Western **1–5** numerals next to lines 2–6 are *not* the EVA values of those marginal symbols; the two columns must not be conflated. VIB Stolfi/Takahashi witness has disagreements at some isolated symbols (notably line 15 and 24). Sources: SRC-0047 (f57v), SRC-0048 (f49v).

Data layers: image/canvas → visible strokes (not reverified) → editorial IVTFF glyph names (frozen) → dot or left-margin segmentation (frozen) → sequence statistics. No linguistic interpretation.

## Frozen deterministic algorithms

Python 3 standard library only; program `research/scripts/exp0023_f57v_f49v_prediction.py`, `--input` user-held ZL3b-n file. Reject input with wrong SHA. Detect and assert exactly 68 ring units and 26 left-margin markers. No source string or glyph image is embedded in code.

**A. f57v, full-position test.** First 34 units (two complete 17-slot sectors) for training; remaining 34 for evaluation. Search lag 2–20, requiring at least 14 training comparisons, maximize exact-match fraction (then match count, then shorter lag). Freeze final lag-length training template, tile without any heldout feedback over all 34 heldout slots. Positive control: self-evident periodicity; negative/random-order control: 10,000 deterministic within-heldout permutations, preserving its symbol multiset. Benchmark is explicitly weak against the **copy-previous-sector** alternative.

**B. f49v, fixed global period test.** First 14 labels for training; positions 15–26 held out. Search lags 2–9 requiring at least five training comparisons, then tile last lag template over all 12 targets, with no feedback. If the period prediction collapses, reject this exact fixed-template explanation, not arbitrary periodicities.

**C. f49v, local-copy motif.** Within the first 14 labels, scan nonoverlapping near-repeat pairs of length 3–8, same first label, Hamming distance ≤1; deterministically choose longest, fewest mismatches, latest second occurrence. The second occurrence becomes the frozen motif. Only after observing an anchor matching its first label in the holdout, predict the *following* motif positions. The anchor itself is NOT predicted; report coverage. Conditional negative control: shuffle the other 11 heldout symbols 10,000 times while fixing the observed anchor. A first-order conditional predictor using the immediately observed preceding heldout glyph is a looser descriptive baseline, **not** a strict frozen whole-block comparator.

## Actual observations

| Test | Learned structure | Evaluation | Hits | Scope |
|---|---|---:|---:|---|
| f57v fixed lag | 17, trained at 15/17 matching lagged pairs | 34 positions (cycles 3/4) | **32/34 (94.12%)** | Two mismatches at full-ring positions **43 and 60**, both relative slot **9**: template has `f`, observed `p`. Each of the last two sectors independently 16/17. |
| f49v fixed lag | 8, trained at 4/6 matching lagged pairs | 12 final positions | **0/12** | Strong heldout failure of a single rigid 8-period positional cycle |
| f49v found near-repeat | 5 labels, initial occurrences at positions 2 and 10, differing in 1 slot | 4 positions after observed `o` anchor at position 17 | **4/4** | Predicts positions 18–21, but covers only **4/12 = 33.3%** of test slots and **does not predict anchor placement** |
| f49v first-order control | preceding symbol from 14-unit training dictionary; uses actual prior holdout symbol | 12 sequential positions | **6/12** | Not a wholly frozen block forecast |

For f57v, 10,000 random rearrangements of the heldout list (same symbol multiset) averaged **2.1485** positions matching the lag-17 template; maximum **10**; zero rearrangements matched or beat 32 (**Monte Carlo resolution p = 1/10001 ≈ 0.000100**). This demonstrates nonrandom *sequence alignment under that simplistic shuffle null*, not encryption or independent manuscript confirmation. The count excludes methodological selection and is **not a confirmatory p-value**.

For f49v, the conditional 10,000-shuffle control of four motif positions after keeping the `o` anchor fixed averaged **0.6334** matches; three shuffles matched all four, giving **p = 4/10001 ≈ 0.000400**. This control does **not** penalize the retrospective selection of the motif or anchor and therefore is exploratory only. The global-period rule's zero-match outcome had shuffle-control upper-tail p=1 and cannot support a fixed-period code.

**Independent arithmetic/parser spot check:** a second short implementation separately read the exact source loci, confirmed 4×17 and 26 markers, fixed-lag counts 16/17 for each of two heldout sectors, source motif start indices and 0/12 for period eight. This is **same-input algorithmic reproduction**, not independent textual paleography or separate transcription witness.

## Inference and status

- **VERIFIED (within pinned local IVTFF and exact parser):** ring's strong 17-slot recurrence and 32/34 retrospective position forecasts; f49v's 0/12 out-of-sample collapse of globally learned 8-period template; 4/4 conditional glyph forecasts within one discovered five-symbol motif. Code, deterministic seeds and aggregate JSON support replay.
- **DOCUMENTED:** VIB editorial transcriptions describe ring repetition, f49v marginal glyphs and distinct accompanying Western numerals; second-source witness readings are not identical.
- **CONTRADICTED (narrow):** a uniformly fixed 8-position copying rule for the last half of f49v based on first-half fitting.
- **INFERRED:** a varying-gap local-copy process is adequate for observed f49v motif and sector copying adequate for f57v. This is an explanation of **surface repetition only**, not proof of historical author method.
- **UNKNOWN:** whether the symbols form a key, an alphabet, a radix, a homophonic substitution, a meaningful calendar/onomantic table or merely an ordered list; glyph-level identity in ambiguous slots, true 17/18 segmentation, cross-folio predictive generalization, all semantic/linguistic/decipherment criteria.
- **Strongest alternative:** deliberate copying of a familiar sequence during production of a reference circle, with occasional substitutions/insertions and editorial classification of strokes. It makes the same observed predictions without a reversible encoding. The one repeated margin motif is likewise compatible with copy-and-edit.

## Truly prospective next gate (not run)

Before inspecting any additional key-like list or alternate image-linked witness, **freeze a predicted glyph mapping**, score minimum coverage and accuracy against a conservative copy-and-edit null and independent transcribers, and check unseen loci, e.g., a rights-reviewed f66r margin sequence. Alternatively require a frozen rule from f57v that predicts specific distinct *new* characters or mappings on f49v/f66r without observing their anchor positions. A model that merely repeats a visible sector cannot fulfill manuscript reading/script/semantics acceptance gates.

**No owner-authorized merge requested for this new independent PR.** Keep integrated README denominator 213/213 owner-canonical canvas IDs and 0/5 decipherment gates; this draft does not count as integrated research. No automation, other repository, source licensing or permission changes.
