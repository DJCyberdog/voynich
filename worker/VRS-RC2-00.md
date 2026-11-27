# RC2-00 — exact-base portable source patch transaction

Status: IMPLEMENTED / HOSTED TECH_PASS (RC2-00 closed for engineering scope; RC2-10 native owner acceptance remains mandatory). No owner ZIP, release or scientific approval.

## Design

Extend the existing `vrs_source_update.py` transaction, existing portable lock, managed-source allowlist, schema-1 recovery journal and verified rollback. The exact RC1 base is commit `8121427f4612eee3d95de58c685015de84bb3491`, manifest Git blob `34327354cce8d4d72069812593ac49bd3cb35184`. Apply requires both manifest SHA-256 values and independent SHA-256 approval of the complete target source ZIP. Reject other base versions/local source modifications, incorrect archive/target, changed critical launchers or dependencies, unmanaged collisions, running worker or lock contention. The updater itself may change only when the independently verified staged implementation exactly equals the target member. New source bytes are validated in memory; disk space and backups verified before journal and managed writes. Manifest activated last under lock. No global setup or downloads.

The retained RC2 receipt records exact base/target/archive hashes and the existing journal delta. A rollback after successful activation verifies the current target, the pinned original manifest and the exact delta, then reuses the original recovery mechanism. Unfinished update/rollback leaves the same journal that blocks normal exclusive launches; the original RC1 recovery command remains compatible. Refuse external edits or corrupt backup rather than overwriting them. A subsequent update while the target rollback is retained is refused; explicit later finalization policy is a separate RC2-10 qualification decision. If already restored to the base, retry is permitted. Recovery concerns managed source only, not private state schemas; take a private full snapshot before owner acceptance. This is not a general sandbox or guaranteed physical power-loss durability.

## Final RC2 delivery contract (not a release now)

RC2-10 creates one owner-facing patch ZIP. It must contain a complete compatible managed-source archive and an independently SHA-256-verified staged updater, exact base/target source identities and German instructions. Never extract over the installed managed files. Stop worker using Stop.bat and close desktop/tray; verify no unmanaged direct-entry processes. Verify outer package and staged script hashes before executing any supplied code. Stage under a root-local reserved directory, e.g. temp/rc2. Use existing local bootstrap, not a system Python or new runtime.

Illustrative commands (actual hashes and layout supplied only at RC2-10):

```bat
bootstrap\python.exe -I -B temp\rc2\vrs_source_update.py apply-rc2 --root . --source temp\rc2\source.zip --approve ARCHIVE_SHA256 --base BASE_MANIFEST_SHA256 --target TARGET_MANIFEST_SHA256
bootstrap\python.exe -I -B temp\rc2\vrs_source_update.py rollback-rc2 --root .
bootstrap\python.exe -I -B temp\rc2\vrs_source_update.py recover --root .
```

Do not remove the staged recovery script/backup until rollback policy is explicitly resolved. If RC2 requires other launcher/dependency changes, this mechanism refuses them; qualified explicit migration must be added before final delivery, not silently relaxed.

## Tests

Existing source updater tests plus wrong base/target/archive/staged code, space, worker/lock, backup permission, interrupted write/recovery, tamper, exact source rollback and untouched private/runtime markers. `vrs_rc2_patch_acceptance.py` executes actual pinned RC1 files and current candidate bytes in a disposable copy on Windows/Linux hosted Python; it creates only a temporary source fixture, not an owner patch. Real Windows local-bootstrap invocation, full private snapshot/restore, actual installed CUDA environment preservation, filesystem/OS audit, full regression, changed identity migration and final artifact qualification remain RC2-10/owner gates. No claims until test evidence is recorded.

### First hosted execution and remediation

At ba590ec0a4bf3bed97f385eebc4e20ca9e4afd4c, run 45963314522: Ubuntu job 140385983972 SUCCESS, 14/14 tests and exact RC1 source apply/rollback (180 base, 182 target files including manifests, eight private/runtime sentinels, Python 3.13.18). Exact base manifest SHA-256 35f9f58ed3d0b1e3b1850a80270696b90cf0b6dc9e01e21e654c3c1fbb37fdbf. Windows job 140385983555 FAIL, 11/14 passed; three failure-injection tests did not raise their expected OSError (two pre-existing and one new). Actual update/retained rollback, wrong base/target/archive, lock, space and backup checks passed; exact-source Windows test skipped because suite failed. Normalize the test root and match the intended injected write via filesystem identity (samefile parent and exact filename), not textual path spelling. No production safety check weakened. Root-cause attribution remains provisional until Windows rerun. No native owner claim.

### Hosted requalification PASS

Exact tested commit 6c870fbb39325c6217f87a166c48ccbe9e47beef, run [45963485254](https://github.com/DJCyberdog/voynich/actions/runs/45963485254). Both Ubuntu 24.04 (job 140386539100, Python 3.13.18) and Windows 2025 (job 140386539235, Python 3.13.17) passed 14/14 transaction tests, including the three formerly missed fault injections, and the exact immutable RC1 -> tested candidate -> RC1 staged CLI integration. All 180 base and 182 tested target files (including manifests) compared byte-for-byte; eight private/runtime marker files preserved per platform; base manifest SHA-256 35f9f58ed3d0b1e3b1850a80270696b90cf0b6dc9e01e21e654c3c1fbb37fdbf, tested target manifest SHA-256 6225c7f3511f7c2a0a5c75966d64cbade295880ff465721e291194c4b4d523d3. The marker tests do not certify actual installed Python/CUDA state, full workspace migration, unmanaged process control, or power-loss durability. The evidence-only follow-up updates the documentation and source manifest, not the tested code. Final cumulative target identity will differ and must be requalified at RC2-10. No intermediate owner patch ZIP was created or distributed; CI temporary archives are qualification fixtures only. Full baseline/native regression remains separately tracked, and no stable/scientific gate is closed. RC2-01 is next.
