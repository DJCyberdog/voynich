# EXP-0002 — Physical foliation is not a digital canvas index

Date: 2026-11-05. Status: RESEARCH_COMPLETED (bounded source-structure test). Scope: codicological source-model prerequisites, not decoding.

## Question and selection
Can a digital canvas count be used without additional mapping as a physical manuscript leaf/folio count for MS 408? Prior memory RM-001 and Q-001 flag an unresolved canvas/folio problem. Avoid leaking wrong location identities into text statistics.

## Sources, provenance, and observations
SRC-0006: Yale Beinecke's own pre-1600 catalogue entry, https://pre1600ms.beinecke.library.yale.edu/docs/pre1600.ms408.HTM, accessed 2026-11-05. Section 'Parchment' (web display lines 34-46) describes 'ff. 102 ... + i (paper)' and five double, three triple, one quadruple and one sextuple folding leaves. It says not every leaf is foliated and collating is difficult because folding leaves are not consistently foliated. Several leaves are missing, identified by folio numbers and quire descriptions.
SRC-0002: Yale Beinecke overview https://beinecke.library.yale.edu/beinecke/collections/beinecke-cipher-voynich-manuscript, accessed 2026-11-05, directs readers to the detailed foliation catalogue and says high-resolution complete-manuscript images are available.
SRC-0005: Official Yale manifest lead https://collections.library.yale.edu/manifests/2002046; direct access in this tool returned HTTP 403. No canonical canvas identifiers/count/ordering/labels were verified.

## Competing hypotheses and predeclared discrimination
HYP-0002a (naive): a digital canvas index can be substituted for a physical foliated-leaf index without a mapping table; a unique 1:1 identity follows from the manuscript's foliation.
HYP-0002b (alternative): canvas is a representation unit and may include fold-out views, covers or other scans, whereas the physical catalog concerns leaves, folds and historically incomplete foliation.
Prediction for HYP-0002a: every image index has a unique historically stable leaf number, and all physical leaves have exactly one numbered face in the same identity system; no unnumbered or multi-surface cases.
Positive control: Beinecke supplies explicit physical leaf and historical folio descriptions that can be cross-referenced; source entry verified.
Negative control: unnumbered or inconsistently foliated folding leaves documented by the catalogue invalidate universal unique numbering.
Null model: numbers from distinct layers have no assumed equality without an independent image-to-object concordance.
Falsification criterion: authoritative evidence of unnumbered/ambiguous foliation is sufficient to reject universal direct identity, but NOT to establish any particular digital canvas count.

## Test and outcome
On reading Yale's institutional catalog, the positive source confirms physical leaves and missing/complex folds; the negative control is present: not every leaf is foliated and folding leaves pose inconsistent assignment. Hence **CONTRADICTED** only for the universal identity/numbering assumption HYP-0002a; **DOCUMENTED** for Yale's catalog descriptions. **INFERRED**: a mapping table is mandatory before image-linked text research; exact mappings and all manifest counts remain **UNKNOWN**.

## Limits and next test
No actual Yale IIIF manifest was fetched; no complete physical-image concordance or image count was measured; no manuscript glyph transcription was read. A later source or image system may offer a perfectly valid explicit canvas-to-leaf map; that would confirm HYP-0002b's need for explicit mappings, not rehabilitate the naive identity assumption. Next: get verified official manifest with IDs, labels and order; design distinct object/folio/face/surface/canvas records and withheld mapping spot checks. No corpus material was copied.
