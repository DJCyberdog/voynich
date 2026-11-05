# EXP-0013: Current decoder R1 odd-repeat segmentation ambiguity (2026-11-05)

**Source:** Tobias Franke, "Voynich-Manuskript: Ein interaktiver Decoder zur Untersuchung von Grammatik und Bedeutung", published 2026-11-01, https://celler-presse.de/forschung/dokument/voynich-manuskript-ein-interaktiver-decoder-zur-untersuchung-von-grammatik-und-bedeutung/ . Current publication says R1 splits runs of at least four identical active forms into pairs; a triple remains intact. The page describes a versioned rule set and word register but does not provide a directly accessible, frozen source-code archive through the article's visible text.

**Question:** Is the stated R1 rule sufficient to determine unique segmentation of odd-length runs of identical active tokens?

**Method:** Synthetic runs of 3,4,5,6,7 identical tokens; compare left-anchored and right-anchored pair grouping. Both groupings obey pairing for runs >=4, absent a published anchoring convention. No Voynich manuscript data used; no author decoder code executed.

| Run length | Left-anchored group sizes | Right-anchored group sizes | Distinct? |
| --- | --- | --- | --- |
| 3 | [3] (explicit triple exception) | [3] | no |
| 4 | [2,2] | [2,2] | no |
| 5 | [2,2,1] | [1,2,2] | yes |
| 6 | [2,2,2] | [2,2,2] | no |
| 7 | [2,2,2,1] | [1,2,2,2] | yes |

**Result:** The natural-language R1 description, taken alone, does not specify the location of the unpaired residual token in odd runs of length >=5. If later interpretation depends on group boundaries, left/right grouping may differ. This is a VERIFIED combinatorial underdetermination of the publicly stated rule, not a verified defect in the implementation. A fixed left-to-right traversal, token positions, or a fuller specification may remove the ambiguity.

**Additional limits:** The R1 rule is about *identical active forms*, not all repeats; synthetic test assumes that condition. The reported f78r qokedy repetition was not independently counted or re-transcribed. No semantic interpretation or manuscript prediction tested.

**Next decisive experiment:** Freeze actual decoder v0.2.5 source and word register; run length 3/4/5/6/7 fixtures under both context settings; inspect deterministic group boundaries and their downstream semantic impact. Then run preregistered folio-held-out semantic controls. Status: isolated model VERIFIED; actual decoder behavior UNKNOWN.
