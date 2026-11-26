# VRS-095 alpha.1 — local scheduler and proposal-stage integration

Parent E-tier head 1be0f527622d5137815fdb5da2b007bfc747716d. Implementation cca61a5bd29f650893cc1b9e9a64c60aed2d9d58. Status **IN_PROGRESS**, first local integration increment; not a full VRS-095 acceptance.

## Implemented

- Explicit local registration of fixed-scope, hash-bound VRS-092 manifests using existing schema-1 ledger. Backend CPU only for this increment (auto resolves to CPU; explicitly requested CUDA is rejected, not silently downgraded). Worker identity binds relevant source digests and Python/package versions. No remote job intake, training, scientific experiment, or publication.
- Single active scheduler sweep per workspace via OS file lock (Linux tested, Windows implementation not native-tested). One stage per independent ready run per sweep; blocked, paused, cancelled, locked or differently bound runs are not automatically executed. No auto retry loop for invalid integrity evidence. Status/list and explicit pause/resume/cancel/recover commands.
- Actual legacy regions.propose on PDF pages and glyphs.boxes on the verified crops. Technical stage artifacts explicitly say INK_PROPOSALS_ONLY and UNREVIEWED_BOX_PROPOSALS_ONLY. Blank page remains a valid empty proposal set. Overlapping regions/box proposals are not distinct verified manuscript glyphs. Classification, review and alignment adapters are deliberately not enabled. Pinned model/reference/transcription/recognition-policy files are not consumed by these two proposal stages.
- Relative workspace under workspace/vrs095, immutable generation-specific attempt directories; nested page/crop/proposal hashes checked at handoff; existing ledger checkpoints pin completed-stage receipt candidates. Restart can commit a completed checkpoint without repeating computation after explicit confirmation that the previous worker stopped. Incomplete attempts without a committed checkpoint remain isolated and are not reused. Cooperative stop checked at page/region boundaries, not arbitrary kernel instruction or power loss. No automatic cleanup or mid-page resume; no claim of power-loss durability for all underlying crop files.
- Existing VRS-094 CPU resource admission invoked before per-page work, with conservative estimates. This is advisory, not OS-enforced memory or storage caps; stage output and input reads can consume additional resources. Scheduler serializes work in a workspace; independent runs advance between stage boundaries, not in parallel or within a blocked run. Owner must configure independent local run scopes. No actual review-pending lifecycle yet.

## CLI

Use the current development environment from worker/ (not a portable release). ROOT must be an existing local application/workspace root. Manifest path for register is relative to ROOT and all input references are pinned relative to ROOT.

`python vrs_coordinator.py ROOT register config/run.json`
`python vrs_coordinator.py ROOT watch --interval 5`
`python vrs_coordinator.py ROOT once`
`python vrs_coordinator.py ROOT list`
`python vrs_coordinator.py ROOT status RUN_ID`
`python vrs_coordinator.py ROOT pause RUN_ID`
`python vrs_coordinator.py ROOT resume RUN_ID`
`python vrs_coordinator.py ROOT cancel RUN_ID`
`python vrs_coordinator.py ROOT recover RUN_ID GENERATION --confirm-stopped`

Recovery requires explicit confirmation only after verifying old worker exited. OS lock refuses competing coordinator sweep/recovery; ledger generation fences stale owners. No unattended recovery of a potentially live owner. Code/package changes require a new run identity or future explicitly approved migration; no automatic compatibility claim. App-root directory confinement for managed scheduler state; environment/bootstrap, temp/cache redirection and native move/delete audit remain VRS-130. CLI watch is a running foreground headless process, not a Windows service or auto-start registration.

## Executed evidence

Linux, Python 3.13.5, CPU, Torch 2.10.0+cpu installed; legacy original v0.8.1 archive and private fixtures restored locally. New coordinator tests: **8/8 PASS**, 6.463 s, no skips. Actual PDF proposal/segmentation including blank page; blocked independent run doesn't starve later run; cooperative pause after checkpoint and replay; actual subprocess os._exit(77) after durable checkpoint with generation fencing and replay; nested crop tampering; cancellation/unsupported CUDA and arbitrary manifest field rejection; actual competing OS lock and copied/moved root with next-stage continuation; actual headless watch process without GUI. No native Windows/GPU or real-manuscript recognition test claimed.

Original baseline evidence: 57 original tests reported ok with no skips/failures before the combined discover run was interrupted by the tool time limit; the remaining 4 original test_worker tests separately completed PASS in 1.750 s. The eight new tests completed independently. These are 61 baseline and 8 new positive results across runs, **not** a completed combined suite or full integrated current-branch regression. Earlier S–E suite not reconstructed in full here. No successful CI claimed.

SHA-256 logs: new tests ce4ebd85aed2da042fed8291f11ece4481cde8cd2be64ccc068eb3e88f9d557f; interrupted discover 4a5244cd87e6816d7a37d3fb019a8ee7950d34ed2122320e4fce8cd832af292b; worker tests 8c1d7d841e4e80edf54a8687fdff9b98467ecccf8ee0c56d98e7c8f9589eb997. Exact verified tested Git blobs: vrs_coordinator.py fe184429d3ca8b22298bc1325e11382d0f551355; test_vrs_coordinator.py 3071e380b0b9c14451d58d335a3a7ef8c878d049. Existing dependencies reconstructed and hash-checked: vrs_core.py f2ca427212c8ffd9455a2f2ebf649062b1ecd1e7, vrs_contract.py dadfa95822158339e6d67e38a6466f019ead1f32, vrs_ledger.py f21f86e8c728c3bee00a549f5116373fe44d5013, vrs_hardware.py e7f04c73297cf0499b240972f385031f1c75a06a. No private inputs committed.

## Remaining VRS-095

Durable dependency-aware exception lifecycle and true review-pending independent work (not merely generic blocked-run test), locally configured scope scheduling/registration ergonomics, actual recognition adapter integration with VRS-096 frozen policy, stage-specific interruption and resume boundaries, richer diagnostics and end-to-end acceptance. VRS-097 handles authorized correction handoff. All scientific gates remain independent. No automatic reporting, GitHub polling, research experiment, automation change or merge.
