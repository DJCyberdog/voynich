# O-01 — Korrekturspuren und nachträgliche Überarbeitungen im Voynich-Manuskript

**Originator:** Owner, direkt im Projektgespräch am **2026-11-13** (Owner proposed searching for scribal mistakes and medieval correction/erasure practices; explicitly names **O-01 = Owner-01**).  
**Scope:** DJCyberdog/voynich / eigenständige Owner-Forschungsfrage; **nicht** A- oder W-Eintrag und **nicht** ein automatisch neu bewiesener HYP/EXP.  
**Status:** **REGISTERED / WATCHING; SOURCE_REVIEWED; kein neues Bildexperiment**. Hypothese und Manuskriptmechanik bleiben **UNKNOWN**.  
**Base main:** `fc266f263a755aae643e9f183f6a1a1bd4b1bec0`. Owner-kanonischer SHA-256-Snapshot SRC-0007 bleibt D-0005-Arbeitsgrundlage; **nicht eigenständig live von Yale authentifiziert**.

## Eigentümerfrage

Lassen sich am echten MS408 **Korrekturen, Rasuren, überschriebene Zeichen oder Einfügungen** eindeutig von bloßem Nachziehen verblichener Striche, Tintenvariationen, späteren Randzusätzen, Beschädigung oder Scan-Artefakten unterscheiden? Und falls ja: **Welche gerichteten Änderungen von einer ursprünglichen zu einer endgültigen sichtbaren Glyphe lassen sich reproduzierbar feststellen**, ohne vermeintliche Lautwerte oder Bedeutungen anzunehmen?

**Origin:** Owner-Idee, keine Zuschreibung als erstmalige Entdeckung historischer Korrekturen. Frühere Forscher beschrieben bereits Verdachtsstellen; O-01 fügt eine eigene *falsifizierbare, systematisch kontrollierte Arbeitshypothese* hinzu.

## Bereits direkt geprüfte Quellen (keine Manuskriptpixel-Auswertung)

- **SRC-0056:** Jorge Stolfi, *Evidence of text retouching on f1r*, original author essay **2004-07-15**, updated **2004-07-22**, https://www.ic.unicamp.br/~stolfi/voynich/00-EXPORT/04-07-15-retouching/ , direkt gelesen 2026-11-13. Der Autor vermutet für **f1r Zeile 2**, bei EVA `daiin` speziell dem Segment `iin`, eine dunkle Nachzeichnung über schwächeren Strichen; weitere Kandidaten in umgebenden Wörtern. **DOCUMENTED ist die originale Beobachtungsbehauptung des Autors; UNKNOWN bleibt die materialphysikalische Ursache.** Selbst Stolfi nennt natürliche Tintenvariationen als Alternative.
- **SRC-0057:** René Zandbergen, *Text Analysis — the Writing System*, https://www.voynich.nu/writing.html , direkt gelesen 2026-11-13. Abschnitt „Apparent lack of corrections“ führt als Verdachtsstellen **f16r, f20v, f24v, f39r, f42r, f50v, f79r, f80r, f83r, f102v2, f112r** an; der Katalog zeigt f39r zweimal, daher **11 benannte unterschiedliche Folios/Panel-IDs**, keine experimentelle Positivzahl. Auch Zuschreibungen zu Anne Nill 1953 sind als Sekundärwiedergabe der historischen Quelle zu behandeln. Zandbergen unterscheidet zusätzliche spätere Eigentümerinschriften von ursprünglichem Voynich-Lauftext.
- **SRC-0007:** Owner-kanonische IIIF-Presentation-3-Manifestkopie für spätere Canvas-Lokalisierung. Kein routinemäßiger Yale-HTTP-Aufruf. Für die obigen Verdachtslokusse ist hier **keine** neue Canvas-zu-Pixel-Konkordanz überprüft.

**Kritischer Unterschied:** Retouching `alte Form X → erneutes Nachzeichnen derselben Form X` ist **keine** orthografische Fehlerkorrektur `X → Y`. Selbst ein echtes `X → Y` ist ohne Zeitreihen-/Materialschichtnachweis zunächst nur eine begrenzte paläografische Aussage.

## Eine diskriminierende Forschungsprognose

**Testbare starke O-01-Version:** Nach unabhängiger Sichtung der Originalbilder verbleiben **gerichtete Korrekturpaare `X→Y`** mit nachvollziehbarer Strichreihenfolge und schreiber-/formkontrollierter Konsistenz, die aus vorab gefrorenen Schreibregeln auf **anderen, zuvor ungesehenen Folios** besser vorhergesagt werden als nach Basishäufigkeiten, Federfüllung und allgemeinen Beschädigungsmustern zu erwarten. Wenn die einzigen Befunde Nachzeichnungen der gleichen Form sind, bleibt eine strukturelle Schreibkorrektur **unbelegt**.

**Stärkste Gegenhypothese:** Alle vermeintlichen Korrekturen sind variierende Federsättigung, Pergamentstruktur, Abrieb, Pigmentalterung, Scankontrast, spätere Restaurierung oder absichtliches Nachzeichnen identischer Grapheme, nicht produktive Schreibregel-Korrektur.

**Kontrollen und Holdout (DESIGN ONLY):**
1. Originalfolien und relevante Canvas-/Regionskoordinaten einschließlich f1r und der elf katalogisierten Kandidaten gegen SRC-0007 versioniert lokalisieren; Bildrechte separat prüfen, ohne Scans zu veröffentlichen.
2. Vor dem Nachprüfen die Annotation festschreiben: **(A) echte Rasur**, **(B) X→Y Zeichenwechsel**, **(C) X→X Nachzeichnung**, **(D) spätere Fremd-/Randschrift**, **(E) Ink-/Pergament-/Scan-Artefakt**, **(U) unentscheidbar**. Sichtbare Striche, EVA-Labels und Interpretationsannahmen getrennt erfassen.
3. Blindes Doppelrating durch unabhängige bildkundliche Beurteilende, mit abweichenden Lesarten erhalten. **Positivkontrollen:** externe datierte und unabhängig gesicherte Pergamentrasuren/Überarbeitungen. **Negativkontrollen:** ungeänderte Nachbarwörter sowie vergleichbare Pergamentregionen mit bekannten Federdruck-, Übertragungs- und Scankontrastschwankungen.
4. **Null:** Fehlerquote und gerichtete Korrekturhäufigkeit sind nicht höher/stabiler als bei artefakt-/tintengetriebenen Varianten mit gleichem Folio, Hand, Pigment-/Strichdichte-/Bildauflösungsprofil. Vor Testbeginn Zielparameter, Metrik, Mindestübereinstimmung, Fehlerschwellen, Modellkomplexität und echten Folio-Holdout **preregistrieren**. Nie f1r aus dem historischen Entdeckungsfall als neuen prospektiven Blind-Holdout ausgeben.
5. Wenn unabhängige Prüfer nicht stabil zwischen `X→X`, `X→Y` und Störvarianten unterscheiden, ist die **spezifische Korrekturpaare-Prognose** im getesteten Bildumfang falsifiziert oder nicht testbar; nicht die Existenz natürlicher Sprache oder eines Chiffresystems.

## Forschungsgrenzen & Wiedereinstieg

**DOCUMENTED:** Es existieren frühere originale/intermediäre Berichte mit benannten Korrektur-/Nachzeichnungsverdachtsstellen. **CLAIMED:** die ursprünglichen Zuschreibungen zu bestimmten nachgezeichneten Glyphen. **INFERRED:** wirklich identifizierte Korrekturpaare könnten Schreibregeln einschränken. **UNKNOWN:** echte physische Korrekturhäufigkeit, ursprüngliche Zeichen, Zeitabstand, Bedeutung, Autorenschaft. **NOT_RUN:** hier wurde **kein** pixelbasierter Blindtest, keine Materialanalyse, keine eigene Frequenzzählung und keine EVA-Übersetzung durchgeführt. 0/5 Decipherment-Gates unverändert.

**Nächster begrenzter Schritt:** Für **f1r** eine exakte Bild-/Regionreferenz mit geprüften Rechten und kontrolliertem Rastervergleich vorbereiten; anschließend eine echte positive historische Rasurkontrolle beschaffen und vorab das Annotation-/Holdout-Protokoll einfrieren. Die Owner-Priorität der individuellen W-01..W-20-Arbeit bleibt bestehen; O-01 wird separat wiederaufgenommen. Keine Automationen geändert.
