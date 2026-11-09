# FORTY-CLAIM PROGRAMME — Prüfordnung für die 40 Voynich-Audit-Einträge

**Stand:** 2026-11-09 · Owner-Priorität. **Status:** PLAN ONLY / keine neuen Manuskriptmessungen. Arbeitsrepository ausschließlich `DJCyberdog/voynich`. Aufsetzpunkt verifiziertes `main` `eee6721615098918cce02bf76e4fdda26db60176`.

## Eingangsartefakte: zwei ausdrücklich UNGEMERGTE Draft-PRs
- [PR #33](https://github.com/DJCyberdog/voynich/pull/33): `research/hypotheses/2026-11-09_top20_critical_audit.md`, Head `c298262c8773d08e31ae8832141cafb05835f122`. Kandidaten `A-01`…`A-20`; **A steht hier für Audit-Liste, nicht für Prioritätsklasse**.
- [PR #34](https://github.com/DJCyberdog/voynich/pull/34): `research/hypotheses/2026-11-09_weird_erotic_20_audit.md`, Head `edffa19f36877be590b0beaf212118e7f7c9f83a`. Kandidaten `W-01`…`W-20`.
- Die 40 IDs referenzieren **40 abgrenzbare Behauptungs-/Prüfpunkte**, **nicht 40 unabhängige Hypothesen, Publikationen oder Beweisstücke**. Einträge können dieselbe Originalarbeit, Abbildung oder Testbedingung betreffen; wiederverwendete Ergebnisse zählen nicht als unabhängige Replikation.
- Beide PRs sind anfangs Drafts und teilen Dateipfade mit #25–#31. Keine direkte Änderung an deren Branches, kein Merge ohne gesonderte Owner-Autorisierung und erneute Kollisionsprüfung.
- Vor Bearbeitung jedes Kandidaten Quell-PR/Head/Report und integrierten Stand **neu prüfen**; nach Merge referenzierende Queue-IDs erhalten, ohne die ursprünglichen Reports zu kopieren oder zu überschreiben.

## Arbeitsregister und Bedeutung
`research/hypotheses/2026-11-09_40_claims_queue.jsonl` ist der eine indexierte **Bearbeitungsplan**: 40 JSONL-Zeilen, Schlüssel `A-01…A-20` und `W-01…W-20` einmalig. Noch **KEINE** neuen kanonischen `HYP-xxxx` oder `EXP-xxxx` erzeugt. Kanonische Evidenz bleibt in vorhandenen Hypothesen-/Experimentregistern; ein neues Experiment erst nach wirklicher Preregistration und mit tatsächlichem Test. Eintragseigenschaften:
- `queue_priority`: **P0/P1/P2** nach Erkenntnisgewinn/Aufwand, ohne Wahrheits- oder Erfolgschance.
- `evidence_status`: nur `VERIFIED/DOCUMENTED/CLAIMED/INFERRED/UNKNOWN/CONTRADICTED`; Autorenmeinung ist **CLAIMED**, Wikipedia nur Fundstelle.
- `operational_status`: nur `ACTIVE/WATCHING/BLOCKED/SATURATED/RETIRED`; unabhängig von Evidenz.
- `audit_stage`: `QUEUED → SOURCE_REVIEWED → PREREGISTERED → TESTED → SYNTHESIZED`, bei fehlenden Voraussetzungen auch `SCOPED_BLOCKED` oder `SCOPED_RETIRED`. Diese Bearbeitungsphasen **dürfen Evidenz- oder Workflowstatus nicht ersetzen**.
- `completed=true` erst mit test- oder quellenkritisch begründetem Abschlussbericht samt Originalreferenzen, stärkster Alternative, eng begrenztem Ergebnis und ggf. BLOCKED-/RETIRED-Grund; keinerlei automatischer `VERIFIED`-Status.

## Plan für jeden *einzelnen* stündlichen Forschungszyklus
1. **Delta-first:** tatsächliches `main`, alle offenen PRs, sämtliche 14 Pflichtdateien und beide Audit-PRs/Queue lesen; vorige Berichtsergebnisse und Gruppenzugehörigkeit gegen Dubletten prüfen.
2. Wähle **genau einen** noch nicht sachlich abgeschlossenen Kandidaten oder **einen** begrenzten, gemeinsam falsifizierenden Test einer zugeordneten Gruppe. Standard: P0, dann P1, dann P2; bei fehlenden Rechten/Originalen Kandidaten **begründet** BLOCKED setzen und einen anderen möglichen Kandidaten wählen, statt in einer Schleife dieselbe URL anzufragen.
3. Originalveröffentlichung und gegebenenfalls historischen Primärbeleg prüfen, Abbildungen/Transkriptdateien nur nach Nutzungsrechteprüfung. Trenne Quelle, Manuskriptfoto, sichtbare Glyphen, EVA/IVTFF, Tokenisierung, Statistik, Bildassoziation, Semantik, historische Zuschreibung.
4. Vor irgendeinem tatsächlichen Test dokumentiere *vor dem Ergebnis* genaue Vorhersage, beste Gegenhypothese, Falsifikationsgrenze, positive und negative Kontrollen, Nullmodell, Daten-/Rechteumfang, Folio-Holdout, parser/transcription policy und Streu-/Mehrfachtest-Risiko. **Falsifikation wird nicht aus einer Suchsnippet-Bewertung abgeleitet.**
5. Führe nur den zulässigen und materiell neuen Test aus, dokumentiere auch negative/ungeklärte Resultate. Wenn Daten fehlen, **SCOPED_BLOCKED** mit präziser menschlicher Inputfrage oder Rechteprüfung und auf nächsten unabhängigen Kandidaten wechseln.
6. Bei gemeinsamen `hypothesis_family`-Gruppen genau **einen** gemeinsamen Referenztest führen. Für jeden abhängigen Claim nur die *ihm tatsächlich entsprechende* Aussage neu bewerten; kein 9-fach gezählter Rosettenbeweis. Fairer Wettbewerb natürlicher Sprache, Chiffren, nichtsprachlicher und hybrider Ansätze mit gleichen Kontrollen.
7. Konsistente Änderung **ausschließlich im isolierten Branch und PR** nach Scope-/PR-Abgleich, keine künstlichen NO_CHANGE-Commits. Keine direkte main-Schreiboperation, kein Force-Push, keine Fremdrepos, keine unautorisierten Fremdprogramme, keine unlizenzierte Datenkopie. Branch/Draft-Rückstau nicht weiter aufblasen: vorhandene kompatible Forschungs-PRs prüfen; reine Sichtungsfälle in den Kampagnen-PR statt zahllosen redundanten Drafts; andere PRs nicht ohne Owner zusammenführen.
8. Kompakter Bericht: `RESEARCH_COMPLETED/NO_CHANGE/BLOCKED`, tatsächlich geprüftes `main`, Claim-ID, Quelle/Evidenz/Workflow, Falsifikation/Alternativen, neue Artefakte, PR/Merge-Status, nächste konkrete Aktion. Maximal **zwei** erfolglose unveränderte Runden am selben Kandidaten; danach BLOCKED/WATCHING und zur nächsten unabhängigen Aufgabe. Wenn alle 40 sachlich geprüft oder ausdrücklich blockiert sind: **SYNTHESIS** mit offenen Restfragen; niemals 40 Ergebnisse erzwingen.

## Querschnitt-Gruppen zur Vermeidung von Scheinevidenz
- CURRIER_SCRIBE_SECTION: 2 entries
- BREWER_ROSETTES: 10 entries
- TUCKER_MESOAMERICA: 3 entries
- SHERWOOD_BIRTH: 2 entries
- BARON_MICROSCOPY: 4 entries
Wichtig: `A-19` und `W-01…W-09` teilen Brewer/Lewis als Quelle; `A-20` und `W-17/W-18` überlappen mesoamerikanische Deutungen. `W-12…W-15` stammen aus einem einzigen Mikroskop-/Reproduktions-Abstract. Die bloße Wiederholung einer Hypothese in 40 Zeilen erzeugt keine weitere Evidenz.

## Fortschrittsdefinition — keine Schein-Prozente
- **Kandidaten inventarisiert:** `40/40` = **100 % der owner-definierten Liste**, durch Überschriften in PR #33 und #34 verifiziert; kein universeller Hypothesenkatalog.
- **Im neuen Prüfprogramm einzeln sachlich abgeschlossen:** `0/40` = **0 % der 40 Prüfpunkte** zum Start des Programms. Dokumentarische Vorinventarisierung ist nicht eine neu durchgeführte unabhängige Falsifikation.
- **Unabhängige neue manuskriptbezogene Tests im neuen Programm:** `0` zum Start; bei späteren Fällen Testumfang explizit mit festem Nenner ausweisen, nicht alle 40 als `TESTED` zählen.
- **Kanonischer Yale-Canvas-Index:** `213/213` IDs = **100 % Snapshot-Inventarisierung**, keine unabhängige Folio-/Bildprüfung.
- **Entzifferungsgates:** `0/5` = **0 % der fünf Anforderungen dokumentiert erfüllt**, *keine* Wahrscheinlichkeit einer Lösung.
- **Quellen- und Schreibrechte:** originale Yale-IIIF-Kopie SRC-0007 nach D-0005 Owner-kanonisch; unabhängige Live-Yale-Authentifizierung nicht erfolgt und wegen gesättigter 403-Tests nicht routinemäßig wiederholen.

## Erfolgskriterium
Nicht 40 neue PRs, sondern **40 transparente Einzelentscheidungen** (bestätigte eng begrenzte Vorhersage, widerlegte Vorhersage, ungeklärtes Modell, mangels Daten/Rechten blockierte oder wegen Unprüfbarkeit zurückgestellte Folklore), mit *geteilter* Evidenz nur dort, wo logische Ableitung tatsächlich trägt. Kein Entzifferungsanspruch ohne alle Kriterien aus `docs/DECIPHERMENT_CRITERIA.md`.

**Vorliegendes Dokument richtet das Programm ein; es behauptet keine erfolgreich ausgeführten Tests.**
