# v0.8.1 — local Windows review tray

A deliberately small companion to the v0.8 Glyph Review Client. It monitors explicitly registered local prediction/review batches and can open the next pending batch. It does not start, stop, supervise or schedule the GPU worker, download or execute remote code, train models, contact GitHub, or change Windows startup settings. Closing the tray leaves an already opened Review Client and any independently running worker alone. This is not a new research or model release.

## Setup

The existing virtual environment must have Tk and Pillow. Windows tray support requires optional `pystray` (install explicitly only if wanted; no automatic installation). The launcher assumes `.venv` beside the worker files. On Windows, after installing the existing worker dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install "pystray>=0.19.5,<0.20"
```

Copy `tray_config.example.json` into a private directory as `tray.json`. Add one entry to its `sessions` array per completed prediction batch, using actual local files (the following paths are illustrative):

```json
{
  "id": "batch01",
  "reviewer": "owner",
  "manifest": "dataset/manifest.json",
  "predictions": "predictions.json",
  "references": "catalog/references.json",
  "output": "owner-review.json"
}
```

Paths are relative to the config or absolute; do not use untrusted configs. The manifest, predictions and references must be the same inputs as the v0.8 client, with a distinct output per batch. The config can be edited to register additional completed batches; this release does **not** discover batches automatically. Use an atomic file replacement when updating the config. A changed manifest/prediction/catalog does not silently migrate old decisions. Keep inputs and reference images private and immutable. The monitor validates sources and crop/reference images on first use or when an input JSON changes, caches the validated candidate IDs and inventory, and checks the review binding and decisions on subsequent polls. The full client revalidates images at launch. This cache is not a continuous integrity scan of image bytes.

Inspect the configuration before starting the tray:

```powershell
.\.venv\Scripts\python.exe tray_client.py C:\private\tray.json --once
.\start_review_tray.cmd C:\private\tray.json
```

`--once` works on CPU/Linux too and returns nonzero for blocked sessions. For diagnostic output run `python tray_client.py CONFIG` directly. The launcher uses pythonw (no console) and displays startup exceptions. The tray tooltip reports pending and blocked counts, its default action opens the first eligible batch, and its menu also offers refresh and exit. One child window per tray instance; after the child closes, use the menu again. Existing manual Review Client launches are not tracked; do not open the same output independently. A per-config exclusive lock prevents duplicate tray instances with that config. If a process was killed, verify it has stopped before manually removing the corresponding `.tray.lock`.

Defaults: check once a minute; notify at 10 pending unknowns; at least 15 minutes between automatic notifications. Threshold, poll interval and cooldown are configurable. Alerts fire on threshold crossing, an increased count or new eligible batch subject to cooldown. Counters reflect unknown candidates without a saved decision, not model accuracy or cases awaiting independent adjudication. Deferred cases stay pending. A saved uncertain/compound/false-positive decision counts as reviewed. Invalid inputs are marked blocked, never counted as zero eligible evidence or silently launched. Notifications contain counts only, not source paths or manuscript contents. Windows notification settings may suppress delivery. There is no autostart, automatic label propagation or automatic model retraining.

## Acceptance scope

Linux CPU unit and simulated tray lifecycle tests; native Windows icon, menu/notification display, pythonw launcher, NVIDIA CUDA and real GitHub API remain untested. No PyStray installation in the test environment. No scientific accuracy claim. The original worker and annotation schema remain unchanged.
