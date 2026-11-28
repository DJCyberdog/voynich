# RC2-02b/c — native-resolution binary hypotheses and method agreement

Status: LOCAL EXPERIMENT PASS; not a production ink/segmentation gate. RC2-02d/h remain open. No auto-acceptance, no deletion, no change of existing runtime or private annotations.

## Method and identity

Exact native PDF SHA-256 d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c; exact canonical review manifest SHA-256 e95f1d10df4b50a9ac1a8ccd6b3ec99cbdcb08453cc6311a6533a62056a75311. The audit rechecked both digests and the complete ID set. 180 native envelopes across 80 PDF pages (160 enriched candidate cases and 20 random windows; 20 wrapper controls excluded). Conservative mapped 200-DPI boxes, no upsampling. Each envelope processed with up to 64 native pixels of context per side, clipped at the embedded image boundary. Otsu, Wolf global statistics and CLAHE tiles are calculated in this context, not on entire pages. Counts are development proxies, not independent accuracy or complete-glyph retention. Two other candidate classes (mixed and uncertain) excluded from the handwriting/non-script denominators. Original RGB and annotations unchanged.

37 single hypotheses: fixed threshold (<160), Otsu, Sauvola and Wolf-Jolion with windows 15/31/51 and k=.15/.25/.35, Niblack k=-.2 on three windows, Gaussian ratio normalization on grayscale and RGB channels, locally implemented tile CLAHE (32 px, clip 2, not claimed equivalent to OpenCV), single-scale log-ratio Retinex and morphological black-hat, each of the seven transformed inputs combined with Sauvola/Wolf (31,.25). Gaussian radius 16, black-hat size 15. No physical scanner calibration or stroke-width adaptation yet. Code uses only NumPy and Pillow for mask generation. SciPy is used in the private experimental audit to count 8-connected foreground components, not added to portable dependencies. Audit is run from worker with PYTHONPATH pointing to worker, using the pinned source and review as arguments, Python without -O; writes aggregate audit-result.json to working directory. No private raw assets, crops, labels, or results committed. Do not run the audit with untrusted input or publish its local output automatically.

Six-method ensemble fixed for this exploratory comparison: Sauvola and Wolf 31/.25, grayscale normalization + Sauvola/Wolf, red and blue normalization + Sauvola. Votes (uint16), union, intersection, strict majority and disagreement preserved; not calibrated confidence. Correlated methods and context effects limit interpretation. No selected production winner.

## Development observations (aggregate only)

| Method | Handwriting with nonempty mask / 66 | Non-script/blank empty mask / 92 | 8-connected components within handwriting boxes (sum) |
|---|---:|---:|---:|
| Fixed160 | 66 | 0 | 397 |
| Otsu | 66 | 14 | 411 |
| Sauvola 31/.25 | 65 | 39 | 482 |
| Wolf 31/.25 | 66 | 10 | 471 |
| CLAHE + Sauvola | 66 | 4 | 484 |
| Normalization + Sauvola | 64 | 45 | 504 |
| Blue normalization + Sauvola | 66 | 34 | 460 |
| Red normalization + Sauvola | 63 | 47 | 494 |
| Blackhat + Sauvola | 61 | 51 | 490 |
| Retinex + Sauvola | 56 | 56 | 394 |
| Union | 66 | 10 | 471 |
| Strict majority | 65 | 39 | 487 |
| Intersection | 63 | 47 | 494 |

Disagreement pixels in all 66 handwriting cases: 6062 pixels total across 42540 box pixels (overlap possible). Disagreement in 82/92 non-script/blank cases. On 20 random windows, eight handwriting and twelve non-script/blank, union retains some foreground in 8/8 and empties 0/12; majority 7/8 and 6/12; intersection 7/8 and 6/12. This is a small development control set, not a held-out test. Component count is not a glyph count or independently scored fragmentation; higher count can reflect finer structure, breakage or noise. Clipping and exact topology require reference masks and boundary annotations not available in the 200-case export. Context-dependent thresholds can change on full-page processing; no full-page performance inference. A native reference envelope can contain neighboring pixels. No threshold or filtering policy is scientifically validated.

## Engineering verification

Locally executed seven tests, 7/7 PASS: local statistics against naive calculation, constant images, two-tone Otsu, synthetic thin stroke, preservation/alignment, vote algebra, invalid input and small/odd CLAHE tile handling. During testing a uint8 overflow in normalization was detected and fixed before the actual audit; exact tested module blob ef7d1c6859a31a27ff8e344e7603eaa941f0ef3b and tests blob 51b5cadb702321cf3c1e04be7396750be4438479. Audit script blob 4dffafe6667d7f560f34157ddd77078df36eb695; local duration 13.8 s for this context-window run, not a throughput qualification. Hosted regression on previous 381d7ca completed successfully; current new tests require explicit hosted execution or discovery verification. No CUDA benchmark, no whole-page masks, no production integration, no vectorizer, no independent holdout, no new owner patch. Next RC2-02d: artifact, contour and script localization with retained uncertainties and geometric evidence; then e/f vector stages may be developed together when masks/coordinate and licensing contracts are defined.
