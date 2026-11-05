# Project memory — 2026-11-05

Canonical repository DJCyberdog/voynich. Initial empty-repo bootstrap `01ec8257cfaa9cd75e8fe008d9e1da8bf7182d7a`.

EXP-0001: parchment dating cannot alone date inscription. EXP-0002: Yale codicology describes 102 parchment leaves + one paper leaf, folding leaves and incomplete historical foliation; unqualified historical folio = digital index assumption rejected.

EXP-0003: User provided a complete-looking IIIF Presentation 3 Manifest JSON snapshot claiming `https://collections.library.yale.edu/manifests/2002046`. SHA-256 of 403041-byte fenced Markdown upload: `4aa05eb43637b15ce68ba3fa15eb2d2e69dccd65cc46a31e84f80e89cd1e155e`. Deterministic local parse: 213 canvases and painting annotations, 213 unique canvas IDs, 210 label strings, 183 simple r/v labels, 21 compound/part/foldout labels, 9 bracketed descriptive labels. Three labels occur twice: 70v (part), 72v (part), 102v (part). Direct official URL still HTTP 403, so **this is verified parsing of user-supplied bytes, NOT authenticated current Yale manifest**. No full original corpus copied; no glyph reading or language claims.

Resumption: authenticate independently fetched Yale manifest and metadata against snapshot, build pinned canvas/folio/physical-surface map and visually spot-check foldouts; audit image and EVA/IVTFF rights. Maintain independent identity layers. No text deciphered.
