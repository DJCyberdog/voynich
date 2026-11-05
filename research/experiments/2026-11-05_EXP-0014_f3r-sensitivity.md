# EXP-0014: f3r token-boundary sensitivity and permutation control (2026-11-05)

Scope: Reanalyse the **20 previously embedded f3r lines** in the local pilot script (ZL3b-n v3b attributed to Zandbergen/Landini); source file not re-downloaded or independently byte-verified in this run. No claim about whole corpus, author decoder, or semantic decipherment.

Method: IVTFF period = confident word boundary; comma = uncertain. Three policies for comma-containing segments: (a) exclude whole uncertain segment, (b) join across comma, (c) split at comma (original pilot). Editorial <-> splits are treated as boundaries, an additional simplification. Keep only ASCII lowercase strings. Four suffix classes: ORY, EDY, OL, OTHER. Leave-one-line-out CV on 20 lines; additive alpha=0.5, 4 classes. Compare unigram and first-order Markov predictive negative log likelihood in nats per transition. Random control: 2,000 fixed-seed (1405) within-line shuffles per policy; empirical upper-tail p=(1+count(null improvement >= observed))/(2001). Null preserves line lengths and per-line class counts, not all positional structure.

| Policy | Tokens | Transitions | Unigram | Markov | Improvement | Positive lines | Null mean improvement | Empirical upper-tail p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Exclude | 104 | 84 | 0.491488 | 0.512562 | -0.021074 | 0 | -0.021354 | 0.4343 |
| Join | 109 | 89 | 0.474928 | 0.493757 | -0.018829 | 7 | -0.019595 | 0.4058 |
| Split | 114 | 94 | 0.508855 | 0.531232 | -0.022377 | 0 | -0.018777 | 0.6342 |

Observed sign is robust across these editorial treatments, but not significant relative to within-line permutation. Two classes only appear in this sample (OTHER/OL); four-class smoothing remains fixed. This cannot reproduce or falsify Franke VGM 377's 176-folio cross-validation, nor compare his semantic decoder.

**Audit correction:** Previous pilot's phrase 'exclude uncertain commas' was incorrect: its regex split on commas and retained fragments. Its numbers are reproduced exactly by the **split** policy. Document correction rather than silently overwriting history.

Evidence: locally executed Python with deterministic seeds; raw f3r line provenance only DOCUMENTED from prior pilot, not source-byte authenticated. Next: full authenticated ZL3b-n v3b with editorial provenance, folio-held-out CV, author source archive, and semantic anchors.
