# EXP-0005 — Layer correction and competing parser-rule matches (2026-11-05)

## Scope and provenance

One bounded DOCUMENTARY source-revision experiment, not a held-out decipherment or a corpus-frequency test. Question: does the f2v raw-EVA/token mismatch in EXP-0004 independently refute the Eschede model, and is the subsequently disclosed raw-to-system parser fully deterministic from the currently published rule table?

Sources, accessed 2026-11-05:
- SRC-0008: Tobias Franke/Celler Presse 2026-09-27 f2v example, originally represented with `pchor` and 2x/3x `qokedy`.
- SRC-0009: VIB / Currier C f2v.P.1–P.8 transcription witness (EXP-0004; not reclassified as direct glyph evidence).
- SRC-0010: Franke, 'Methodisches Addendum & Transparenzbericht', version 1.1, published October 4, 2026, https://celler-presse.de/forschung/dokument/methodisches-addendum-transparenzbericht-vom-rohen-eva-text-zur-funktionalen-system-synthese-folios-f1r-f78r/ . States that formerly shown parameter chains were **not raw/diplomatic EVA** but computed system-parsing outputs, and calls that impression a methodological presentation error. Document specifically discusses f1r/f78r, not verified f2v transformation trace.
- SRC-0011: Franke, 'Das formale, maschinenlesbare Regelwerk (P-01 bis P-20)', version 1.1, published October 4, 2026, https://celler-presse.de/forschung/dokument/das-formale-maschinenlesbare-regelwerk-p-01-bis-p-20/ .
- SRC-0012: Franke, 'Das deterministische Parsing-Protokoll (Beispiel Folio 1r, Zeile 1)', version 1.2, published October 4, 2026, https://celler-presse.de/forschung/dokument/das-deterministische-parsing-protokoll-beispiel-folio-1r-zeile-1/ . Explicitly maps raw `shol` to output `qokedy` via P-12.

## Prediction/competing interpretations (declared before examining rule overlap in this cycle)

HYP-0005a: A raw Currier-C word mismatch alone is adequate to reject the alleged system-token computation. Counterhypothesis HYP-0005b: at least some system labels can arise from dissimilar EVA tokens via deterministic mappings, so raw absence is expected; only a falsifiable source-to-parser-to-output trace can test computation. Positive control: a public worked example `shol` → `qokedy` proves the author actually describes a layer conversion. Negative control: `shol` must not be silently equated with a raw `qokedy` glyph sequence. Null model: arbitrary many-to-one symbolic recoding carries no demonstrated semantic content absent independent constraints. No independent holdout used here; this is exploratory source-method audit.

### Actual observation and scoped result

The author's October 4 addendum explicitly distinguishes raw EVA from parameter outputs and acknowledges misleading earlier presentation. His f1r worked example maps `shol` via P-12 to `qokedy`. Thus **CONTRADICTED** for HYP-0005a's claim that a raw-string mismatch *by itself* rejects all possible computed outputs. Prior EXP-0004's actual data (no standalone raw `pchor` or `qokedy` in VIB Currier C f2v) remain valid as a narrow raw-text observation, but **do not prove parser failure**. As of this cycle no f2v byte-for-byte parsed output was independently reconstructed, so f2v model fit remains **UNKNOWN**.

### Second test: overlapping stated rule conditions

The published version 1.1 table contains:
- P-12 `(ol|ory|edy)$` → `qokedy`, which matches raw token `shol` (suffix `ol`).
- P-17 exact lookup `[shol, otch]` → 'Catalysis status', which **also matches the same token `shol`**.
- P-02 `^qo.*` → 'Control parameter' and P-12 `(ol|ory|edy)$` → `qokedy` overlap on a token such as `qokedy` itself.

A single token triggering two distinct rules is VERIFIED by direct reasoning over the published patterns (no source corpus or code used). The f1r *worked* example selects P-12 for `shol`, but the publicly inspected table does not itself specify a general precedence, whether multiple outputs can co-occur, evaluation order, or context-specific exceptions for all such collisions. This is **DOCUMENTED as an incompleteness of the inspected published specification**, not a proof that Franke has no working software or that the full model is logically impossible. The strongest rescue is an elsewhere-published fixed rule priority, context gating or deterministic multi-label output; request an unambiguous trace for f2v/f1r, complete formal tie-breaking and a frozen parser version.

## Decisive prospective next experiment (NOT performed)

Lock the raw transcriber/version and line/word positions on f2v using canonical SRC-0007 labels and compare original image where allowed. Pin the parser as source or exact formal rules, including precedence, combination, tokenization and context. Given raw inputs, predict all intermediate outputs including counted `qokedy` runs; negative control shuffle folio/section tags; null model many-to-one generic grouping; hold out other folios, independent replicate. Reject only preregistered exact output failures. Medical semantics and historic authorship require separate blind tests.

## Consequences

HYP-0004 remains **CONTRADICTED** narrowly as raw f2v-token equivalence within a named witness but its strong interpretation must be *downgraded*: absence of an output token in raw EVA is not a relevant direct falsification of the newly clarified parser. Add independent HYP-0005, and record that rule-conflict resolution for full determinism is currently **UNKNOWN**. No large transcript copied, no unapproved third-party code, no image download or asserted translation.
