# K-0001 INV-007 — Owner-Annotation und explorativer Quellenbildvergleich (2026-11-16)

**Scope / Status:** Ein begrenzter, bildbezogener f1r-Zyklus auf `DJCyberdog/voynich`. **RESEARCH_COMPLETED nur explorativ**, keine erfolgreiche formale INV-005-Blindprüfung, keine neuen Grapheme oder EVA-Zuordnungen. Delta-first: `main` vor Arbeitsbeginn `11a6223b1a5521bf4e962db8327e57326a4a121f`, null offene PRs. Alle sechs Pflichtdokumente, acht Memory-Dateien, README, 40er-Queue und INV-005/006 geprüft.

## Prüffrage und Primärquelle

Können die eigens vom Owner markierten Gruppen auf **f1r.1** quellpixelgenau dokumentiert und unabhängig von EVA mit einem ausschließlich am Originalbild arbeitenden Verfahren verglichen werden? Owner-PDF (214 Seiten), SHA-256 `d095900be761dd8702a63cf79f83a09e832f98e4abd0d4ea394d6c47e8d35a7c`, f1r = PDF-Seite 4, PyMuPDF-Raster 1489×2105 RGB, SHA `cbd95103a136471df3a27933f881fa4de7664c1d1075c4930c5e9e24234daf10`. Original-ROI `[760,337,1050,414]` = 290×77 Pixel. Originale handmarkierte Benutzer-PNG 960×255 SHA-256 `c980e9fa87520e29b276e468bfd49b68c2c8423061b72c65edd1ef534b6d4190`. Diese Originaldatei, andere Bildpixel und Transkriptionszeilen werden **nicht** ins Repository kopiert. Quellenregister SRC-0108.

## Wesentlicher Befund — Zahl der vom Menschen gemeinten Flächen

Der Owner hat nach Rückfrage **ausdrücklich acht (8) umrandete Innenflächen** angegeben. Die vorherige assistentenseitige Schätzung `vier Nutzerflächen` war falsch. Die automatische Maske erkennt zwar sechs zusammenhängende schwarze Liniennetze, aber nur **vier** vollständig geschlossene, nicht randberührende Maskenhohlräume ab 100 Bildschirmpixeln. Das ist **kein Widerspruch zum menschlichen Zählwert**: Überlappende/geteilte Linien, offene Ränder, Bildskalierung und nicht als Polygon geschlossene Gruppierungen führen zu anderen topologischen Flächen. Die automatische Vier darf niemals als Korrektur der Owner-Acht dargestellt werden. Ebenso wenig sind die acht Gruppen acht Grapheme.

Das eingezeichnete Bild ist auf 960×255 skaliert (gegenüber Original 290×77). Zur nur ungefähren Rückprojektion gilt `x=760+x_png*290/960; y=337+y_png*77/255`. Strichstärke, Randschnitt, Unsicherheit und nicht vollständig geschlossene Linien verhindern derzeit echte INV-005-INK-Polygonlisten mit IoU-Werten. B/C-Antworten sind in lokalem SHA-gepinntem Receipt gespeichert; ihre erwarteten Klassen bleiben **versiegelt**.

## Algorithmus und Ergebnis (keine annotatorabhängige Optimierung)

Auf dem Roh-RGB wird zuerst der Originalquellen-Vordergrund extrahiert: Graustufenbild, morphologisches Closing (Ellipse 23×23), Differenz Hintergrund minus Original. Die Negativkontrolle `[720,275,790,315]` legt drei Schwellen über das 99., 99,5. und 99,9. Perzentil fest: **27,33,41**. Das Verfahren zählt danach 8-nachbarige Komponenten von mindestens drei Quellpixeln. Die Anwender-Linienmasken werden erst **danach** getrennt ausgewertet; keine EVA-Zeichen oder menschlichen Zeichenzahlen als Modell-Ziel. Der nächste linke Ausschnitt auf f1r ist `[280,405,740,485]`, ausdrücklich **explorativ** und nicht isoliert von benachbarten Zeilen.

| Quelle und Messobjekt | Schwellwert 27 | 33 | 41 |
|---|---:|---:|---:|
| f1r.1 `[760,337,1050,414]` Komponenten >=3 Pixel | 54 | 56 | 54 |
| f1r.2 links `[280,405,740,485]` Komponenten >=3 Pixel | 89 | 95 | 78 |

Randberührende Kandidaten: f1r.1 **7/6/5**, f1r.2 links **16/9/6** (Reihenfolge der Schwellen). **Keine** dieser Zahlen ist ein Graphem-, Glyphen- oder Buchstabenzähler. Wiederholbarer Code: `research/glyphs/k0001_inv007_owner_annotation_audit.py`; nur abgeleitete Kennzahlen in `research/glyphs/2026-11-16_K0001_INV007_exploratory_metrics.json`.

## Materialer INV-006-Prüfsummenfehler

Die frühere als SHA-256 bezeichnete Negativkontroll-Prüfsumme `271190883ca64508bbd8f7e0d83fdfd8fb3a7e565ff3c7adf43b31f0a9685e` war nur **62** Zeichen lang. Die unveränderten rohen **70×40×3 RGB-Bytes** des durch den Owner gepinnten Originalrasters ergeben **64-stellig**: `271190883ca64508bbd8f7e0d83fdfdfd8fb3a7e565ff3c7adf43b31f0a9685e`. Der positive Kontrollhash `52741a707b175fef5629129d25168fa666d04445087c1dcaac67aec354f485a8` stimmt. Dies korrigiert nur ein fehlerhaft notiertes Hashfeld — **nicht** Originalbild, Kontrollklassifikation oder eine angebliche unabhängige Kontrollbestätigung. D-0227 wahrt die Historie.

## Falsifikations- und Evidenzstatus

**Gegenhypothese / Null:** Zeichen-/Tintenkonturen sind nicht ein-eindeutig mit zusammenhängenden Pixelkomponenten oder geschlossenen Benutzer-Konturflächen identisch; Ligaturen, Damage, Pergamentstruktur, Seiten-/Zeilenüberlappung und variable Zeichengrenzen können jeden Unterschied erzeugen. **Falsifiziert:** verkürzte Annahme `4 maskengeschlossene Konturen = vom Owner beabsichtigte 4 Bereiche`. **Nicht getestet:** vollständiges Schriftinventar, Lesung, Semantik, natürliche Sprache, Chiffre, nichtsprachliche oder Hybrid-Herkunft. **Kontrollen:** Quell- und Kontroll-Crop-Hash geprüft, Klassen von B/C weiter verblindet. **Holdout:** physische f11+ und zweiter Bildzeuge unverändert. **VERIFIED:** Quellhashes, korrigierter SHA, maschinelle Wiederholung des konkreten Algorithmus. **DOCUMENTED:** ausdrücklich acht Owner-Flächen. **INFERRED:** visuelle Annäherung der automatisch erkannten Strukturen. **UNKNOWN:** Schriftzeichen, Graphemidentität, EVA-Angemessenheit. **ACTIVE:** K-0001. **BLOCKED:** unabhängige zweite Person, zweiter rechtegeklärter Bildzeuge und echte Polygon-IoU-Prüfung.

**Fortschritt unverändert:** f1r–f10v 20/20 PDF-Seiten inventarisiert, **0/20** vollständig unabhängig glyphenvalidiert; 28/28 f1r-Textbänder vorläufig lokalisiert, **0/28** glyphenadjudiziert; 213/213 kanonische Snapshot-Canvas-IDs nur inventarisiert (nicht Folio-/Pixelzuordnung verifiziert); **3/40** eng geschlossene Prüfpunkte; **0/5** Entzifferungsgates. Keine Gesamt-Entzifferungswahrscheinlichkeit. Kein manuelles Freigeben der Kontrollcodes, keine Automation geändert, keine Yale-Live-Manifest-Anfrage.

**Nächster Schritt:** Neue unsicherheitsbehaftete Markierungskandidaten an f1r-Zeilen und Marginalien erfassen, ohne Komponenten als Glyphen zu zählen. Zweiten unabhängigen Menschen und zweites Rechte-geprüftes Bild beschaffen, dann echte polygonale Doppelannotation mit vorregistrierten IoU- und Kontrollkriterien.
