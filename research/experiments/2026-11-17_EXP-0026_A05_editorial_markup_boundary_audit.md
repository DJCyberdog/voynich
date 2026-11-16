# A-05 / EXP-0026 — editorial markup boundary adversarial parser audit (2026-11-17)

**One bounded question:** Does the already frozen EXP-0026 parser's treatment of editorial markup guarantee that it never creates a new "certain" ASCII EVA token across a removed inline markup span? Priority P0 A-05: the existing significant heldout q-onset result relies on first-token length and certainty; false certainty can change its operational null. This is a **synthetic code-level adversarial falsification**, not a second manuscript experiment. Actual main `5ca7cfc9b43ec820d99292d87c784990e0266c64`, existing only open draft PR #62, same source file and report already integrated on main. All required governance/memory and 40-claim queue/protocol consulted; no new EXP ID, HYP, or manuscript claim.

## Pre-specified test of the parser contract

Frozen implementation: `research/scripts/exp0026_a05_folio_root_q_test.py`, SHA256 of the original local frozen source as documented by EXP-0026: `846317ffb86373cbc36b81c8e345a12d044b010a2b8c0e66c99949184a7ea6c1`; relevant lines in `tokenize`: `COMMENT.sub('', body)`, then explicit `<->` and `<~>` replaced by dots, then `MARKUP.sub('', body)`, then dot split and `CERTAIN.fullmatch` filter.

**Test prediction:** For a token with an internal unrecognized markup span, removal must NOT make two otherwise separate or uncertain alphabetic fragments a single certain token. **Strongest counterhypothesis:** The IVTFF witness never contains such a span in eligible `+P0` rows, so the behavior, while real, never affects the published result.

**Synthetic adversarial input and result, independently checked by literal JS equivalent of the exact regex transformations, NOT by running the frozen Python script on the original corpus:**
- `abc<unc>def.qqq` -> `abcdef.qqq` -> first token `abcdef` **accepted as certain** (length 6), whereas markup boundaries were not authenticated as contiguous manuscript strokes.
- `abc<!editorial>def.qqq` -> same `abcdef.qqq` (comment stripping likewise concatenates).
- **Positive delimiter control:** `abc<->def.qqq` -> `abc.def.qqq` -> three certain tokens; intended explicit separator works.
- **Additional delimiter control:** `abc<~>def.qqq` -> `abc.def.qqq` -> three tokens.

These are **synthetic strings, not claimed attested IVTFF markup syntax or manuscript observations**. The source-level implication is a general boundary-safety failure if the real input permits inline tags or comments between ASCII fragments. **Code behavior: VERIFIED in this bounded equivalent-regex test; real source prevalence and impact: UNKNOWN.** This cannot retrospectively change the frozen confirmatory result, nor justify an invented correction of 677/69/99.7857/p-value. The published EXP-0026 numerical result remains a correctly described result **conditional on the exact frozen parser**, not an independently established physical-line effect. Any new parser would require new preregistration, an independent rights-cleared witness or explicitly exploratory labeling, and a previously unexposed holdout.

## Falsification controls and next gate

**Positive control** above must fail closed or preserve a boundary for unknown markup. **Negative control** explicit `<->` and `<~>` must continue to split. **Null**: no unknown inline markup occurs in any eligible original lines; then observed published statistics are unchanged by a fail-closed fix. **Heldout**: prospective independently licensed transcription witness and untouched folio roots; the prior EXP-0026 20 test roots are **no longer unseen** and cannot be reused as new confirmation. Do not inspect the original heldout lines before freezing a new protocol.

**Actual original data check:** NOT RUN — owner-held 411,671-byte `ZL3b-n.txt` with SHA256 `bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc` not available via GitHub; no manuscript image or separate independent transcription was inspected. This audit does not assert any specific markup occurs in the original witness. **Rights:** no transcription or manuscript pixels copied. SRC-0007 IIIF manifest is Owner-canonical but not independently live-Yale authenticated; no live request.

**Decision:** a **conditional implementation safety invariant is CONTRADICTED**, but **A-05 manuscript-level status remains UNKNOWN / ACTIVE / TESTED / OPEN**; EXP-0026's frozen result is not retracted or re-run. No decipherment gate (0/5) changes, A/W closures remain 3/40. Do not promote synthetic parser behavior to manuscript observation. **Reentry:** independently determine whether the pinned source has any eligible inline markup patterns; if none, close this implementation concern as non-impacting; if present, preregister and compare conservative parser on a fresh independent heldout and report any quantitative change without retroactive p-value reuse.
