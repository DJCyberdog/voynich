# BLACKBOX 002 — Vaelun 1.0 methodological audit (2026-11-13)

**Status:** DOCUMENTED user-supplied synthetic-language test transcript; **not** a manuscript observation or decipherment result. **Scope:** one bounded methodological audit. No new Voynich EXP/HYP identifier assigned.

## Question and design
Can a model infer syntax and *independently* recover semantics from a small invented-language corpus? The user privately held a fixed Vaelun 1.0 key and graded predictions, but its immutability was not independently verified. The model received nine initial sentences, later additional positive examples, binary grammatical judgments, and then successive word glosses. No frozen preregistration artifact or blinded evaluator outside the conversation existed.

## Observations (conversation-reported, not independently replicated)
- Initial SVO hypothesis was supported by `Taren velis koran.` and reversal `Koran velis taren.`; invalid verb-first and misplaced-preposition controls were reported.
- `no` was hypothesized as preverbal negation; the user subsequently disclosed `no = nicht` and confirmed minimal pairs involving `nori`, `savi`, and `velis`.
- `in` was hypothesized as a locative marker; the user disclosed `in = in/innerhalb`, and location substitution `doma`/`vera` was confirmed in tested sentences. Orthographic resemblance is a confound.
- `savi` was initially classified as a transitive verb, **not** predicted to mean 'trinken'. After the gloss was supplied, `Taren savi miri.` and the semantically odd `Taren savi koran.` were both confirmed grammatical with literal compositional interpretations. The user explicitly stated no object-selection restrictions for `savi`.
- `sana` was observed in `Luma sana.` and `Koran sana.`; only after the user disclosed `sana = scheinen` did `Taren sana.` receive a correct syntactic and compositional prediction. German 'scheinen' is lexically ambiguous; no particular reading was demonstrated.
- `Nara kela.` and `Taren savi.` were **UNKNOWN / not adjudicable**: optional object omission was not specified in the key. Neither is a positive or negative test result.

## Full key disclosed at end (19 entries)
Nouns: taren=man, nara=woman, miri=child, koran=dog, aro=bird, doma=house, vera=tree, sela=water, pana=bread, luma=sun.
Verbs: velis=see, mara=eat, savi=drink, nori=sleep, tali=go, kela=like, sana=shine/seem ('scheinen'; reading unresolved).
Other: no=not, in=in/inside.

## Conclusions and limitations
**INFERRED (restricted):** local syntactic roles, SVO order, preverbal negation and locative composition can be predicted from simple examples when an interactive judge is available. The experiment **did not demonstrate blind semantic decipherment**. Most specific semantic assignments were provided by the judge, not discovered. Unadjudicable valency tests exposed a key specification gap. Post-gloss compositional predictions must not be scored as lexeme discovery. No independent negative-control corpus, held-out evaluation, or uncertainty calibration was executed.

**Identifiability limit:** lexical permutation can preserve distributional syntax while changing meanings; without an external semantic anchor, many assignments are observationally equivalent. This is a methodological argument, not a theorem about MS 408 or evidence that Voynichese encodes a language.

## Follow-up protocol (proposal, NOT executed)
1. Use a **new** language and genuinely unseen corpus; Vaelun 1.0 is contaminated for further semantic blind tests.
2. Freeze generation key, corpus, segmentation/transcription conventions, and scoring **before** model access; independent custodian retains the key.
3. Provide no word glosses, grammar judgments, or adaptive semantic hints during inference.
4. Preregister structural predictions and abstention/identifiability claims on held-out passages, with leakage-resistant partitions.
5. Compare with matched nonlanguage generators, shuffled and structured nulls, and alternative language grammars; separate syntax scores from semantic accuracy.
6. Evaluate any semantic guesses only after opening the sealed key, using independently defined accuracy and calibration metrics. If semantics are nonidentifiable, report that outcome rather than rewarding plausible stories.
7. For MS 408, keep source/transcription rights, folio holdouts and the five decipherment gates separate; synthetic success is a **method positive control only**, never manuscript translation.

## Governance
No main modification, no merge authorization presumed, no changes to automations or canonical evidence registers. Existing draft PRs overlap README/memory; this isolated report deliberately avoids those paths. Integrated decipherment gates remain 0/5 as stated on main.