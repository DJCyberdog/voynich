# EXP-0007 — Does the author's pinned ZL3b-n v3b witness independently contain a separated pchor at f2v.1?

Date: 2026-11-05. Bounded primary-transcription source audit; not a manuscript-image reading, parser reproduction, or semantic validation.

## Prior state and falsifiable scope
EXP-0004 found no standalone pchor in a *different* VIB Currier C witness and EXP-0005 corrected confusion between raw and derived qokedy. EXP-0006 identified ZL3b-n v3b as Franke's own designated FDM reference, but had not read it. New question: does that exact primary **transcription source** expose pchor with a punctuation boundary at f2v.1? This is a comparison of two transcription witnesses, not a claim that one is universally correct.

## Immutable leads and source provenance
SRC-0016: René Zandbergen/Gabriel Landini, ZL3b-n.txt, direct origin https://www.voynich.nu/data/ZL3b-n.txt , accessed 2026-11-05, visible header `#=IVTFF Eva- 2.0 M 5` and `Version 3b of 13/05/2025`, f2v header and f2v.1–8 lines. The full origin bytes were not downloaded and independently hashed in this run. An independent public registry SRC-0018 reports 411671 bytes and SHA-256 `bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc`; this is **CLAIMED**, not a locally reproduced checksum. The owner-canonical Yale manifest SRC-0007 was not reauthenticated or replaced. No image was inspected.
SRC-0017: Origin author's site legal notice https://www.voynich.nu/roadmap.html#cop (site map legal section), accessed 2026-11-05, permits free use of site material with requested attribution, but font has separate conditions; do not conflate transliteration with font/image rights. Original site's data README https://www.voynich.nu/data/000_README.txt describes IVTFF and multiple conventions.
SRC-0018: third-party release registry https://depot.quantumlynxresearch.com/releases/88e258d1-cccb-4ad1-ae2a-e91c3d31b9bf ; version/date/checksum and CC0 classification are registry claims; not independent original-site CC0 legal verification.

## Hypothesis, adversary and predeclared checks
HYP-0007: The pinned ZL3b-n v3b line f2v.1 **contains an explicit comma-delimited pchor sequence** distinct from the preceding `cheo` characters, unlike the older VIB witness rendering `cheopchor`.
Strongest alternative: comma is a transliterator/editorial uncertain-space marker rather than unambiguous manuscript word boundary; the two witnesses may differ only in segmentation and still depict the same underlying strokes. This source-level observation cannot independently establish raw glyph boundaries.
Prediction: the origin file must identify version 3b and show f2v.1 containing `cheo,pchor` rather than uninterrupted `cheopchor`.
Positive control: origin f2v.2 explicitly contains `shol`, and f1r.1 also contains `shol`; confirms folio and locus indexing and some ordinary recognizable EVA.
Negative control: do not count a mere substring in a contiguous word as a distinct token; do not assume comma means certain word break without IVTFF syntax specification.
Null model: distinct editors may encode different boundaries for the same visible glyph sequence; semantic claims do not follow from punctuation.
Held-out: f3r and all later folios reserved for future parser and semantic tests; no fitting or analysis performed on them.

## Observation / result
Direct origin text f2v.1 has `kooiin.cheo,pchor.otaiin,odain.chor<->dair.shty`. It **does** have comma directly before pchor. VIB Currier C previously displayed `cheopchor`. Therefore the strong generalization 'no pchor in Franke's pinned raw transcription' is **CONTRADICTED**. The narrow documentary prediction HYP-0007 is **DOCUMENTED** in origin source. However whether comma is an independently justified physical word boundary is **UNKNOWN** until exact IVTFF convention and manuscript image are compared. This is a source witness discrepancy, not a proof that Franke's medical meaning, repetition counts, or parser work.

The origin f2v.1–8 text has no visibly literal qokedy sequence, but EXP-0005 established that derived system outputs may differ from raw tokens. No assertion about derived counts or dosage is made. No corpus frequency computation. No new decipherment, language, semantics, or origin claim.

## Next
Freeze complete origin bytes and calculate independent SHA-256; inspect the primary IVTFF punctuation/space rules for comma, dot, and `<->`; compare same locus against canonical owner-manifest f2v canvas image and an independent witness without treating punctuation as glyphs. For functional output require frozen parser contract and blind tests. Attribution to Zandbergen and Landini; no full transcription copied to repository.
