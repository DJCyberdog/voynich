# v0.6.0 — local IVTFF transcription alignment baseline

This release integrates the private v0.5.1 reference importer and adds a conservative text comparison layer. Existing CNN, glyph classifier, local queue and opt-in GitHub bridge are unchanged. No new remote job type or upload route. All source PDFs, extracted images, transcriptions, models, observations and detailed reports remain private. The reference preview remains a subset, not an independently validated glyph inventory; aaa is not included. K-0001 remains deferred; EXP-0038g remains NOT_MET. No new image-to-locus match or decipherment claim.

## Supported notation and source audit

`alignment.py audit SOURCE EXPECTED_SHA256` accepts UTF-8 IVTFF 2.0 M files with header `Eva-` or `STA1`. It recognizes numbered regular and Rosetta (`fRos`) loci, retains exact locus/subtype, rejects duplicate loci and unknown record syntax, and counts page metadata separately. The restricted lexical parser strips only leading `<%>` and trailing `<$>` and removes unambiguous dots for a **notation-sequence comparison**, not word-boundary evaluation. EVA is tokenized as lowercase ASCII letters, apostrophe, `@NNN;` and brace-delimited sequences. STA1 uses two-character A–X family codes. This is lexical validation only, not proof each code is an authentic glyph or that braces equal physical units. Commas, square-bracket alternatives, unknowns, additional tags and unsupported notation are reported as unresolved; no default reading or fuzzy cleanup is applied. No cross-convention conversion is inferred. Use native files, not an interchange file with another header.

Three exact owner-supplied sources were recovered and verified:

| File | SHA-256 | Loci | Strict | Unresolved |
|---|---|---:|---:|---:|
| ZL3b-n.txt (EVA M5) | bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc | 5385 | 2161 | 3224 |
| ZL3b.txt (STA1 M5) | 8438ba1c45f47fe1d06b5262cbcdf60ce69158a0edbd4dd802612896f3217e2a | 5385 | 2772 | 2613 |
| GC2a_1.txt (STA1 M6) | 0c0d1eea4b5ab87f8a65fb7f4346864cd90758ad993812b4f2122b3899d4ac88 | 5367 | 3733 | 1634 |

`audit-common --source FILE SHA --source FILE SHA ...` gives aggregate overlap: 5,366 common loci with matching subtypes; 1,691 strict in all three. These are **parser eligibility counts**, not evidence of reading agreement, independent observations, or model accuracy.

## Prepare observations (only explicitly mapped complete loci)

Use a v0.5 glyph predictions JSON, its model JSON and alphabet JSON. The alphabet convention must be the exact source header (`Eva-` or `STA1`) for model labels to be accepted. A physical mapper must review the crop and declare which complete locus it depicts. Do not use string similarity to establish the mapping. For partial crops and uncertain page/panel mappings, retain `mapping_status: tentative` or `scope: partial`; these do not get scored. The mapping JSON pins the source, manifest, predictions and inventory. Example schema (illustrative hashes and values only):

```json
{"source_sha256":"<actual transcription SHA256>","scheme":"STA1","manifest_sha256":"<actual manifest hash>","prediction_sha256":"<actual prediction hash>","alphabet_sha256":"<actual alphabet hash>","regions":{"R001":{"page":176,"group":"<verified physical-leaf group>","locus":"<verified locus ID>","subtype":"<exact IVTFF subtype>","mapping_status":"confirmed","scope":"complete_locus","mapper":"<mapper ID>"}}}
```

Every manifest region must be accounted for, including rejected or tentative mappings. The adapter verifies crop hashes, model/inventory binding, page/group declarations, box bounds and non-overlap. It orders the existing single-line boxes left-to-right; it cannot infer multi-line, circular or nonstandard reading order. Mapping confirmation is a human declaration, not proof of physical identity. Use only independently reviewed full single-line regions with established reading order.

```powershell
$P = '.\.venv\Scripts\python.exe'
& $P alignment.py prepare manifest.json predictions.json alphabet.json glyph_model.json mapping.json ZL3b.txt 8438ba1c45f47fe1d06b5262cbcdf60ce69158a0edbd4dd802612896f3217e2a observations.json
& $P alignment.py compare ZL3b.txt 8438ba1c45f47fe1d06b5262cbcdf60ce69158a0edbd4dd802612896f3217e2a observations.json comparison.json
```

For human corrections add `--review owner-review.json --references references.json --catalog-scheme sta1` to prepare (or `eva-from-sta` for `Eva-`). It verifies the original review session bindings and candidate IDs. Human mapped labels are used only in that explicit convention; unsupported notation remains unknown. False positives are excluded with an audit record; compounds block region comparison; unresolved/absent classifications remain unknown. A model in another convention supplies no labels for the target convention. No automatic conversion from historical EVA2 `&...;`, FSG, etc. The active review queue still covers unknown predictions only. Previously accepted model predictions are not independently confirmed by this adapter.

The observation JSON can also represent explicitly reviewed candidate alternatives as `candidates` arrays, e.g. `[["ch"],["o","a"],[]]` for EVA. Each inner array is a set of alternative readings for one image box, not a confidence distribution. An empty inner array means unresolved. Alternative observations edited outside the adapter require independent provenance review; the comparator checks declared hashes and notation but does not independently authenticate human decisions. Unknown units never earn exact-match credit. A single candidate may consume several target notation units (e.g. `ch` consumes `c,h`); braces remain atomic in the parser. Edit cost 1 per missing/extra/substitution/unknown observation step, 0 for an exact candidate span. Costs are engineering defaults, not calibrated probabilities or standard character error rates. Equally optimal paths are marked ambiguous and no arbitrary path is emitted. Matching an alternative is distinguished from unambiguous exact agreement. Outputs are local, immutable by default, and UNADJUDICATED. Duplicate loci are not claimed independent (unique-compared-loci count included).

## Validation

Run all tests with `EVA_REFERENCE_PDF` and `VOYNICH_TRANSCRIPT_DIR` set to the private original inputs. Linux CPU/Xvfb suite: 44/44 PASS including five new alignment tests and actual pinned source audit. The actual sources were parsed, not used as ground truth for an image recognition score. Synthetic tests exercise input rejection, ambiguity, span matching, missing/extra/substitution/unknown, full-locus mapping gate, model provenance and human review/false-positive integration. No accepted real physical locus mappings, model calibration, Windows/CUDA or live GitHub API acceptance. Multi-line/circular order, full IVTFF editorial grammar, word boundaries and independent manuscript validation remain open. No raw source text in GitHub.
