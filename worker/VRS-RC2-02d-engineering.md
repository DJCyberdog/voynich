# RC2-02d — portable region evidence and technical/scientific gate separation

Owner approved the sequencing correction 2026-11-27. The experimental artifacts, external reference audit and previous counterevidence remain authoritative for their exact method and data. No criterion removed: independent physical leaf boundaries, material/illustration/other-script discrimination, external registration and reliable classification quality move to the combined system evaluation in RC2-02h. RC2-02g must preserve all unresolved alternatives and integrate the existing Runtime, not build a parallel pipeline. RC2-02d LOCAL ENGINEERING BASELINE PASS, not a scientific or production PASS.

## Implementation
worker/vrs_region_evidence.py (blob fa49572d4ba1158f5a82d6c023ca4c4b5332dfa3) requires only already managed NumPy/Pillow. Three grayscale thresholds 30/50/70; 3x3 neighborhood majority support (zero padding); intersect horizontal and vertical spans. Return three aligned material hypotheses plus disjoint intersection, disagreement and outside-union masks. These are axis-aligned envelopes, not physical leaf outlines. They can bridge disconnected leaves or miss dark borders. They never gate ink extraction or authorize deletion. Context grouping reuses the existing script-zone proposal logic from experiments/vrs_geometry.py with duplicate ID and geometry guards; script type remains UNRESOLVED. Record includes source/page identity, native origin and dimensions, RGB/votes/component digest, method count, material-mask digests, proposed zone boxes and component IDs, exclusion_authorized=false; deterministic ID. Caller supplies source identity; this is not an authenticated registration certificate. Record is generated in memory, not yet integrated into durable Runtime. Existing component flags remain authoritative and caller supplies them; no trained model or genuine script classifier here.

## Executed evidence
Five local unit tests PASS: material partition and immutability, dark image, zone grouping/tiny-component exclusion from grouping only, deterministic identity and changes in source page/component evidence, invalid geometry/vote/duplicate IDs. Exact tests blob 528694166e06f571f112a45d0a95138c473b7226. Prior 55039a5 three hosted workflows completed successfully. New hosted execution still pending. Source-bound full-image material audit experiments/audit_region_material.py blob a4f6c73b2caa9ccb42aba0d9f5fdbb9e8b692d5a. From worker, PYTHONPATH=worker, python experiments/audit_region_material.py PRIVATE_PDF. Rechecked pinned PDF SHA-256 d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c. Initial Pillow median-filter approach exceeded local execution limit; replaced by explicit NumPy neighborhood majority and reran tests/audit. Final full audit completed local Linux in 17.31 s (excludes source hash verification, includes page decode, hypotheses and assertions; not owner target throughput).

| Check | Count |
|---|---:|
| PDF pages | 214 |
| Native RGB images | 213 |
| Metadata-only pages | 1 |
| Native pixels | 338025600 |
| Core/intersection | 312913190 |
| Disagreement | 604715 |
| Outside union | 24507695 |
| Empty core images | 0 |

All partitions exhaustive, disjoint, aligned and consistent with the method masks; every original RGB byte retained. Counts are method agreement, not accuracy. Full-corpus material-only audit; script-zone grouping and evidence record verified by synthetic tests in this turn, previous real-window experiments remain documented separately. No full-corpus script/segmentation run or owner Windows performance claim. No new dependency or external private data committed. Scientific quality gate in h still NOT_MET/BLOCKED; no further owner file acquisition requested at this stage. Next g: integrate non-destructive evidence, vectors, grouping alternatives, durable identities, review and replay. No intermediate patch ZIP.
