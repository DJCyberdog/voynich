# EXP-0008 — IVTFF comma and f2v.1 segmentation (2026-11-05)

## Preregistered source-convention test
Question: Does IVTFF 2.x define the comma in ZL3b-n v3b `f2v.1 cheo,pchor` as a certain word boundary?
Priority: resolves an immediate tokenization ambiguity before testing Franke's parser, without downloading protected imagery or full corpus.
Prediction under H1 (certain boundary): the format specification calls comma a definite word space.
Strong counterhypothesis H0: comma is an uncertain editorial space, permitting both `cheo|pchor` and `cheopchor` tokenizations. Alternative: actual manuscript image might resolve the physical gap, not assessed here.
Falsifier: a normative format statement defining comma as uncertain defeats H1.
Positive control: the same specification explicitly defines period as confident word space.
Negative control: drawing intrusion `<->` and `<~>` are separate codes, not interchangeable with comma.
Null model: editorial segmentation variation without evidence of distinct manuscript glyphs.
Held out: other folios and parser-derived outputs; no leakage or confirmatory semantic test.

## Evidence and observation
Origin specification: https://www.voynich.nu/software/ivtt/IVTFF_format.pdf section 6.7; origin explanation https://www.voynich.nu/extra/sp_transcr.html (IVTFF 2.0.2 description). Both accessed 2026-11-05. Section 6.7 states comma denotes relatively small space for which the transcriber is not confident that it is a word space; period denotes a confident word space. IVTT manual https://www.voynich.nu/software/ivtt/IVTT_manual.pdf distinguishes -h0 keep uncertain comma, -h1 promote to normal space, -h2 remove uncertain spaces. Source witness SRC-0016 in EXP-0007 directly documents `cheo,pchor` at f2v.1. This cycle did NOT independently redownload/hash source bytes or inspect a Yale image.

Result: CONTRADICTED for certain-word-boundary reading of comma; DOCUMENTED for normative comma semantics; UNKNOWN for the physical word boundary, glyph reading, Franke parser output, language, semantics, and manuscript origin. Operational status ACTIVE for parser boundary sensitivity, not decipherment. No statistical frequencies or new language hypotheses claimed.

## Reproducible next test
Freeze exact ZL3b-n bytes and checksum, preserve comma in source, run two explicitly declared tokenization branches (split versus join) on f2v.1, with a frozen published parser and full rule precedence, then compare resulting outputs and independent held-out folios. Do not select the split yielding the preferred medical meaning. No third-party code executed.

Owner's SHA-pinned SRC-0007 remains canonical working Yale manifest; independent live Yale authentication NOT performed. No manifest URL retries. Rights: specification links cited, no scan or corpus redistribution.
