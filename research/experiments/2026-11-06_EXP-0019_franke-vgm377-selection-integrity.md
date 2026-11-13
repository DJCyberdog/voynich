# VGM 371/377 – Data-Integrity-Audit der 176 Folios

**Untersuchungsdatum:** 6. November 2026  
**Umfang:** Ein begrenzter, adversarialer Reproduzierbarkeits-/Selektionsaudit. Kein Nachweis von Manipulation, Cherry-Picking, Ursprung oder Bedeutung des Manuskripts.

## Kurzbefund

**Die veröffentlichte Auswahl der 176 Folios ist aus den derzeit öffentlich nachvollziehbaren Angaben nicht eindeutig rekonstruierbar.** Ohne `VGM356/interlinear_all.csv`, `VGM377/run377.py`, die vollständige 176-ID-Liste und die versionierte Selektions- und Tokenisierungskonfiguration ist nicht entscheidbar, ob die Auswahl einer prospektiven sachlichen Regel folgte oder von bereits betrachteten Modellwerten beeinflusst wurde.

**Neuer konstruktiver Befund:** Unter einer expliziten *anderen* Pipeline — aus der vom Nutzer bereitgestellten ZL3b-n v3b ausschließlich P-Textzeilen auslesen, unsichere Kommata als Trenner (split) behandeln, nur reine ASCII-EVA-Tokens akzeptieren — lassen sich **mindestens zwei verschiedene** Teilmengen zu je 176 Transkriptions-Folio-IDs finden, die **alle** publizierten Aggregate gleichzeitig treffen, einschließlich der Einzelklassenhäufigkeiten und der Anzahl Ein-Token-Zeilen. Die beiden Teilmengen unterscheiden sich in **44 Folio-Mitgliedschaften** (22 je Richtung). Sie erzielen aber verschiedene Markov-Vorteile von **0,01671266** und **0,01650717** statt Frankes veröffentlichten **0,01700337** nats/Übergang. **Sie sind weder die tatsächliche noch eine wahrscheinlichere Auswahl Frankes.** Sie belegen ausschließlich die Nicht-Eindeutigkeit einer Inversion aus aggregierten Ergebnissen.

## Primäre Quellen

- **VGM 377** (Franke/Celler Presse, 18.10.2026): https://celler-presse.de/forschung/dokument/vgm-377-generative-reproduction-of-voynich-class-sequence-structure/ ; nennt 176 Folios, 3.633 Zeilen mit mindestens zwei Tokens, 27.266 Übergänge, fünf folio-getrennte Folds, Alpha 0,5, Seed 377 und Daten-/Skriptnamen `VGM356/interlinear_all.csv`, `VGM377/run377.py`, `fold_results.csv`.
- **G1.7 / VGM 371** (Franke/Celler Presse, 18.10.2026): https://celler-presse.de/forschung/dokument/voynich-manuscript-provisional-integrated-model-g1-7-scientific-interim-report/ ; 176 Folios, 3.659 Zeilen, 30.925 Tokens; OTHER=24.180, EDY=3.804, OL=2.874, ORY=67. Vier orthografische Suffixklassen sind keine sprachlichen Bedeutungen.
- **Alternative lokale Quelle:** Nutzer-Upload `ZL3b-n.txt` Version 3b vom 13.05.2025, SHA-256 `bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc`. Original lokaler Parser `voynich_full_corpus_cv(1).py`, SHA-256 `7acf5cb70b6197549d71cd2f1b91bda3a72d1c7885d63db76522454083017e89`. Beide lokal verifiziert, aber nicht identisch mit der uns unbekannten VGM356-Quellpipeline.

### Provenienzgrenze

Am 06.11.2026 waren die genannten VGM356/VGM377-Quelldateien nach gezielter Suche der veröffentlichten Projektseite, Websuche nach den exakten Dateinamen und GitHub-Dateisuche **nicht als überprüfbare Dateien auffindbar**. Die Veröffentlichungen *nennen* diese Artefakte, aber geben keine vollständige Folio-Mitgliedschaft und keine herunterladbaren zeilenweisen Nachweise. Ein negativer Suchbefund ist kein Beweis für Nicht-Existenz, Geheimhaltung oder Manipulation.

## Prüfung 1 – Interne arithmetische Konsistenz

Frankes Werte stimmen unter der Annahme zeileninterner Übergänge mathematisch: 30.925 Tokens minus 3.659 nichtleere Zeilen = 27.266 Übergänge. Von den 3.659 nichtleeren Zeilen haben 3.633 mindestens zwei Tokens, sodass genau 26 Zeilen ein einzelnes Token besitzen müssten. **VERIFIED** als arithmetische Aussage, **DOCUMENTED** als Ausgangsaggregate, aber keine Validierung der Original-CSV.

## Prüfung 2 – Kann eine bloße Folio-Auswahl diese Aggregate erzeugen?

Pro Folio wurden die gezählten akzeptierten Tokens nach ALL/P-Zeilen und drei Unsicherheitsbehandlungen `exclude`/`join`/`split` aus der hochgeladenen ZL3b-n v3b rekonstruiert. Das 0-1-Auswahlproblem lautet:

> Wähle pro Folio-Kennung entweder 0 oder 1; erzwinge exakt 176 Ausgewählte, 3.659 nichtleere Zeilen, 3.633 Zeilen mit ≥2 Tokens, 26 Einzel-Token-Zeilen, 30.925 Tokens und die exakten vier Klassenzahlen (OTHER/EDY/OL/ORY).

Zunächst wurde jeweils sogar die *gelockerte* lineare Optimierung (0≤Auswahlwert≤1) auf Erfüllbarkeit geprüft. Ein Unmöglichkeitsnachweis für die lockerere Version ist auch ein Unmöglichkeitsnachweis für eine echte 0-1-Folioauswahl.

| Zeilenumfang | Unsichere Kommata | Erfüllbarkeit der linearen Relaxation | Folgerung |
|---|---|---|---|
| Alle | Exclude | Unmöglich | Reines Entfernen von Folios unter diesen Regeln kann die publizierten Aggregate nicht erzeugen |
| Alle | Join | Unmöglich | Gleiches |
| Alle | Split | Unmöglich | Gleiches |
| Nur P-Textzeilen | Exclude | Unmöglich | Gleiches |
| Nur P-Textzeilen | Join | Unmöglich | Gleiches |
| **Nur P-Textzeilen** | **Split** | **Erfüllbar** | Zwei getrennt konstruierte echte 0-1-Zeugen erfüllen *alle* Zielzahlen |

**Beachte:** Feasibility für `P + split` zeigt *nur*, dass diese Tokenisierungsvariante mögliche Aggregat-Zeugen besitzt. Sie zeigt nicht, dass Franke diese Variante gewählt hat. Die VGM356-CSV kann aus einer anderen Transkriptionsversion, Qualitätsfilterung, Folio-Konvention oder Segmentierung stammen.

### Zwei verschiedene exakte Zählzeugen

| Kennzahl | Kandidat W1 | Kandidat W2 | Franke publiziert |
|---|---:|---:|---:|
| Ausgewählte Folio-IDs | 176 | 176 | 176 |
| Nichtleere Zeilen | 3.659 | 3.659 | 3.659 |
| Zeilen mit ≥2 Tokens | 3.633 | 3.633 | 3.633 |
| Zeilen mit 1 Token | 26 | 26 | daraus 26 |
| Tokens | 30.925 | 30.925 | 30.925 |
| Übergänge | 27.266 | 27.266 | 27.266 |
| OTHER / EDY / OL / ORY | 24.180 / 3.804 / 2.874 / 67 | identisch | identisch |
| **Markov-Vorteil** (eigener Originalparser, Seed 377) | **0,01671266** | **0,01650717** | **0,01700337** (andere Pipeline) |
| Zusätzliche Rohzeilen ohne akzeptiertes Token | 1 | 2 | nicht öffentlich geklärt |

Bei beiden rechnerisch passenden Teilmengen sind alle fünf Markov-Folds unseres Evaluators positiv. **22 IDs werden von W1 gegenüber W2 ausgetauscht.** Aus den veröffentlichten Kennzahlen ist damit die Mitgliedschaft der 176 Folios keineswegs bestimmt.

**Wichtige Abgrenzung bei „Zeilen“:** Die beiden Zeugen haben 3.659 Zeilen *mit akzeptierten Tokens*, aber einschließlich vollständig verworfener Rohzeilen 3.660 beziehungsweise 3.661 Zeilen. Wenn Frankes Angabe 3.659 **sämtliche Rohzeilen** meint, ist keine dieser beiden Auswahlen eine vollständige Übereinstimmung. Ein zusätzliches 0-1-LP-Constraint „keine verworfene Rohzeile“ ist selbst in der gelockerten Relaxation **nicht erfüllbar** unter `P + split`. Der Publikation lässt sich diese Roh-/Akzeptiert-Zeilen-Konvention nicht sicher entnehmen.

## Prüfung 3 – Wie auffällig ist der publizierte Markov-Wert unter willkürlichen 176er-Auswahlen?

Explorativ und **nicht auf die publizierten Summen konditioniert** wurden 5.000 zufällige 176er-Teilmengen aus den 206 verfügbaren P-Folio-Kennungen des lokalen `split`-Korpus gezogen; reproduzierbarer Seed 1200261106. Alle wurden mit denselben fünf Folio-Folds (Seed 377), Unigramm-/Markov-Formeln und Alpha=0,5 ausgewertet.

| Vergleichswert | Ergebnis (nats/Übergang) |
|---|---:|
| Mittelwert der 5.000 Zufallsauswahlen | 0,01737275 |
| Median | 0,01737080 |
| 2,5–97,5 %-Bereich | 0,01548285 – 0,01931842 |
| Frankes berichteter Wert (nur Vergleichsmarke) | 0,01700337 |
| Zufallsauswahlen ≥ Vergleichsmarke | 65,46 % |

**KRITISCHE Einschränkung:** Die 5.000 Zufallsziehungen enthielten durchschnittlich **28.958 Tokens**, Franke meldet **30.925**. Nur **4 von 5.000** zufälligen Auswahlen erreichten mindestens 30.925 Tokens. Die Zufallsverteilung ist deshalb *keine* fair konditionierte Nullverteilung für Frankes tatsächlichen Datensatz und erlaubt **keinen Vorwurf und keine Entlastung** bezüglich Cherry-Picking. Sie zeigt allenfalls, dass der Wert 0,01700337 nicht isoliert außergewöhnlich erscheint, wenn man die ungematchte ZL3b-n-Teilmengenverteilung betrachtet.

## Prüfung 4 – Wurden Regeln vor der Ergebnissichtung fixiert?

**BLOCKED / UNKNOWN.** Aus dem publizierten Bericht sind der formale Klassifikator, Alpha, fünf Folds und Random Seed dokumentiert, aber **nicht** die vollständige Auswahl-/Ausschlusslogik mit Versionierung und Zeitstempeln. Eine nachträgliche Erklärung kann ausreichen, um die Statistik exakt zu reproduzieren, belegt aber noch keine **prospektive** Festlegung. Für einen Manipulationsvorwurf wären zusätzliche Hinweise wie Provenienz-/Versionskonflikte, nachträgliche auf Score optimierte Auswahl bei gegenteiliger Methodenzusage oder bewusst irreführende Darstellung erforderlich; nichts davon ist derzeit nachgewiesen.

## Wissenschaftliche Entscheidung

- **VERIFIED:** Frankes publizierte Aggregatsummen sind arithmetisch konsistent. Die lokal geprüften sechs Parser-/Zeilentypvarianten haben die oben genannten Feasibility-Eigenschaften; die beiden `P + split`-Zeugen erreichen exakt die publikationsseitigen Zählsummen, aber unterschiedliche Markov-Vorteile.
- **DOCUMENTED:** Franke beschreibt Modellklassen, Kennzahlen und nennt die Originalartefakte mit Dateipfaden.
- **CONTRADICTED (enger Scope):** Die publizierten Summen erzwingen eine eindeutige 176er-Folio-Auswahl. Sie sind außerdem mit einer unveränderten reinen Folio-Selektion unter fünf unserer sechs getesteten lokalen Parserkonfigurationen unvereinbar.
- **UNKNOWN:** Frankes tatsächliche 176 IDs, seine CSV-Rohwerte/Tokenisierung, Art und Chronologie von Ausschlüssen, unveränderte Replikation seiner 0,01700337 und irgendeine absichtliche Auswahl von günstigeren Ergebnissen.

**Antwort auf die Eigentümerfrage:** Es ist derzeit *nicht bewiesen*, dass die 176 Folios zwangsläufig aus einer objektiven Regel folgen; aus den veröffentlichten Summen allein folgen sie definitiv **nicht eindeutig**. Ebenso gibt es **keinen Beleg**, dass Franke die 176 Folios wegen günstiger Modellleistung auswählte. Diese Alternative bleibt bis zum Originaldaten-/Code-Audit offen.

## Benötigte Originalartefakte und entscheidender Fortsetzungstest

Erforderlich sind `VGM356/interlinear_all.csv` samt SHA-256 und Versions-/Zeilenherkunft, `VGM377/run377.py`, `VGM377/fold_results.csv`, die 176 individuellen Folio-IDs, ggf. `VGM371/run371.py`/frozen G1.7-Konfiguration, alle Vorfilter-/Transkriptionsentscheidungen, und Belege dafür, **wann** die Filter/IDs relativ zur Auswertung feststanden. Danach pro Rohzeile Ursache und Zeitpunkt jedes Ausschlusses prüfen, Original-CV-Score byte-/numerisch reproduzieren und *erst dann* alternative sachliche Vorauswahlen unter identischem Parser vergleichen. Ohne diese Dateien keine geschlossene Manipulations- oder Entlastungsentscheidung.

## Reproduzierbarkeit und Dateien

- `franke_vgm377_selection_integrity.py`: komplettes Audit mit lokalem ZL3b-n-/Owner-Parser, linearen Machbarkeitsprüfungen, zwei konstruierten Zeugen und 5.000 Zufallsauswahlen.
- `franke_vgm377_data_integrity_summary.json`: vollständige Ergebnisse und beide exakten ID-Listen.
- `franke_vgm377_data_integrity_random_draws.csv`: 5.000 Markov-Gewinne + Token-/Übergangssummen (keine EVA-Transkriptionspassagen).

Befehl (bereits ausgeführt):

```bash
python franke_vgm377_selection_integrity.py --input ZL3b-n.txt \
  --owner-parser 'voynich_full_corpus_cv(1).py' \
  --output-prefix franke_vgm377_data_integrity --trials 5000
```

Keine Originaltranskription, gescannten Seiten oder fremden Mediendateien in den Ergebnissen gespeichert.