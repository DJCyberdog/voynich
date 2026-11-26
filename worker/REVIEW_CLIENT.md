# v0.8.0 — Glyph Review Client

A local, focused graphical client for unresolved glyph candidates. Existing processing, training, scientific validation and GitHub bridge remain unchanged. The client does not start jobs, train models, contact GitHub, or upload any data. Existing review files remain compatible with the v0.5.1 schema; optional revision history and proposed correction boxes are additional local metadata.

## Start

Use the existing Python environment with Tk and Pillow. From the worker directory:

```powershell
.\.venv\Scripts\python.exe review_client.py
```

The startup dialog selects the crop manifest, prediction JSON, private reference catalog, review output and reviewer ID. Alternatively supply `--manifest`, `--predictions`, `--references`, `--output`, `--reviewer`. The output must be a private local file; use a single writer. The client checks the output digest before saving to reject stale sessions, but does not provide a multi-process locking protocol.

The dark desktop UI is designed for a 1080p display (default 1320×940; minimum 1160×920). It includes a contextual crop with a highlighted candidate, enlarged glyph, progress, two independently selectable reference panes (EVA and STA1 preferred), label search, 18 references per page, selection highlights, and a source/image-variant dialog. Other loaded conventions can be selected via the dropdowns. Coverage notices explicitly identify incomplete or unreviewed catalogs. No mappings are inferred from visual similarity.

## Review actions

- Choose a reference image/code in each applicable inventory; use **Rest unbestimmbar** to explicitly mark the remaining loaded conventions uncertain. Save with Ctrl+Enter.
- **In keinem Inventar** marks absence from the loaded catalogs only; confirm by saving. This is not a discovery claim.
- F2: false positive; F3: compound/segmentation case; F4: defer for the current session; F5: unresolved. Deferral does not persist across restarts; when all remaining cases are deferred, F4 starts another pass.
- Drag on the context image to propose correction boxes. These are saved with the compound disposition only; the original candidate is immutable. No automatic resegmentation or retraining occurs.
- Previously reviewed candidates can be reopened; replacing a decision preserves the prior decision in the local revision list. Decisions are saved atomically. Do not edit the output externally during a session.

The client groups candidate order with the existing visual similarity heuristic. It never propagates a decision to other members. Scientific review independence, adjudication, dataset selection and model promotion remain external steps.

## Validation

55/55 tests passed in the Linux CPU environment using a virtual display, actual EVA PDF, the three pinned transcriptions and the canonical manuscript probe. Five new tests cover review deferral/resume, revision history, stale-session rejection, correction-box validation, reference search/preferences, and interactive button/drag/save behavior. The actual UI was captured with an explicitly hand-selected f2r demonstration candidate and authentic source-derived reference images. The screenshot is not a model prediction. No manuscript images, reference images, or screenshot are bundled in the code package or committed to GitHub. No Windows/CUDA/live API or scientific recognition acceptance claimed. For the optional v0.8.1 tray companion see [TRAY.md](TRAY.md). Native Windows tray validation remains open. Small-window/high-DPI layout not validated.
