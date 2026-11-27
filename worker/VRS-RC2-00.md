# RC2-00 — exact-base portable source patch transaction

Status: IMPLEMENTED / qualification pending. No owner ZIP, release or scientific approval.

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
