# v0.5.1 — multi-convention human review

The local review queue consumes v0.5 glyph predictions and shows every `unknown` candidate with its marked source crop and enlarged excerpt. Reference panels can display EVA, STA1, and up to six additional named, versioned conventions. Each entry can have several real reference images. No correspondence between conventions is assumed. Neither a real EVA/STA1 image catalog nor a rights clearance is included; the owner must supply source-verified, locally permitted reference images. Synthetic test fixtures are not manuscript glyphs.

## Catalog format

Create a private `references.json` next to the reference images. The following is a schema illustration, not a mapping or an authentic glyph:

```json
{"schema":1,"schemes":[{"id":"eva","name":"EVA","version":"<verified edition>","source":"<inventory source>","entries":[{"label":"<documented label>","samples":[{"file":"refs/example.png","sha256":"<actual SHA-256>","source":"<source and locus>"}]}]}]}
```

Add STA1 and other conventions as separate scheme objects. Use a relative image path and the exact SHA-256 of the local file for each example. The catalog is checked for missing files, hash mismatches, duplicate labels and invalid images. A source string is a provenance declaration, not independent proof of authenticity or permission.

## Run locally

```powershell
$P = '.\.venv\Scripts\python.exe'
& $P active_review.py C:\private\dataset\manifest.json C:\private\predictions.json C:\private\references.json C:\private\owner-review.json owner
```

The panels display the label, image exemplars, edition and source. Scroll vertically inside an inventory or horizontally to further inventories. Select a reference image/label, `Nicht im geladenen Inventar`, or `Nicht bestimmbar` separately for each convention. `In keinem geladenen Inventar` marks every loaded convention absent; confirm with `Zuordnungen speichern`. This is an owner's provisional finding for the loaded inventories only, not proof of a novel glyph or absence from every existing transcription. `False Positive` records that the candidate is not a glyph; `Ligatur / Segmentierungsfehler` records a compound or boundary problem; `Unbestimmbar` leaves the entire candidate unresolved. These three outcomes do not assert any convention mapping. Optional notes are saved with the decision.

Each completed decision is saved atomically and reopening skips already decided candidates. The exact crop manifest, prediction file, reference catalog and reviewer bind the session; new data require a new review file. The queue deliberately does not show the model's proposed labels or scores. It does not group similar candidates or automatically propagate an annotation. Only the explicitly unknown predictions enter this queue; use the existing glyph editor for other candidates. Keep the decisions local. No automatic training, remote jobs, model promotion or publication occurs. Before using decisions as training labels, adjudicate them, keep genuinely independent test leaves excluded, and use an explicit conversion to the target convention. EXP-0038g remains NOT_MET; K-0001 remains deferred.
