# Research landscape and prospective Eschede adversarial test — 2026-11-05

Status: SOURCE-INVENTORY / PRE-REGISTRATION DRAFT, not a manuscript experiment or verification of decipherment. Owner guidance: first survey multilingual sources and then seriously test Celler Presse/Franke claims, trying to defeat falsifications through independent evidence where possible, not designing tests to guarantee a desired result.

## Source discovery (live HTML visited 2026-11-05)
- DE Wikipedia: https://de.wikipedia.org/wiki/Voynich-Manuskript — researcher/history and six-section overview; **tertiary index**.
- EN Wikipedia: https://en.wikipedia.org/wiki/Voynich_manuscript — distinguishes cryptographic, shorthand, steganographic, natural-language, constructed-language, hoax and glossolalia models; **tertiary index**.
- FR Wikipedia: https://fr.wikipedia.org/wiki/Manuscrit_de_Voynich — additional segmentation of medical/herbal hypotheses and ciphers; **tertiary index**.
- ES Wikipedia: https://es.wikipedia.org/wiki/Manuscrito_Voynich — additional codicological context and dialects; **tertiary index**.
- IT Wikipedia: https://it.wikipedia.org/wiki/Manoscritto_Voynich — chronology and cryptanalytic hypotheses; **tertiary index**.
- https://voynich.net/ — VMs-list and forum, established 1991 mailing-list context; **discussion/discovery, not proof**.
- Yale Bowern & Lindemann, *The Linguistics of the Voynich Manuscript*: https://alumniacademy.yale.edu/sites/default/files/2021-07/The%20Linguistics%20of%20the%20Voynich%20Manuscript.pdf — research review arguing for statistical tests against natural language, enciphered controls and nonlanguage hypotheses.
- Celler Presse, Tobias Franke (2026-09-27): https://celler-presse.de/2026/09/27/durchbruch-in-eschede-per-ki-kollaboration-das-raetsel-des-voynich-manuskripts-ist-entschluesselt/ ; extended work https://celler-presse.de/voynich-manuskript/ and research index https://celler-presse.de/forschung/ — **author's claims and proposed interpretations; no independent validation completed**.
- Additional competing proposal: Caspari & Faccini *A Key to the Voynich Manuscript* https://pure.mpg.de/rest/items/item_3644902/component/file_3644903/content (Italian vernacular shorthand claim, research preprint); include as candidate, not accepted conclusion.

## Initial claims to extract from Eschede source (CLAIMED, not VERIFIED)
Franke proposes women’s health/therapeutic baths/astromedicine under a Fontana-circle provenance hypothesis. Claimed operational lexicon: `pchor` controls indication/topic, `qokedy` repetition counts quantitative units, `dal` combining, `shol` extracting/routing, `shey` finishing/cooling; different sections change measured variable. Examples explicitly ascribed to folios 2v, 33v, 78r, 71r; source also presents extended purported corpus-wide translation. The reported mechanism is sufficiently concrete to permit adversarial testing.

## Strongest immediate concerns (unresolved; not falsifications)
- Section-dependent semantics and picture-informed readings risk circular confirmation. Lock exact mapping and section variables **before** unseen evaluation.
- The source assigns differing contextual values to the same `pchor`; this may be legitimate control-code polysemy or flexible post hoc labeling. A discriminating prospective test must define how one chooses meaning without seeing held-out answer.
- `qokedy` repetitions allegedly encode quantities, but token counts and strings on cited folios must first be verified against independent EVA transcription and/or original image. Exact repeat positions vs illustrative schematic text remain UNKNOWN.
- A dated author hypothesis (Fontana circle) and a semantic decoding are logically separate; one cannot certify the other.

## Bounded next protocol — candidate EXP-0004 (NOT EXECUTED)
1. Freeze exact original claim text/version and all prescribed folio/token snippets; avoid adapting after manuscript inspection. Extract deterministic decoder rules, allowable section-dependent variants, and claimed exceptions; request complete codebook if needed.
2. Select reliable named/versioned EVA corpus with rights review; independently map test folios 2v/33v/78r/71r using owner-canonical IIIF snapshot SRC-0007; read underlying folio images where permitted. Verify first that the quoted `pchor`, `qokedy` repeats and `dal/shol/shey` genuinely occur at precise cited locations. Do not use unverified counts.
3. Positive control: literal transcription matched to image and a decoder-created *development* example. Negative control: shuffle section labels or swap folio images while keeping text; if decoder still yields comparably coherent medical readings, illustrative anchoring is insufficient. Null: generic thematic interpretation fitting image without unique text prediction.
4. Pre-specify held-out folios across all sections; require deterministic prediction of token role, repetition quantity and unseen passages before viewing their illustration. Compare alternate medical and nonmedical, natural-language and procedural-code controls; assess failure cases instead of selecting only successes.
5. Retain CLAIMED for author's claimed translations until manuscript transcription and out-of-sample tests pass. Any failure must be scoped; do not prematurely reject broader medical content or a Fontana connection.

Do not conflate Wikipedia article count with independent corroboration: multilingual editions may share references or copy material. Seek primary citations behind each testable assertion. Do not translate dangerous medical formulas into actionable treatments.
