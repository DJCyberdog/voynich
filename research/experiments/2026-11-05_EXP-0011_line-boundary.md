# EXP-0011: P-20 end-of-line context stress test (2026-11-05)

**Source:** Tobias Franke, archived formal P-01 to P-20 table v1.1, https://celler-presse.de/forschung/dokument/das-formale-maschinenlesbare-regelwerk-p-01-bis-p-20/ , accessed 2026-11-05, existing SRC-0011. The table describes P-20 as an end-of-line completion filter with literal regex `(sholdy|shols)$` and output `shocksol`.

**Question:** Does this published regex, by itself, enforce an exact complete-token match and manuscript line-final context?

**Method:** Execute ECMAScript RegExp `/(sholdy|shols)$/` on deliberately constructed inputs, without additional tokenization or line-position metadata.

| Input | Literal match |
| --- | --- |
| `sholdy` | true |
| `xxsholdy` | true |
| `sholdy foo` | false |
| `foo sholdy` | true |
| `foo sholdy bar` | false |

**Verified narrow result:** The printed regex is suffix-anchored but not start-anchored. It accepts `xxsholdy`; when applied to an individual token it has no way to establish manuscript line position. A parser may legitimately implement separate line-end gating or prefiltering, so this is a *specification completeness* issue, NOT evidence of an error in the actual executable decoder. For token-level exactness, `^(sholdy|shols)$` would be a stricter candidate; line-final gating still requires explicit context.

**Alternatives:** Regex is applied only after token validation; regex is run over an entire line; upstream passes an explicit line-final flag; additional rule precedence. These must be checked in frozen author implementation. The test inputs are synthetic; no claim of manuscript frequencies or semantic validation.

**Conclusion:** Direct literal condition alone is insufficient to implement both exact token identity and end-of-line gating (VERIFIED within isolated test). Actual full parser behavior UNKNOWN. No current decoder v0.2.5 execution, no G1.7 test, no Yale reauthentication.

**Next:** obtain version-pinned parser source or reproducible API and test P-20 on genuine final and nonfinal positions with matched token identity, plus negative controls with longer prefixed tokens.
