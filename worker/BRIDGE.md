# Voynich GPU Worker v0.3.0 — GitHub bridge

The existing offline commands remain available. The optional bridge uses only the Python standard library for HTTPS and is restricted to DJCyberdog/voynich. It does not fetch executable code, install dependencies, merge PRs, or write directly to main.

## One-time owner setup (not yet performed)

Follow README.md and PIPELINE.md for the local Python environment and GPU smoke test. Create a fine-grained GitHub token restricted to DJCyberdog/voynich: Contents read, and only for publishing, Contents read/write and Pull requests read/write. Keep the token in the local environment, not in the repository, policy file, logs or chat. Use the repository's branch protection and owner review. The bridge uses HTTPS with normal certificate verification and refuses redirects. No credentials are bundled.

Copy `bridge_policy.example.json` to a private workspace outside Git. Set `actions` to the operations you wish to allow (`prepare`, `propose`, `train`, `predict`). In `allowed_inputs`, add each exact relative workspace path and SHA-256 of its locally approved bytes (including the PDF, group map, annotations, manifests and checkpoints as applicable). Default policy denies all jobs and all publication. For later derived inputs, inspect and approve their new hashes locally. Do not allow unrelated files or share this local policy. The bridge limits explicitly requested epochs to 50, batch size to 64 and pages to 213. Keep the workstation and workspace trusted.

## Research-side contract

Create `worker/jobs/JOB_ID.json` using the existing pipeline schema (`pipeline.py make` locally or equivalent reviewed JSON). It must contain the exact expected input hashes and relative paths; no shell command, credentials, absolute paths or raw manuscript data. Add its ID and exact file SHA-256 to `worker/jobs/approved.json`, for example `{"schema":1,"jobs":[{"id":"job01","sha256":"<64 lowercase hex characters>"}]}`. Merge the job and approval together via an owner-authorized PR. A job ID is immutable; revised jobs require new IDs. The initially empty approval index schedules nothing.

The bridge snapshots the actual main SHA and retrieves the index and job files from that single commit. It verifies their hashes and local policy before execution. Revoked jobs are not started by a subsequent bridge cycle; already running jobs are not remotely cancelled. Failed jobs are not automatically retrained. Use the documented local retry workflow only after review. Keep offline and bridge processing separate; running the offline queue manually can intentionally bypass remote approval.

## Launch

In PowerShell with VOYNICH_GITHUB_TOKEN already securely set in the local environment:

```powershell
$P = '.\.venv\Scripts\python.exe'
& $P bridge.py C:\private\voynich C:\private\bridge-policy.json
& $P bridge.py C:\private\voynich C:\private\bridge-policy.json --watch --interval 60
```

To enable automatic result PRs, additionally set `publish: true` in the local policy and add `--publish` to the chosen command. Both switches are required. The watch command is a foreground process; Ctrl+C stops it. A forcibly killed process may leave `bridge.lock` or `worker.lock`; verify it has stopped before removing stale locks. A failed publication is retried on the next poll without recomputing the completed job. Network/API errors stop that cycle; a watch retries on its configured interval. Nothing runs while the PC is off.

## Return path and evidence boundaries

Only completed training/inference aggregate exports are published. The bridge validates numeric metrics and hash fields, excludes raw images, annotations, region scores, local paths and model weights, and labels the result `UNADJUDICATED`. Preparation/proposal outputs remain local. One result JSON is created on a deterministic `worker-results/` branch, its exact bytes and one-file diff are checked, and a PR is opened against main. Existing identical results and PRs are reused; conflicts fail closed. No PR is automatically merged. Job IDs are public within the repository, so use non-sensitive IDs. The publication uses local receipts to recover after interruptions.

Scientific status is unchanged: EXP-0038g is NOT_MET; no glyph or semantic validation. Real labels, verified physical-leaf groups, genuine holdouts and calibrated/validated classification are separate requirements. No automatic credential provisioning, remote cancellation, live GitHub authentication test, Windows or RTX acceptance has been performed.

## Validation

Linux Python 3.13.5, PyTorch 2.10.0+cpu, PyMuPDF 1.26.7, Pillow 12.3.0: `xvfb-run -a python -m unittest -v test_worker test_pipeline test_gui test_bridge` passed 18/18 (11 existing, 7 new). The bridge tests use a fake GitHub API and real synthetic CPU training. They cover opt-in publishing, approved hash/local policy, reused IDs, revocation, duplicate prevention, retry after simulated PR failure, scope/aggregate rejection, lock and redirect refusal. This is not a live network or manuscript accuracy test.
