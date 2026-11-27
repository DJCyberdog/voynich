# RC2-01 — Yale PDF source surface isolation

Status: SOURCE_ISOLATION TECH_PASS (hosted controls + actual complete PDF); PARTIAL for independent script/non-script validation within scans. No scientific acceptance, recognition calibration, physical-leaf mapping or owner patch.

## Source-specific method

The exact locally authorized Yale PDF (214 PDF pages, SHA256 d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c) consists of a metadata-only first page and 213 separately embedded digitization images. All images are kept, including covers, flyleaves, foldouts, marginal marks and illustrations. The PDF wrapper has separate modern text, page labels and two rectangular vector border strokes per image. The exact source pin is a hard precondition. Inspect PDF objects rather than use OCR, font similarity, fixed crop margins or an uncalibrated semantic classifier. Unrecognized object arrangements or overlays touching the image fail closed. Do not use this as a generic heuristic for other PDF editions.

The in-memory image-only PDF preserves the original page rectangle, image placement (0.001 pt verification tolerance), entire image extent and exact extracted encoded image bytes. No original file changes. Verify the reconstructed display list contains only the image; log every excluded object geometry and reason, source/image hashes, pixel envelope, outside area, and explicit unresolved inner-image status. Page 1 yields a zero-region manifest, not a failed page or guessed folio. The 200 DPI proposal algorithm retains previous ink thresholds, includes terminal edges of the envelope and uses full-page coordinates for regions. This is wrapper exclusion only: dark marks within scans may be script, illustration, binding, background, later annotations or uncertain material. No claim of semantic script classification; uncertain candidates remain available to RC2-02 and review. No new model approval.

The historical direct regions.py propose default remains full-page for other sources and replays; explicit --isolate-yale activates the new method. The live coordinator automatically selects it only for the exact Yale digest, binds the new module into worker identity and validates envelope accounting before segmentation. No silent resume of old worker identity; preserve RC1 evidence and plan a new explicit compatible RC2 run. Other source editions retain legacy proposal behavior, not verified wrapper exclusion. Page scopes may account for 214 pages with the pinned source; physical grouping remains separately supplied and unverified. The audit command requires no invented physical group map:
```
python -B regions.py audit-yale path/to/voynich.pdf d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c private-audit.json
```
The audit uses exactly the same isolation/screening routines without saving crop PNGs. Keep output private; only aggregates may be disclosed under policy.

## Actual local source observations and validation

Exact module blob f88990b765eb362e0728e83e5ad3a66bad60ef2e was executed against SHA256-verified original PDF in isolated Linux development environment, PyMuPDF 1.26.7. All 214 pages passed wrapper structure, image-only reconstruction and geometry checks: 213 image envelopes with exact extracted bytes preserved, 1 metadata-only, 896 visible text objects, 1 invisible text object, 426 border stroke objects excluded. Source image geometry checked including f1r (PDF 4), foldout pages 127 and 159 and back cover 214. A local reproduction of the new screening loop over all 214 pages checked 917603 windows and selected 446494 ink proposals, all inside image bounds; 4 pages had zero selected regions. These are overlapping proposal windows, not glyphs or validated writing. No crop files or model predictions were generated for this full-corpus audit.

Selected page comparisons of old full-page and new image-only screening (not ground truth or precision):
| PDF page | Legacy proposals | Legacy outside/crossing new envelope | New proposals |
|---|---:|---:|---:|
| 1 (catalog) | 1531 | 1531 | 0 |
| 4 (f1r) | 2161 | 558 | 1633 |
| 127 (foldout image) | 1165 | 286 | 875 |
| 159 (foldout image) | 2615 | 341 | 2311 |
| 214 (back cover) | 423 | 419 | 4 |

The grids are reanchored at the true image edges; counts are not a set-subtraction. In particular the RC1 6539 glyph proposals cannot be compared directly to these region counts. The observed cut modern Y is consistent with the separate wrapper text; exact glyph provenance remains unconfirmed. Independent handwritten-region annotation and full script/non-script discrimination inside images are not established by these checks. Actual end-to-end owner CPU/CUDA, interruption/resume, RC2-02 segmentation and full-manuscript downstream acceptance remain open. No private image/crop data is included in Git or CI.

## Engineering qualification

Synthetic control tests exercise source hash, no text on catalog, image-only raster, preservation of marks at edges, exact crop hashes, proposal bounds and counts, old CLI route, overlap and unexpected vector refusal, actual coordinator selection. Hosted Linux/Windows test run is required. Full private real-source audit repeated on local owner PC at RC2-10. Broader manuscript script/background discrimination within the image and independent reference validation remain open (RC2-01 partial until explicit separate evidence or agreed scope, not a scientific claim).

### First hosted execution and edge remediation

Initial Ubuntu run 45965975369 found actual one-pixel rasterization bleed beyond the mathematical floor/ceil image envelope on a synthetic edge fixture. Do not crop it away: expand the image-only envelope by one pixel, clipped to page bounds, and fail closed unless the entire exterior is white. This cannot restore wrapper content because the isolated display list only contains the source image. The original full-corpus audit (916507 windows, 445895 selected) is superseded by the repeated audit after the guard; all 214 pages passed again with the exact updated surface module and screening loop, 917603 windows, 446494 proposals, all inside their envelope. The original image bytes, counts of excluded PDF objects and other conclusions are unchanged. Existing test_regions imports torch via test_worker; add the same CPU wheel dependency used by existing baseline CI. No successful hosted requalification claimed yet.

The initial Windows job additionally exposed a fixture-only Windows 8.3 short-path vs resolved long-path mismatch in coordinator ref construction. Normalize the fixture root before generating refs, as for RC2-00. Do not relax production path containment. Full original Windows result FAIL; pending corrected retest.

### Corrected hosted qualification and full raster comparison

At exact tested commit ed79e909b34a1cf2706bd131b8142834681687e0, [run 45966475775](https://github.com/DJCyberdog/voynich/actions/runs/45966475775) succeeded: Ubuntu 24.04 job 140396236505 and Windows 2025 job 140396236633 each passed 8/8 tests (4 new surface controls including live coordinator route + 4 existing region tests). Initial geometry/CI dependency and Windows path fixture failures are retained above, not waived. The final exact source module blob f88990b765eb362e0728e83e5ad3a66bad60ef2e was also exercised on every actual PDF image page at 200 DPI. Compared the original full-page rendering and isolated rendering inside the verified envelope, omitting four pixels on each edge to avoid the known modern vector border and rasterization boundary. Two batches 2–107 and 108–214: 291926596 + 264894416 = 556821012 RGB pixels, zero changed pixels in the compared interior, 213/213 image pages. The boundary is separately covered by exact embedded image bytes, geometry, conservative raster guard and synthetic four-corner tests; do not assert original border pixels are identical. Whole-source wrapper isolation and existing proposal/coordinator behavior therefore TECH_PASS for tested conditions. Independent recognition of script versus non-script within source images, and exact provenance of the previously observed cropped Y, remain open; retain RC2-01 PARTIAL under its broader original acceptance wording and continue independent RC2-02 work without silently relaxing those requirements. Full owner installation and corpus downstream native qualification remain RC2-10. No owner patch distributed or scientific gate closed. Evidence-only follow-up changes documentation/manifest, not the tested source or tests.
