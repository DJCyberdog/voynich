# EXP-0016 — Algebraic transition-count consistency audit (2026-11-05)

## Scope and preregistered logical prediction
Question: Are the owner-reported EXP-0015 token/transition totals **compatible** with transitions counted only between adjacent accepted tokens inside nonempty transcription lines? This is a deterministic necessary-condition audit of already published aggregates, **not** a rerun of the transcription parser, a permutation test, or manuscript observation. Data were recorded before this audit in the merged EXP-0015 report.

For each line with `n >= 1` accepted tokens, the number of adjacent within-line transitions is `n-1`; a line with zero accepted tokens has zero transitions. Therefore, if every within-line adjacency is counted exactly once and no cross-line transitions are counted, `tokens - transitions = number of nonempty accepted-token lines`. With 5,225 matched lines, inferred zero-token lines = `5225 - (tokens-transitions)`. Reject internal compatibility if inferred nonempty lines are negative, exceed matched lines, or disagree with an independently stated zero-token count under the same policy.

## Inputs, calculation and controls

| IVTFF comma policy | Matched lines | Owner-reported accepted tokens | Owner-reported transitions | Implied nonempty lines | Implied zero-token lines |
|---|---:|---:|---:|---:|---:|
| Exclude | 5,225 | 32,147 | 27,038 | 5,109 | 116 |
| Join | 5,225 | 34,415 | 29,269 | 5,146 | 79 |
| Split | 5,225 | 37,105 | 31,956 | 5,149 | 76 |

Positive control: EXP-0015's separately reported `lines_with_no_accepted_tokens = 116` for **exclude** agrees exactly with `5225 - (32147-27038)=116`. Negative control: a deliberately invalid transition total greater than tokens would imply a negative nonempty-line count and fail this test; this is a mathematical control, not an executed parser perturbation. No independent join/split zero-token line count is available here.

## Falsification result and alternative
**VERIFIED** arithmetic identities from **DOCUMENTED** owner-reported aggregate inputs. All three policies are internally *compatible* with line-local adjacency accounting. This does **not** establish the identities of individual lines, correct IVTFF parsing, source integrity, fold assignment, statistical significance, or even that the software actually counted only within-line transitions. Alternative explanation: erroneous token filtering and erroneous transition counting can still produce the same algebraic totals. The test does not discriminate natural-language, cipher, nonlinguistic or mixed explanations. It is not an independent reproduction of EXP-0015.

Operational status: **ACTIVE** reproducibility work, confirmatory full-corpus test **BLOCKED** until exact input bytes and parser are frozen and independently checked. No Yale manifest reauthentication attempted; owner-canonical SRC-0007 remains distinct from independent live authentication.

Next: freeze owner-reported script and ZL3b-n v3b bytes, audit actual accepted-token line counts under all three policies, then execute preregistered within-folio and within-line shuffles with held-out folds. Do not treat this arithmetic check as a permutation p-value or decipherment gate.
