# EXP-0025 — byte-exact frozen repository-script reexecution (2026-11-13)

**Execution after owner-authorized integration review.** This is a new reproducibility follow-up; the original frozen preregistration and earlier experiment outcomes remain historically unchanged.

- Frozen GitHub script: `research/scripts/exp0025_eva_bridge.py` as in `9d1bb16c1a2e5c2b80730ab5ce37eda6085e0637`; its verified Git blob ID is **67e6a9d222c3a3930d0a6ad8994cda889d3b3d98**. The local byte-for-byte reproduction passed `git hash-object` equality, despite internet-isolated runtime.
- Input: locally held `ZL3b-n.txt` SHA-256 **bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc**.
- Exact command: `python exp0025_frozen_github.py --input ZL3b-n.txt --output exp0025_frozen_result.json`; script `--selftest` also passed.
- Local script SHA256: **71a2546b7ea4beb3b5f96382d8b778924385fc991d6955a38580cd918ce5af8b**.
- Output JSON SHA256: **b1608c3c47ce804d0953e399d95ff9b3814767dda1d381c0021686b7d7e3c921**.
- Observed 160 training vs **43** held-out IVTFF folio IDs; **5,369** eligible heldout accepted words, **991** OOV exact word types. OOV top1: left-only **0.4328960645812311** vs bridge **0.6306760847628657**. OOV mean bridge gain **+0.659458308679125 nats**. Folio bootstrap 95% `[0.604368341635463,0.7244655104626426]`; **199** matched-right permutation controls, **0** exceedances, `p=0.005`; all frozen gates pass; synthetic positive **+1.0311579806695186** and negative **-0.00021052543579885212** nats, passed.
- Compared against prior independently implemented local `exp0025_results.json`: all experiment core counts, numeric scoring outcomes and pass gates agree; only microscopic float rounding in some null/control aggregates and intentionally different output field names in synthetic controls and gate dictionaries. **No changed scientific effect, corpus or holdout definition.**

**Strict interpretation:** Reproduced frozen repository implementation on its SHA-pinned single EVA editorial witness, NOT a new independent manuscript image or independently sourced transcription witness. A pair of recto/verso sides can remain split across folds, source labels represent editorial EVA ASCII characters rather than all physical grapheme classes. Competing strong copy/edit, cipher and nonsemantic models, rights-cleared independent glyph segmentation and full physical-leaf grouping remain open. **0/5 decipherment gates**, no Voynich translation.

These results confirm repeatability within the original narrow target; the exact-script execution gap in the **initial** report is now closed by this later follow-up, not retroactively rewritten.
