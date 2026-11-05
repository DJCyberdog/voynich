# EXP-0010: Literal regex semantics stress test (2026-11-05)

**Question:** Can selected published regex conditions be executed literally without unintended matches or undocumented input conventions?

**Source:** Tobias Franke, "Das formale, maschinenlesbare Regelwerk (P-01 bis P-20)", v1.1 (4 Oct 2026), https://celler-presse.de/forschung/dokument/das-formale-maschinenlesbare-regelwerk-p-01-bis-p-20/ . Existing SRC-0011. Original archived P rules only; NOT the November decoder or G1.7 model.

**Method:** Execute each listed string as an ECMAScript RegExp against deliberately chosen synthetic tokens, with no preprocessing. This tests the published *literal conditions*, not the author's software.

| Published condition | Input | Observed literal match |
| --- | --- | --- |
| P-04 `^ykal|ykar` | `ykal` | yes |
| P-04 `^ykal|ykar` | `xykar` | yes |
| P-08 `-(am|ar|al)$` | `chedar` | no |
| P-08 `-(am|ar|al)$` | `ched-ar` | yes |
| P-07 list `[p, t, k, f, sh]` treated *as a regex character class* | `,` | yes |
| P-07 list treated as a regex character class | `s` | yes |
| P-07 list treated as a regex character class | `h` | yes |
| P-12 `(ol|ory|edy)$` | `shol` | yes |

**Findings:** (1) P-04 alternation means the beginning anchor applies only to `ykal`, not `ykar`; `^(ykal|ykar)` would enforce both alternatives at the start. This is a VERIFIED property of the printed regex, not proof of a software bug. (2) P-08 requires a literal hyphen before its ending, so a plain unhyphenated token does not match; whether upstream tokenization inserts that hyphen is UNKNOWN. (3) P-07's bracketed set appears to be a notation for base clusters, NOT necessarily a literal regex: interpreting it as a character class includes comma, space, s and h separately. Do not attribute that implementation to the author.

**Adversarial interpretation:** The claim that the printed conditions can be directly executed as a complete, unambiguous specification is not established without documented token representations, grouping and pipeline order. No evidence here that the complete current decoder actually mishandles these inputs. Synthetic strings are not manuscript observations.

**Next:** obtain source implementation, unit tests and input representation for P-04, P-07, P-08; check whether code adds grouping, preprocessing or semantic list handling. Keep this distinct from structural G1.7 and from historical semantic validation.
