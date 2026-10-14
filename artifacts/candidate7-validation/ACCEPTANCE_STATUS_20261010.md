# Candidate 7 acceptance status — 2026-10-10

## Candidate identity

- Source base: `d40f03d0289be158294241b8542e64ba6a0947be` with the Candidate 7 geometry fix recorded in the build manifest.
- Packaged EXE SHA-256: `a95a71c3b296d279f548330598e9e1e44f468b32bc0514f056b376deae600266`.

## Verified

- Candidate 7 is launched through the canonical `Invoke-Windows11Interactive.ps1` runner in Windows11 `test\home`, Explorer session 2. The runner verified the staged app SHA-256.
- The packaged app’s Add Connection → Cancel → clean exit journey passed (`ui-interaction.json`). An additional run recorded keyboard focus through the Add Connection dialog, Cancel, and clean app exit (`ui-probe-login.json`; screenshot `screenshots/candidate7-probe-dialog.jpg`).
- Candidate 7 fits 1366×768 / 1366×728 work area in the existing layout evidence. Other resolutions and DPI scales remain unmeasured.
- Ubuntu-Test is Running with 8 vCPUs and 9.4 GiB guest memory. `ubuntu-doctor.ps1 -Username test` passes under strict host-key checking. SSH and SFTP are configured, and port 22 is reachable.
- Ubuntu-Test is not the documented LOCAL_REAL cluster. It has no live Slurm, MUNGE, NFS, accounting database, or compute nodes. Its service inventory is recorded in `ubuntu-live-service-inventory.json`.

## Remaining acceptance gaps

- The latest UIA discovery captured the visible Candidate 7 window but reported zero descendant controls (`ui-catalog-discovery-result-login4.json`). The current probe is not an exhaustive runtime control inventory.
- A later interaction attempt did not reach the Connection page or submit a profile; it remained on Terminal (`ubuntu-test-gui-result4.json`). No app-level SSH/SFTP connection or transfer is claimed.
- Profile save/edit/delete/persistence, connection, terminal, files, transfer queue, settings, plugins, editor, jobs, context menus, keyboard accelerators, language, logs, help, update, shutdown variants, and most conditional actions remain unaccepted.
- The 152-row action coverage snapshot remains 5 PASS, 1 FAIL, 2 NOT_APPLICABLE, and 144 BLOCKED. It is not close to the requested exhaustive 100% coverage.
- Slurm/MUNGE/NFS/accounting/two-node journeys cannot run on Ubuntu-Test. Use repository LOCAL_REAL for those journeys, or mark them blocked until those services are available.

## Cleanup

A disposable Ed25519 key was generated for attempted app authentication. Its exact line was removed from Ubuntu `authorized_keys`, and both guest key files were deleted. The verified host-key pin remains. No private key or credential was added to the repository.

## Next steps

1. Stabilize interaction with the app’s top-level page selection and connection dialog, then run a real SSH/SFTP GUI journey against Ubuntu-Test with a fresh disposable key and remove it after the run.
2. Use the documented LOCAL_REAL cluster for Slurm and shared-storage journeys.
3. Expand the action catalog from static source, runtime control tree, menus/context menus, accelerators, and conditional controls; continue serialized packaged GUI journeys.
4. Run the requested display/layout matrix and complete the final evidence report only after coverage is supported by action-level evidence.
