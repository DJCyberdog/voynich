# K-0001 — VY001 A/B/C coordinate-provenance audit (2026-11-13)

**One bounded question:** Can the three recorded VY001 candidate crops be independently reproduced and compared from the metadata already integrated, without reusing the original investigator's unblinded visual judgment?

**Scope / source layer:** metadata audit ONLY of `research/glyphs/2026-11-13_K0001_VY001_triad.jsonl`, `research/glyphs/2026-11-13_K0001_v02_samples.jsonl`, `research/glyphs/2026-11-13_K0001_all_glyphs_scope.md`, and `docs/TRANSCRIPTION_POLICY.md` on main `e3d0205d455154fbd43f443f3898816d9bc341d6`. No manuscript image or uploaded PDF was opened in this cycle; no Yale live manifest request. No image rights assumed. No new glyph observation.

## Reproducible metadata findings

- **VERIFIED within repository metadata:** Triad IDs K0001-VY001-A/B/C are unique and point to f16r/p32, f24r/p48, f20r/p40 respectively. All three carry the *same* parent PDF SHA-256 `d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c`; all three declare physical grapheme identity, ligature, modifier, distinct scribe and EVA mapping unverified.
- **VERIFIED within repository metadata:** A's bbox `[209.5,230,248,267]` matches the VY001 sample record, which identifies its raster as 1042×1474 and a separate f16r PNG SHA-256 `0303fee883b1c30dbc9eca2f10fc0480e383fba65cb07e02384cc76dde3cc5e0`.
- **VERIFIED metadata gap:** B and C are listed as `bbox_xyxy` analogues in the VY001 sample and triad records, but neither record identifies the exact rendered *page raster dimensions*, page-specific image hash, rendering DPI, rotation, crop transform, or pixel-origin convention for those two pages. The triad's shared PDF hash identifies source bytes, not a unique rendered raster coordinate frame. Consequently, the B/C crop geometry is **not yet independently byte-reproducible** from the current record alone.
- **UNKNOWN:** whether A/B/C represent distinct graphemes, allographs, ligatures, modifiers or image artifacts; whether the lower-left differences persist when crops are rendered identically and viewed with their neighbors. The prior visual descriptions are exploratory claims, not a blinded test.

## Preregistered next test — design only, NOT executed

**Prediction (H1):** after a deterministic rendering recipe and complete per-page raster hashes are pinned, at least one of the three pre-specified lower-left termination categories is reproducibly distinguished by blinded independent annotators on identical, context-preserving crop geometry and on a second independently sourced image witness.

**Strongest counterhypothesis (H0):** the perceived distinction is caused by rendering scale, crop bounds, adjacent strokes, ink degradation or within-class allography; any between-candidate difference disappears under image/context matching.

**Positive control:** identical raster crops reintroduced with random IDs and standardized transforms, to test annotator self-consistency. **Negative control:** same-witness, context-matched visually ambiguous strokes selected *before* revealing identities. **Null:** class-frequency-preserving random annotator assignments, with the strongest same-hand/context allograph model separately evaluated. **Held-out:** distinct physical leaves and an independently sourced imaging witness; no reuse of A/B/C as confirmatory holdout. **Rejection:** fail a frozen chance-corrected agreement threshold or fail second-witness replication; reject only the proposed identity partition, not all writing systems. Threshold, folios, rights, sample sizes and exact crop coordinates MUST be frozen before execution; no post-hoc thresholds.

**Required next metadata fields:** `source_pdf_sha256`, `page_index_base`, `pdf_page`, `render_engine_version`, `dpi`, `rotation`, `raster_width`, `raster_height`, `page_png_sha256`, `bbox_coordinate_origin`, `bbox_xyxy`, `context_bbox_xyxy`, `folio_canvas_id`, `annotation_blind_id`, `rights_status`. Preserve raw candidate IDs; never overwrite previous observations.

**Deduplication:** K-0001 remains ACTIVE, not done; O-01 addresses correction/reinking, not glyph-class identity; K-0002 and EXP-0014/0015/0018/0025 are EVA/statistical tests, not independent pixel-level corroboration. No new HYP/EXP/SRC ID; no change to 3/40 audit closures, 213/213 owner-canonical canvas-ID inventory or 0/5 decipherment gates. Source provenance: SRC-0007 owner-canonical snapshot, **not independently live Yale-authenticated**. Workflow: **RESEARCH_COMPLETED** for narrow metadata audit; **BLOCKED** for confirmatory image test until raster pinning, rights, and blind sampling are resolved.

## 2026-11-13 addendum — direct source-PDF raster reproducibility (after PR #48 merge)

**Material new input:** owner-provided complete PDF `voynich.pdf` is now merged to main through PR #48; merge commit `69b21518738a857fd004add908182534d8eb0c04`. Git LFS pointer declares SHA-256 `d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c` and size `127121031` bytes. The actual locally mounted 214-page source PDF was SHA-256 checked against this exact value. This does **not** authenticate the separate owner-canonical IIIF manifest SRC-0007 live against Yale.

**Deterministic first-pass raster procedure:** PyMuPDF/MuPDF (`fitz.VersionBind=1.26.7`), `page=d[pdf_page-1]`; `page.get_pixmap(matrix=fitz.Matrix(1.75,1.75),alpha=False)`; decode pixmap samples as RGB and save using PIL as PNG. On f16r/PDF page 32, f24r/page 48 and f20r/page 40, **all three renders produced 1042×1474 RGB pixels**. Coordinates refer to this raster with origin top-left and xyxy box boundaries, allowing all three recorded boxes to be located without inventing transforms. Rendered page PNG SHA-256 fingerprints for this exact local process (not the earlier separately created f16r PNG):

| VY001 candidate | folio / 1-based PDF page | source bbox xyxy | 1042×1474 page PNG SHA-256 |
| --- | --- | --- | --- |
| A | f16r / 32 | 209.5,230,248,267 | `2f31a1e90dc41651b73f32ef9926a51404d90365a33d6ba60f6e9cc815a7842f` |
| B | f24r / 48 | 330,230,364,263 | `b51601e5263f477aa09bf05c1a8879ad0b9942272cff26b5efbccdeceac991d6` |
| C | f20r / 40 | 463,383,497,416 | `79ecadadeb30af61aa0309cc85d899b14529ebc2ba5a45a9dbda2164ad78eba6` |

**Observed, nonblind direct-image result:** at those source coordinates, A has a broad curved left-descending terminal; B appears to terminate in a flatter leftward stroke above its base; C shows a more complex left-side terminal, including an additional short lower horizontal stroke in the context image. Thus, the three registered *visible marks* are distinguishable in this fixed raster; this is **DOCUMENTED** direct image observation, **not** a validated three-grapheme classification. The owner explicitly vetoes automatic conflation of the three candidates: preserve A/B/C as separate provisional glyph **classes**, with `CLAIMED` classification and `ACTIVE` follow-up. Their functional grapheme identity remains `UNKNOWN`. Distinct render pixel arrays are not independent manuscripts or scribes.

**Strongest counterhypothesis:** one shared functional grapheme with allographic / pen-trajectory variants; additional strokes might be adjacent textual marks or minor artifacts. **Falsification still pending:** blinded independent annotators with preregistered class definitions, rotated/identical positive controls and context-matched negative controls, plus held-out folios or independent imaging witness; this cycle supplies no blind consensus, frequency counts, semantic interpretation or image-independent corroboration. No new HYP/EXP or numerical decipherment progress, no copy of the source scans into the repository beyond owner-uploaded original PDF, and no modification of manuscript transcriptions. PR #46 remains a separate unmerged research review.


## K-0001b — Owner hypothesis: at least THREE distinct hands within Davis's Scribe 1 (2026-11-13)

**Owner correction (do not silently weaken to two):** The owner hypothesizes **at least three different scribal hands** across f16r, f20r and f24r, all provisionally compared to Lisa Fagin Davis's broad Scribe 1 classification. This is a **CLAIMED / ACTIVE** proposal, **not** an independently established scribal attribution and not a claim that Davis has been refuted. This is a handwriting-attribution test, separate from K-0001a's visible glyph class / functional grapheme identity.

**Owner's exploratory image observations (not confirmed quantitative results):**
- VY0001's top-left triangular feature appears different among f16r (A), f24r (B) and f20r (C).
- An **o-shaped** mark appears different between f16r and f24r.
- A **c-shaped** mark appears different between f24r and f20r.
Here “o” and “c” are **shape-only descriptions**, not phoneme or EVA assignments. The page-local context (underlying/embedded or adjacent strokes) may alter the visible outline and must be coded independently. The user-supplied PDF, SHA-256 `d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c`, is now versioned on main via PR #48; this only fixes a source witness, not scribal identity.

**Preregistered discriminating prediction (DESIGN; test not run):** After annotators predefine at least five stable, recurring shape classes and blind-identify multiple occurrences per page, **each of the three folios forms a reproducible, distinct handwriting profile**, including all *three pairwise* contrasts (f16r/f20r, f16r/f24r, f20r/f24r), based on several independent diagnostic features rather than one selected gallow. Within-page variability should be demonstrably lower than between-page differences under the same imaging, lexical-position and graphical-neighbor conditions. Thresholds, exclusions and labels must be frozen before evaluation.

**Strongest competing account:** one hand showing contextual allography, ligatures, neighboring/interior strokes, pen trajectory, writing session, quill/ink variation or manuscript image differences; another competing account is shared exemplar conventions without independent hand identities. An out-of-source Davis attribution is a **pre-existing comparative hypothesis**, not ground truth.

**Controls:** positive—folio pairs independently assigned to different hands in the *original, independently verified Davis hand-attribution source*, plus blinded duplicate crops to verify coding reliability; negative—different line positions and context-matched repetitions from a single folio and known near-neighbor strokes; null—one-hand model allowing contextual and session variability; evaluation—leave entire folios out, stratify by region, writer-independent adjudicators and truly sealed physical leaves; no training/holdout contamination. Compare absolute performance to the five-hand scheme and to simpler one-/two-hand partitions with penalties for additional hands. If any of the three pairwise separations fails the frozen criterion, the **specific minimum-three-hands claim is not supported**; this does not disprove distinct *visual* glyph shapes. Visual similarity is not proof of common authorship.

**Status:** owner observations **CLAIMED**, three-hand conclusion **UNKNOWN**, review **ACTIVE**, confirmatory blind paleographic test **BLOCKED** until diagnostic loci and independent comparison/holdout are frozen. No new HYP/EXP number, no independent handwriting or semantic claim, no progress change to decipherment criteria or 40-claim audit. Do not conflate K-0001b with the VY0001 triad itself.
