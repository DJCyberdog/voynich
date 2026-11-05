# Franke decoder: bounded adversarial documentary review (2026-11-05)

Research question: Does the interactive decoder independently validate medical semantics, beyond assigning functional labels to recurring Voynich transcription patterns?

Direct sources read 2026-11-05:
- https://celler-presse.de/forschung/dokument/voynich-manuskript-ein-interaktiver-decoder-zur-untersuchung-von-grammatik-und-bedeutung/ (report v1.0, 2026-11-01; decoder v0.2.5): qokedy is decomposed as qok + edy, with hypothetical dosage/process gloss and a fluent German reading. The author explicitly calls this an unconfirmed working interpretation.
- https://celler-presse.de/forschung/dokument/das-deterministische-parsing-protokoll-beispiel-folio-1r-zeile-1/ (2026-10-04): raw shol/shory can map to derived qokedy through P-12; never conflate derived and raw tokens.
- https://celler-presse.de/forschung/dokument/voynich-manuscript-provisional-integrated-model-g1-7-scientific-interim-report/ (2026-10-18): author says morpheme identity, syntax, parts of speech, language and meaning remain unresolved; structural G1.7 and historical V54 models are distinct.

DOCUMENTED observation: The published decoder illustrates a hypothesis-dependent semantic rendering, not independent validation of that meaning. This does NOT contradict its structural regularities. Semantic correctness remains UNKNOWN.

Prospective preregistration candidates (NOT EXECUTED):
1. Freeze version, complete parser rule priority, lexicon, input and output. Test shol against the P-12/P-17 overlap already documented in the repository. Require either unique deterministic output or declared multi-output behavior.
2. Freeze ZL3b-n v3b source bytes; evaluate both editorially permissible split/join treatments of IVTFF comma in f2v.1 cheo,pchor. Do not claim physical word spacing from the comma.
3. Freeze semantics before held-out folios. Compare original semantic labels with blinded shuffled-label controls; score independently anchored predictions, not fluent prose.
4. Compare original text with matched artificial strings preserving prefix/suffix, word length and position distributions; report abstention, coverage and rule collisions.
5. Separate structural predictive gains from claims about historical medicine, language and translation. Specify sampling, effect sizes and rejection thresholds before quantitative evaluation.

Alternative explanations: meaningful functional notation; regular orthographic/positional grammar without recoverable meaning; a nonsemantic generator; editorial segmentation effects.

Limitations: documentary comparison only. No interactive decoder operation, source code inspection, image check, full corpus ingestion, independent SHA-256 or numerical replication. No claim of falsification or confirmation. Next: retrieve frozen parser implementation/precedence and test reproducibility first. No Yale manifest reauthentication needed.
