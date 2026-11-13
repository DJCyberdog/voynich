# A-01 — Currier A/B: Primärtext-Prüfung und trennscharfe Vorregistrierung (ohne Manuskripttest)

**Datum:** 2026-11-09. **Arbeitsgrundlage:** owner-kanonische SRC-0007 unverändert; integriertes main vor Zyklus `eee6721615098918cce02bf76e4fdda26db60176`. **Status:** SOURCE_REVIEWED; Manuskript-Reproduktion NOT_REACHED. **Scope:** nur A-01. A-02 wird als abhängiger, separater Claim nicht automatisch bewertet.

## Forschungsfrage
Behauptet Prescott Curriers Originalvortrag 1976 tatsächlich zwei nachweisbare natürliche Sprachen, oder unterscheidet er zunächst zwei statistische Schreibregime, die durch Schreiber/Abschnitt/Transkription erklärbar sein könnten?

**Primärtext / Editionsstatus:** Prescott H. Currier, „Some Important New Statistical Findings“, in *New Research on the Voynich Manuscript: Proceedings of a Seminar*, 30. November 1976, herausgegeben von M. E. D'Imperio; elektronisch transkribiert von Jacques Guy und Jim Reeds im Januar 1992: https://www.voynich.nu/extra/curr_main.html. Am 2026-11-09 direkt eingesehen. Das ist eine **spätere Transkription eines Autorenoriginals**, keine eigenhändige Autografen- oder Manuskriptbildprüfung. Die vorliegende Webedition enthält Tabellen und Originalvortrag, aber keine unabhängig ausgeführte moderne Corpusreproduktion. Ihre Rechte sind separat zu prüfen, bevor größere Teile übernommen werden.

## Neue eng begrenzte Beobachtung
1. Currier nennt A und B explizit „languages“ als **Arbeitsbegriff** und räumt ausdrücklich ein, dass das nicht die normalen Konnotationen von Sprache hat (Abschnitt „Two Hands and two 'Languages' in the Herbal Section“, Anfang des Vortrags). Seine Beobachtung betrifft laut eigener Darstellung Unterschiede von Symbolfolgen und Häufigkeiten.
2. Die Klassifikation der ersten ca. 50 Herbal-Folios wird im selben Abschnitt **zugleich** mit verschiedenen Händen beschrieben. Diese historische Datengrundlage trennt damit nicht automatisch Scribe- von Regime-Effekt.
3. Currier berichtet später **mehr als zwei Schreiber**, aber nur zwei statistische „Sprachen“; damit ist die triviale Gleichsetzung „ein Schreiber = ein Regime“ ebenfalls nicht direkt seine These. Die Zahlen für unterschiedliche Schreiber sind Curriers historisches Urteil, nicht hier unabhängig geprüft.
4. Im Vortrag nennt er für die A/B-Charakteristika **keine vorbereiteten Vortragsfolien**, beschreibt aber an späterer Stelle konkrete Symbolzählungen und Kontexttabellen. Das reicht für eine **quellennahe Beschreibung seiner Behauptung**, nicht für deren heutige unabhängige Reproduktion.

**Evidenzstatus:** DOCUMENTED, dass der zugängliche Currier-Originaltext diese *Aussagen* macht; CLAIMED, dass die behauptete A/B-Trennung im Manuskript robust reproduzierbar ist; UNKNOWN, ob A/B über Schreiber, Sektion, Layout und Transkriptionskonventionen hinaus einen unabhängigen Faktor bildet. **Workflow:** A-01 ACTIVE / SOURCE_REVIEWED. Keine Aufwertung zu VERIFIED; keine Aussage zu natürlicher Sprache oder Entzifferung.

## Vorregistrierter nächster Test (nur Protokoll, keine Testausführung)
**H1:** A/B-Label lassen sich auf vorab separierten Folios anhand präfix-/suffix-/glyphn-gramm-basierter Merkmale **zusätzlich** zu Hand-, Sektions- und Layoutvariablen vorhersagen. **H0:** Bei Kontrolle dieser Kovariaten gibt es keine robuste zusätzliche Vorhersagekraft; die vermeintliche Trennung ist mit Schreiber-/Abschnitt-/Layout-/Editionsartefakten vereinbar. **Stärkste Gegenhypothese:** Scribe-, Sektion-, Layout- und Transkriptionskonventionen erklären das Muster, ohne zwei Sprachsysteme zu erfordern.

**Material/Gates:** Version und Rechte der konkreten EVA/IVTFF-Transkription festhalten; Currier-A/B-Label-Herkunft prüfen; Folio-Canvas-IDs mit SRC-0007 abgleichen, ohne `70v`/`72v`/`102v`-Partlabels als einfache Seiten zu behandeln. Überlappende Folios und Labels für Bild- und Textanalyse getrennt behandeln. Glyphenbefunde aus Yale-Fotografien nicht aus EVA-Werten rückprojizieren. Kein neuer Versuch, die gesättigte Live-Manifest-URL routinemäßig zu reauthentifizieren.

**Kontrollen:** (a) positive Kontrolle: bekannte, im Training belegte A/B-Folioetiketten, ausschließlich als **Pipeline-Sanity-Check**, nicht als unabhängige Bestätigung; (b) negative Kontrolle: Folio-label-permutation *innerhalb* der vorab definierten Hand-/Sektion-/Layout-Strata, nicht freie Tokenpermutation, um Confounding nicht zu zerstören; (c) robuste Alternative: Vergleich von Modellen `hand+section+layout` gegen `hand+section+layout+text_features`; (d) Transkriptionswitness- und Komma/Space-Sensitivität, keine stillschweigende IVTFF-Korrektur.

**Holdout:** Folio-gruppierter, vorab eingefrorener Testsatz; keinerlei Textzeilen derselben Folio auf Training und Test verteilen. Bei Strata ohne beide Labels ist eine stratifizierte Permutation nicht identifizierend; solche Strata als **BLOCKED für die betreffende Kontrollfrage** ausweisen, nicht beliebig umetikettieren. Vor dem Experiment erst Teststatistik, Fehlerrate, Baseline und Multiple-Testing-Korrektur festlegen. Ein statistischer Erfolg zeigt noch keine zwei natürlichen Sprachen.

**Falsifikationsgrenze:** Kein belastbarer Zusatznutzen gegenüber Kovariaten-/Transkriptionskontrollen in den vorab festgelegten Heldout-Strata widerspricht der *starken* unabhängigen A/B-Regime-These im getesteten Umfang. Umgekehrt bestätigt ein Zusatznutzen nur ein statistisches Regime, nicht dessen linguistische oder semantische Ursache.

## Ergebnis und nächste Aktion
**Ergebnis dieses Zyklus:** Die häufige verkürzende Formulierung „Currier bewies zwei natürliche Sprachen“ ist durch Curriers eigenen Wortlaut **nicht gedeckt**. Seine ursprüngliche A/B-Unterscheidung ist als historisch dokumentierte statistische Behauptung ernstzunehmen, aber die Trennung von Schreiber, Sektion und Layout bleibt offen. **Keine Manuskript-Falsifikation ausgeführt, keine Übersetzung, keine neuen Frequenzen.**

**Nächster Wiedereinstieg:** Beschaffe eine nutzungsrechtlich geprüfte, versionierte A/B-Folio-Labeltabelle und mindestens einen gepinnten Transkriptionswitness; prüfe vor dem Modellieren, ob innerhalb der Hand-/Sektionsstrata überhaupt beide A/B-Klassen vertreten sind. Sonst das nicht identifizierbare Experiment begründet blockieren und zu einem anderen P0-Kandidaten wechseln.

**Dublettenabgleich:** Nicht HYP-0001…0013 und nicht EXP-0017…0020; A-02 teilt CURRIER_SCRIBE_SECTION und darf die Quellenprüfung wiederverwenden, nicht als unabhängiges Experiment zählen. Quell-Audit in offenem PR #33; Queue/Protokoll in offenem PR #35. Dieser Zyklus ergänzt nur #35, kein weiterer PR.
