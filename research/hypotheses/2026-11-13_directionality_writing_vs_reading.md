# Directionality hypothesis — writing direction vs reading order (2026-11-13)

Status: **PROPOSED / NOT_RUN**. This is a falsifiable roadmap item, not an established decipherment, a new glyph classification, or a passed gate.

## Research question
The physical ductus and page layout may support left-to-right scribal execution while the *linguistic reading order* remains unproven. Evaluate distinct competing hypotheses without assuming EVA transcription is a transparent phonetic rendering.

- **DIR-H1 (baseline):** both physical writing and linguistic reading proceed left-to-right.
- **DIR-H2:** physical writing proceeds left-to-right, linguistic reading proceeds right-to-left.
- **DIR-H3:** physical glyph order differs from linguistic order through a reproducible permutation/transposition scheme; preregister a *bounded* model family rather than unrestricted post-hoc transforms.
- **DIR-H0 (control):** observed asymmetries are due to layout, word-boundary transcription, positional conventions, copy practice or nonlinguistic generators, without identifying linguistic direction.

Do not conflate (a) stroke ductus, (b) line/paragraph progression, (c) token orientation, (d) read order, and (e) semantic direction. Reversing glyph order within words, reversing word order within lines, and reversing both are distinct interventions; retain folio/line boundaries and record what was reversed.

## Roadmap and dependencies
1. **K-0001 first:** preserve physical coordinates and glyph occurrences independent of EVA and reading-order assumptions, including rare glyphs, suspected ligatures and diacritics. Never reverse or silently normalize primary image-grounded records.
2. **Source audit:** use version-pinned, rights-reviewed manuscript witnesses and explicit transcript alignment. Independently check evidence for line starts, end-of-paragraph truncation, quire/diagram reading order and stroke ductus; note uncertainty and script-hand variation. Layout alone does not prove linguistic reading order.
3. **Preregister tests:** score H1/H2 and defined H3 transforms with the same train/holdout partition, same model capacity and tuning budget; compare forward/backward conditional entropy, position-conditioned transitions, prefix/suffix patterns and unknown-position prediction. Distinguish invariants (e.g., symmetric measures and unrestricted Markov likelihood under reversal) from genuinely direction-informative tests.
4. **Controls:** length, folio, section, scribal hand, line position, marginal words, EVA editorial tokenization, mirrored/artificial strings, nonlinguistic copy/generator baselines; negative and positive synthetic controls. Prevent information leakage from choosing direction on held-out data.
5. **Falsification and reporting:** preregister primary held-out directional prediction difference and uncertainty interval; report effect size, bootstrap/appropriate permutation control, per-section heterogeneity and failure cases. Direction declared **UNRESOLVED** if effects are not robust to source/transcription choices or the metric is reversal-invariant. Reject a hypothesis only within explicitly tested models and witnesses.

## Acceptance
A reproducible protocol, immutable input hashes, script/config and held-out results; no claim of decipherment, semantic interpretation or confirmed reading direction on mere statistical asymmetry. Test must have predictive power on unseen glyph contexts and must survive appropriate confound controls. If inputs are blocked, retain **SCOPED_BLOCKED / NOT_RUN**, do not manufacture outcomes.

## Integration
This item is a *directionality hypothesis family* downstream of K-0001, compatible with K-0002 positional prediction and existing EXP positional/context tests. Avoid duplicate tests and IDs in A/O/W/K registers. Existing K-0001 scope and 0/5 decipherment gates remain unchanged.
