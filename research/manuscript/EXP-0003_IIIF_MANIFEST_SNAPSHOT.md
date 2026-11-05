# EXP-0003 — User-supplied Yale IIIF manifest snapshot: canvas structure and exceptions

Date: 2026-11-05. Material artifact: user-provided Markdown fenced JSON, filename `Eingefügtes Markdown(3).md`, local full-file SHA-256 `4aa05eb43637b15ce68ba3fa15eb2d2e69dccd65cc46a31e84f80e89cd1e155e` (403041 bytes). Inner JSON SHA-256 (UTF-8 with Markdown fences removed and stripped) `317d58fd9ea90392a83d9858a91eada3d0b41416a3c835857dc0154bd123a309`. Claim of origin: https://collections.library.yale.edu/manifests/2002046. The live official manifest continued to return HTTP 403 to this agent; **the submitted bytes were not independently authenticated as the live Yale response**. Do not imply live fetch succeeded.

## Question / alternatives

Can a supplied IIIF Presentation 3 manifest establish an internally consistent canvas inventory and exceptions needed for a folio concordance? HYP-0003 (testable, narrowly scoped): every canvas bears a unique simple single-side folio label, and historical foliation can serve as a direct canvas index. Alternative: independent IIIF canvas IDs exist and labels include covers, non-leaf views, compounds and repeated partial views. Null: no guaranteed 1:1 identity, pending checked labels and source authentication. Test on *all* supplied items, no holdout needed for a deterministic schema census; confirmation on new independently fetched manifest remains blocked.

## Reproducible parsing of supplied snapshot

Strip exactly outer Markdown code fence, trim boundary whitespace, parse JSON. Assert `type=Manifest`, `id=https://collections.library.yale.edu/manifests/2002046`, `items` array. For each Canvas, extract `id`, `label.none[0]`, image AnnotationPage and painting image URL, and dimensions; do not download media. Count items; classify each label with strict regex `^[0-9]+[rv]$` as simple; labels starting `[` as descriptive/non-folio; remaining as composite/part/foldout. Count repeated labels. SHA-256 of raw attachment and inner JSON pins supplied bytes.

**Results, VERIFIED only as parsing of supplied artifact (not independently verified live Yale data):**
- 213 `Canvas` records, 213 painting annotations, 213 distinct canvas IDs; 210 unique label strings.
- 183 plain labels `number + r/v`; 21 compound/part/foldout labels; 9 bracketed descriptive labels (covers, flyleaves and edges).
- Duplicated label strings: `70v (part)`, `72v (part)`, `102v (part)`, each occurs twice. This is not a duplicate canvas ID.
- Examples: canvas image IDs `1006074` = `[Front cover]`, `1006075` = `[Inside front cover]`, `1006076` = `1r`, `1006077` = `1v`; `1006199` = `69v and 70r`; `1006231` = `85v and 86r (foldout)`; `11868210` = `[Spine]`. The image IDs are not consecutive throughout.
- `11v` is followed by `13r` in the ordered items; no `12r` or `12v` entries, consistent with the Yale physical catalog's missing f. 12, but this agreement is **INFERRED**, not independent image verification.
- No exact simple `59r/59v`–`64r/64v` labels, consistent with the physical catalog's missing leaves 59–64.
- Source metadata states `Extent of Digitization: Completely digitized`, `Access: Public`, and includes a rights warning that use **may be subject to copyright, site licence and other terms**. Public access does not by itself permit unrestricted redistribution.

## Controls / falsification

Positive control: ordinary sequential `1r` and `1v` each have discrete canvas IDs. Negative control: unnumbered `[Front cover]` and repeated `70v (part)` plus compound `69v and 70r` each refute universal 1:1 folio-label mapping. Falsification criterion for HYP-0003: any duplicate, non-folio or composite label; multiple explicit counterexamples found, so HYP-0003 is **CONTRADICTED** for this snapshot. Strongest rival: a curated concordance can still unambiguously relate each canvas to physical leaves and parts; not tested here.

## Evidence limitations and follow-up

No image pixels, original manuscript observations, transcription, OCR or statistical text analysis were used. `items.length=213` is a count **within the provided snapshot**, not an independently verified live Yale total. The source is a user-supplied primary-looking artifact with asserted origin and unverified server provenance. An authenticated official GET/ETag/digest and independent image/folio spot checks remain OPEN. Never copy this entire manifest or large images into GitHub until provenance and rights reviewed. Resume by authenticating the live manifest, then generate a compact canvas-ID/label concordance and manually verify foldout mappings, with held-out folios for later text experiments.
