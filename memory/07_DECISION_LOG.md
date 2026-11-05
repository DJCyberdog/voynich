# Decisions

## 2026-11-05 D-0001 — repository-only provenance
First empty-repository README commit on main; subsequent changes require PRs. Prefer smaller material deltas to automatic volume.

## 2026-11-05 D-0002 — initial research priority
Start by separating material dating from inscription dating, then audit Yale image and transcription provenance. No glyphs independently measured.

## 2026-11-05 D-0003 — physical foliation vs digital identity
Yale pre-1600 catalog SRC-0006 documents folds, missing/unnumbered leaves. Preserve physical and digital identity. EXP-0002.

## 2026-11-05 D-0004 — user-provided manifest received
A user provided a hash-pinned IIIF snapshot, parsed in EXP-0003.

## 2026-11-05 D-0005 — owner accepts user manifest as canonical working reference
The user-supplied SRC-0007 is canonical for research mapping; routine live HTTP 403 attempts SATURATED. Provenance and rights claims remain distinguished.

## 2026-11-05 D-0006 — owner prioritizes broad hypothesis survey and severe fair testing of Eschede proposal
Owner asks to survey German/English/other Wikipedias, Voynich.net and to attack the 2026 Eschede decipherment proposal from every plausible direction, seeking to establish whether proposed explanations survive *genuine* attempted falsifications. This does not justify confirmation bias or pre-deciding a successful decipherment. Preliminary sources and proposed protocol documented in research/hypotheses/2026-11-05_landscape_eschede_protocol.md. No semantic claim yet elevated beyond CLAIMED; corpus verification and held-out evaluation pending. Avoid cycling back to URL-access concerns.

## 2026-11-05 D-0007 — distinguish reading validation from semantic criticism
EXP-0004 compares Franke 2v literal-word claims with the Currier C f2v.P.1–P.8 VIB witness. Source-level literal mismatch is documented, but not elevated to universal disproof without raw transcription/image and other witnesses. Next effort should seek best rescue interpretation (e.g., different EVA witness or segmentation), without overriding evidence. Prioritize literal image-linked provenance above speculative medical meaning.

## 2026-11-05 D-0008 — correct layer confusion in EXP-0004; refocus on parser reproducibility
Franke's published Oct 4 method correction (SRC-0010) says his parameter chains are **derived parser outputs**, not raw EVA. The previously observed Currier C mismatch remains a correct witness-level observation, but cannot be promoted to a refutation of generated system tokens. Worked f1r example SRC-0012 maps raw shol to qokedy. Parser table SRC-0011 has at least one overlapping match, shol triggering P-12 and P-17, for which precedence was not visible in the inspected table. EXP-0005 records this constrained concern, not an assertion of no solution. Ask for deterministic full trace then blind test. Owner's canonical manifest status unchanged; task unchanged.
