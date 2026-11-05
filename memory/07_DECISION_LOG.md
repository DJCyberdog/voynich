# Decisions

## 2026-11-05 D-0001 — repository-only provenance
First empty-repository README commit on main; subsequent changes require PRs. Prefer smaller material deltas to automatic volume.

## 2026-11-05 D-0002 — initial research priority
Start by separating material dating from inscription dating, then audit Yale image and transcription provenance. No glyphs independently measured.

## 2026-11-05 D-0003 — physical foliation vs digital identity
Yale pre-1600 catalog SRC-0006 documents folds, missing/unnumbered leaves. Preserve physical and digital identity. EXP-0002.

## 2026-11-05 D-0004 — user-provided manifest accepted as untrusted, hash-pinned snapshot
A user provided 403041 bytes of Markdown-fenced claimed Yale IIIF v3 JSON. Parse and document compact metadata (EXP-0003) but do NOT assert verified live Yale provenance, copy full manifest, download image corpus or treat labels as manuscript glyphs. Obtain direct official attestation before promoting source authenticity. Automation unchanged.
