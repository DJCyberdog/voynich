# K-0001 / INV-006 — f1r.1 control integrity: a red-negative patch is not blank parchment

**Date:** 2026-11-16. **Scope:** one bounded pre-annotation control-source audit of existing INV-005; no independent annotator, glyph count or new language test. **Question:** can the earlier f1r red-pigment negative ROI [380,1660,515,1749] serve as the *blank parchment* procedural negative for the new EVA-blind dark-ink segmentation experiment?

## Sources and verification
The previously supplied, owner-held f1r raster was locally available as `f1r_current.png`; PIL decoded RGB 1489×2105, raw RGB SHA-256 `cbd95103a136471df3a27933f881fa4de7664c1d1075c4930c5e9e24234daf10`, exactly the pinned source raster in INV-002 through INV-005. Parent owner PDF SHA-256 `d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c` is *inherited provenance*, not reverified PDF bytes this cycle. SRC-0007 remains owner-canonical, not independently live Yale authenticated. No images or transcript lines redistributed.

Coordinates are half-open raster xyxy with top-left origin. Crops were inspected at 4–5× nearest-neighbor/display enlargement for morphology only; the original RGB byte values were used to compute reproducible crop checksums, not to infer script identity.

## Direct image observation and decisive counterexample

The former `CTRL_BLANK` rectangle [380,1660,515,1749] used in INV-002/003 contains a **clearly visible dark figurative/illustrative mark**, despite having zero pixels under the previous *red-specific* HSV mask. Its crop dimensions are 135×89 and RGB-byte SHA-256 is `856be8ead7abc5eecebe0053b1759a0b93ea3fc7e6ff7d2914f36b71210c725b`. Therefore **the inference `red-negative => visually blank parchment` is contradicted for this exact ROI**. This is not a correction to the previous red-mask computation: it legitimately measured absence of pixels passing the *red* threshold, not absence of other dark marks. The rectangle MUST NOT be silently reused as a blank negative in the independent dark-ink stroke test.

### Prospective replacement control rectangles — selected before annotator enrollment

- **Positive control (clear continuous dark stroke, outside scored test ROI):** [465,340,495,395], RGB 30×55, SHA-256 `52741a707b175fef5629129d25168fa666d04445087c1dcaac67aec354f485a8`. Visually contains a dark tall looped stroke in f1r.1. This is a coordinator-selected visual control, NOT an independently adjudicated glyph. The rectangle is disjoint from test [760,337,1050,414].
- **Negative control (apparently unlettered parchment with small texture/specks):** [720,275,790,315], RGB 70×40, SHA-256 `271190883ca64508bbd8f7e0d83fdfd8fb3a7e565ff3c7adf43b31f0a9685e`. This was visually screened as lacking apparent intentional writing; microscopic damage or tiny pigment specks remain possible. It is disjoint from the scored test ROI and the positive control. **Expected class: BACKGROUND / no deliberate ink stroke**, not "zero dark pixels".
- The old red-mask control [1000,1680,1085,1730] was not independently certified as blank parchment and is not an approved INV-005 negative.

These control coordinates and crop hashes are **frozen before any A/B annotation**. Source raster and source-pixel crop hashes must be verified by the independent coordinator before images are given to annotators. Do not label the classes in the annotators' presentation; the coordinator keeps the key sealed until both annotation files are locked. The control selections are not random or independent; they are procedural controls only, not a manuscript population estimate.

## Falsification and alternatives

**Predeclared question for this cycle:** if a red-negative ROI is actually blank, visual inspection should reveal no salient non-red ink/illustration. **Observation:** obvious dark illustration. **CONTRADICTED:** the *cross-task blank-control transfer assumption* for this rectangle. **VERIFIED within the local raster:** exact RGB raster hash, crop hash and dimensions; the visible mark is **DOCUMENTED** in the source image. **UNKNOWN:** historical pigment/mark authorship and whether tiny texture in the replacement negative might be adjudicated as uncertain damage.

**Strongest alternative:** the earlier study used a different measurement target (red pigment), so a dark non-red mark does not invalidate the original red-vs-blank *red-color* test. This alternative is correct for the earlier measurement but does not rescue the ROI as a visually blank control for the present dark-ink annotation protocol. Natural-language, cipher, nonlanguage and hybrid interpretations remain equally open; this control audit is independent of those families.

**Null/control/holdout:** the red-mask null (absence of *red*) and the stroke-annotation null (absence of *intentional dark ink*) must remain separate. No new statistical null distribution or p-value is asserted. The replacement ink/blank pair is a nonblind coordinator preselection; it has not been independently scored. All f11+ physical leaves remain held out. Two independent EVA-blind human A/B annotations and a separately licensed second image witness are still missing, so **no independent visual segmentation outcome exists**.

## Decision and next step

**Material methodological delta:** a legacy red-negative region is now specifically excluded from use as a blank control for INV-005; a byte-identified positive and negative control pair is frozen. The existing INV-005 IoU>=0.50 and agreement>=0.80 thresholds, original test ROI and all blinding requirements are unchanged. This is **control-quality evidence**, not evidence for additional Voynich graphemes. K-0001 **ACTIVE**; independent annotation execution still **BLOCKED** until genuinely independent A/B reviewers and a separately rights-cleared image witness are obtained. 0/20 fully annotated first-ten sides, 0/28 fully adjudicated f1r line regions, 0 validated physical grapheme classes/EVA maps, 3/40 narrowly completed A/W audits, 0/5 decipherment gates; 213/213 canonical snapshot canvas IDs inventoried (not verified folio concordance).

Next: independently confirm control class without EVA/editorial leakage, acquire two independent blind annotations, lock SHA-256 files, then score. If either control fails, report failure and revise in a new prospective protocol, never retroactively substitute a successful region.
