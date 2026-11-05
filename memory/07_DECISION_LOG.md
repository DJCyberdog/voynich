# Decisions

## 2026-11-05 D-0001 — repository-only provenance
First empty-repository README commit on main; subsequent changes require PRs. Prefer smaller material deltas to automatic volume.

## 2026-11-05 D-0002 — initial research priority
Start by separating material dating from inscription dating, then audit Yale image and transcription provenance. No glyphs independently measured.

## 2026-11-05 D-0003 — physical foliation vs digital identity
Yale pre-1600 catalog SRC-0006 documents folds, missing/unnumbered leaves. Preserve physical and digital identity. EXP-0002.

## 2026-11-05 D-0004 — user-provided manifest received
A user provided a hash-pinned Markdown-fenced IIIF v3 JSON snapshot, parsed in EXP-0003. Initial procedure required live Yale confirmation before treating it as research working authority; repeated URL tests blocked further research.

## 2026-11-05 D-0005 — OWNER OVERRIDE: canonical working manifest; avoid reauthentication loops
Owner explicitly instructed: do not spend repeated cycles on https://collections.library.yale.edu/manifests/2002046; treat the provided content as canonical. Previous operating rule (D-0004/RM-001): independent live authentication required before continuing. New operating rule: supplied SHA-pinned SRC-0007 is canonical for internal mapping/testing; routine live authentication RETIRED/SATURATED, not a prerequisite. Reactivate only for a concrete mismatch, changed owner instruction or new official evidence. This changes workflow priority, **not** the provenance claim: locally verified provided content is distinct from independently verified current Yale bytes. No relaxation of falsification, rights or decipherment standards.

### Automation self-update, proposed 2026-11-05 (apply only after merge)
Task: Voynich Autonomous Research; existing ID unchanged; hourly schedule and Europe/Berlin timezone unchanged. Before: prompt instructed general primary-source verification, without an explicit canonical-user-snapshot override, repeatedly selecting Yale HTTP 403 as unresolved blocker. After: preserve entire research cycle/governance discipline and add binding instruction to use SRC-0007 as canonical working manifest, stop routine access retries, prioritize mapping, corpus provenance and falsifiable tests. Exact updated directive stored in docs/TASK_OVERRIDE.md. Confirm task update with actual task-tool receipt after merging. If tool refuses, document limitation separately; do not pretend success.
