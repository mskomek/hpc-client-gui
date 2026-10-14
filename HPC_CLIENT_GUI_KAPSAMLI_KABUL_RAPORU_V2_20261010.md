# HPC Client GUI Kapsamlı Kabul Raporu V2 — 2026-10-10

## Verdict

`FULL_ACCEPTANCE_BLOCKED_ACTION_COVERAGE_127_UNEXECUTED`

Candidate 7 is **not exhaustively accepted**. The packaged GUI journey proved profile save/persistence, SSH connection, and real terminal PTY commands; Save & Connect passed 3/3 with independent readback. Candidate 7 Save + Submit has a confirmed product defect, fixed in targeted Candidate 8. Most requested feature groups remain uncovered; no push was performed.

## Candidate identity

- Branch lineage: `codex/c6-full-e2e-fix`
- Base/final lineage: `d40f03d0289be158294241b8542e64ba6a0947be`
- Version: `1.5.9`
- EXE SHA-256: `a95a71c3b296d279f548330598e9e1e44f468b32bc0514f056b376deae600266`
- ZIP SHA-256: `9085561a41e1a83a1ee4235ebe68922e9354af785b7b39bcac0f6ff3a6420f80`
- Manifest: `artifacts/candidate7-validation/candidate7-validation-manifest.json`
- Candidate was not rebuilt or modified.

## Windows VM and lab

Windows 11 VM `Windows11`, interactive `test\home`, Explorer session 2. The canonical interactive runner staged and hash-checked the packaged app. The `Candidate7-LOCAL_REAL` adapter on `hpc-lab` is present with guest address `192.168.250.14` for the ongoing acceptance session. Disposable GUI profile/config and its key reference remain in the test-only `%LOCALAPPDATA%\HPCClientGuiCandidate7Acceptance` root; no credential material is included in evidence. No GUI test was parallelized.

`lab/lab-test.ps1` completed against LOCAL_REAL with **23/23 PASS**. The existing topology includes login/controller `192.168.250.11`, compute01 `.12`, compute02 `.13`, OpenSSH/SFTP, MUNGE, Slurm controller/compute/accounting, MariaDB, NFS, and shared storage. Candidate GUI Test Cluster independently reported DNS, TCP, authenticated SSH, SFTP, and scheduler probes (`squeue`, `sbatch`, `scancel`, `sacct`, `scontrol`) PASS. It reported storage `NOT_CONFIGURED` because no provider storage entry was configured in the test profile. Do not interpret backend health as GUI acceptance of those features.

## Golden journey

One primary Add Connection journey was completed: enter the disposable LOCAL_REAL profile and SSH key; view Home/Scratch defaults; Test Cluster; Save; verify persistence after restart; Connect; run `whoami`, `hostname`, `pwd`, and a terminal marker command. The terminal showed `hpctest`, `login-control01`, and `/home/hpctest`; independent SSH readback found `GUI_C7_PTY_OK`. This primary path was not repeated 3 times and did not include explicit Disconnect.

The separate Save & Connect journey passed **3/3 consecutive packaged GUI runs**. Each run saved/reused the disposable profile, connected, showed a real terminal, and produced a marker independently read back over SSH. Evidence: `journey-save-connect-3of3.json`.

## Feature group results

- Connections: Add, Cancel, Save/persistence, selection, Connect, Save & Connect (3/3), and Disconnect observed. Edit, Duplicate, Delete, and context menu variants untested.
- Auth/host key: Valid key SSH passed. A first-use host-key prompt appeared; its fingerprint matched the independently checked LOCAL_REAL known_hosts fingerprint before Trust and save was clicked. Wrong/missing key, password, prompt cancellation, strict unknown-host rejection, mismatch/rotation, and MFA remain untested. No dedicated mismatch/MFA fixtures were inventoried.
- Jump host: not tested; no dedicated test endpoint was inventoried.
- Terminal: real SSH-backed PTY input/output passed for `whoami`, `hostname`, `pwd`, and marker write. Clear, font down/up, and Disconnect passed through GUI with visible state/readback. Find was clicked with a matching terminal string present, but highlighting/read position was not sufficiently clear to mark PASS. Unicode, multiline/long output, resize, reconnect, transport loss/recovery, and stale-session rejection untested.
- Files/SFTP: real remote listing, path entry/Enter, New Folder, New File, and Refresh passed; remote filesystem readback verified created objects. GUI upload completed and remote SHA-256 matched local. GUI download was run after removing the source file; completed queue state and downloaded SHA-256 matched remote. UI calls the tab “FTP”; protocol was SFTP over SSH. Transfer sizes beyond 45B, conflicts, queue lifecycle, checksum toggle, Unicode and parallel transfer remain untested.
- Directories/storage: no GUI navigation or permission/missing-path cases. The GUI self-test reported storage not configured.
- Editor: Candidate 7 Save, Submit (batch), and Save + Submit were run in the packaged GUI. Save persisted the remote script; Submit (batch) created Slurm job 195 and independent accounting confirmed COMPLETED/0:0. Save + Submit launched a detached Terminal running `bash -- <remote path>` and created no Slurm job; this is a confirmed Candidate 7 product defect. Candidate 8 fixes the dispatch and was verified below.
- Slurm: Candidate 7 Submit (batch) created job 195 (COMPLETED). Candidate 8 Save + Submit created job 196 (GUI showed RUNNING; independent `sacct` confirmed COMPLETED/0:0). Candidate 8 GUI Cancel passed on pre-refactor job 197 and final-package jobs 205 and 207; independent `sacct` confirmed `CANCELLED+` for each. Final-package output readback on job 207 showed `GUI_OUTPUT_MARKER_207` and `compute01` in the `Standard Output + Standard Error` stream. Full PENDING/FAILED/accounting detail journeys remain untested.
- Settings, plugins, update checker, logs/diagnostics, Help/About, languages, accelerators, context menus: untested.
- Layout/DPI: Candidate 7’s prior 1366×768 geometry acceptance was referenced; no other requested resolution/scaling cell or comprehensive surface layout was exercised in this run.
- Fault recovery: untested through the GUI.
- Security: no secret values were written to evidence. The app config had password absent in the saved profile readback. Broader redaction and saved-secret contract were not tested.
- Startup/shutdown/native stability: one app exit code 0 was observed. Scoped Windows11 harvest on 2026-10-10: matching Application events 1000/1001/1002 for `hpc-client-gui` = 0; matching `0xC0000005`, `0xC000041D`, `0xC0000409`, and WER APPCRASH = 0; app-local dumps = 0; acceptance-owned GUI processes remaining = 0 (nine harness-owned old processes were stopped). `wxRecursionGuard`, `WindowDestroyEvent`, and WebView `E_ABORT` remain NOT_SCANNED because the guest app-local log directory had no files.

## Action coverage and evidence

The source-based starting inventory had 152 rows. V2 records updated action statuses; recompute counts from `UI_ACTION_COVERAGE_V2.csv`. The catalog remains provisional because runtime enumeration of conditional/dynamic/plugin/context-menu/accelerator surfaces was not completed; 152 is not a frozen exhaustive denominator. N/A rows retain source-contract evidence. No blocked action is represented as a product failure.

Evidence and matrices are under `artifacts/candidate7-full-e2e/`: `UI_ACTION_CATALOG_V2.json`, `UI_ACTION_COVERAGE_V2.csv`, `LAB_CAPABILITY_MATRIX_V2.json`, `AUTH_MATRIX.json`, `TRANSFER_MATRIX.json`, `SLURM_ACCEPTANCE.json`, `UI_LAYOUT_MATRIX_V2.json`, `NATIVE_STABILITY.json`, `SCREENSHOT_INDEX.json`, runner receipts, and journey receipts. The overall gate fails because supported actions and required GUI journeys remain uncovered; this report does not claim exhaustive completion.

## Bugs, hashes, and Git

Candidate 7 Save + Submit defect was fixed on `codex/c7-exhaustive-fix`; final Candidate 8 commit is `9ae04ff7a6c1265818522bc5c1fad43466b14378`. Final-package Save + Submit passed on job 202. Final-package GUI Cancel passed on jobs 205 and 207, and job 207 output was independently verified. Candidate 7 remains immutable. The checkout remains on `develop` with pre-existing user changes; new acceptance evidence is uncommitted. Those changes were preserved. Push status: **not pushed**.




## Candidate 8 targeted repair follow-up

- Candidate 7 identity remained unchanged: EXE SHA-256 `a95a71c3b296d279f548330598e9e1e44f468b32bc0514f056b376deae600266`. The Save + Submit button dispatched the shell-run callback (`bash -- /home/hpctest/gui_c7_ui_acceptance/c7_save_submit_fresh.slurm`) and did not submit a scheduler job. The screenshot and empty independent `squeue`/`sacct` readback are recorded above.
- Candidate 8 branch `codex/c7-exhaustive-fix`, final commit `9ae04ff7a6c1265818522bc5c1fad43466b14378`, routes Save + Submit through save-then-Slurm-submit and extracts editor file, find/replace, document, action, and control responsibilities. Focused wx regression suite: **54 passed**, including `test_w26_supplement_save_submit_uses_sbatch_not_shell`.
- The pre-refactor Candidate 8 build (`27d291…`) was superseded. Final post-refactor Candidate 8 executable SHA-256: `2b3123260134ae68e9255560aa2cc3e17bd7cf4419e8badb41e47677756f2e05`; ZIP SHA-256: `15ed7d11d77f60e6d174ab2ac675abf55585bba3b779c25f64e534ef8b69da26`. ZIP embedded EXE hash matches the manifest. Windows11 interactive runner verified host and guest hashes matched.
- Pre-refactor Candidate 8 GUI Save + Submit created job `196` (`c8submit01`) and GUI Cancel on job `197` (`c8cancel01`) displayed “Cancel accepted for 197”; `sacct` confirmed COMPLETED and CANCELLED respectively. Final post-refactor Candidate 8 GUI Save + Submit created job `202` (`c8refactor`); Jobs showed RUNNING, and independent `sacct` confirmed COMPLETED/0:0, stdout `compute01`, empty stderr. Final-package Cancel passed on jobs 205 and 207; independent `sacct` confirmed `CANCELLED+` for both. Job 207 output was visible in the `Standard Output + Standard Error` stream tab.
- Fresh lab gates at 2026-10-10 12:04 UTC: `lab-status.ps1` PASS; `lab-test.ps1` `LOCAL_REAL_READY`, 23/23 gates passed.
- The Candidate 8 targeted result does not satisfy the full acceptance gate. Candidate 7 V2 snapshot currently records **21 PASS, 1 FAIL, 127 BLOCKED, 3 NOT_APPLICABLE**. The catalog denominator is provisional and most actions are unexecuted. The editor was split into focused modules; `wx_editor_view.py` is 455 lines, every new module is below 500, and the architecture validator passes on the Candidate 8 worktree.
- No push.


## Current candidate decision

`FULL_ACCEPTANCE_BLOCKED_ACTION_COVERAGE_127_UNEXECUTED`: Candidate 7 has a confirmed Save + Submit defect; final Candidate 8 fixes and passes that packaged GUI journey plus targeted Terminal, Outputs, and Cancel journeys. The editor source architecture check passes after extraction. Exhaustive acceptance is still incomplete: the 152-row action catalog remains provisional with 127 actions BLOCKED and runtime surface discovery is incomplete. The earlier runner timeout was a harness target misconfiguration, now corrected. No push.


Final Candidate 8 after architecture extraction: branch `codex/c7-exhaustive-fix`, commit `9ae04ff7a6c1265818522bc5c1fad43466b14378`; focused suite 54/54 PASS including the Save + Submit sbatch regression, architecture validator PASS (6 changed source files, no over-limit files), final packaged GUI Save + Submit PASS on job 202. Candidate 8 final artifact manifest: `artifacts/candidate8-validation/candidate8-validation-manifest.json`.


## Latest serialized GUI follow-up

- Final Candidate 8 package hash was verified in the Windows11 guest runner. A disposable LOCAL_REAL job 203 (`c8output`) was RUNNING on compute01 and appeared in the Jobs page; the GUI row was selected and Cancel was enabled. Independent `squeue`/`sacct` later showed it completed normally before the runner returned.
- Job 203 Outputs aggregate view was blank in the first inspection; the stream-specific tab had not yet been selected. The final-package job 207 run selected `Standard Output + Standard Error` and displayed its marker and hostname, with independent remote-file readback.
- The earlier job 203 Cancel runner was misconfigured: it targeted the Candidate EXE while passing PowerShell switches, so scripted automation did not run. The corrected canonical runner targets staged `powershell.exe` and hash-checks the Candidate EXE as an additional file. Nine test-owned Candidate processes from the mis-targeted launches were stopped; the final scoped inventory found zero remaining. Corrected final-package GUI runs passed Terminal `whoami`, output readback, and GUI Cancel on jobs 205 and 207; independent accounting confirmed `CANCELLED+`. One UIA-only Connection-tab retry did not confirm connection within 60 seconds; this remains a harness/navigation flake, not a product failure. Receipts are in `SLURM_ACCEPTANCE.json`, Candidate 8 manifest, and `candidate8-final-job-actions-receipt.json`.


## Debug follow-up: final Candidate 8 Jobs and Outputs

- Corrected the Windows runner invocation. The interactive runner target is PowerShell; `hpc-client-gui.exe` is independently SHA-256 checked as a staged additional file. Two earlier timeouts came from launching the Candidate executable itself with PowerShell arguments, so those scripts never ran. Nine resulting test-owned GUI processes were stopped; final inventory found zero remaining.
- Final Candidate 8 GUI Cancel passed twice on LOCAL_REAL: job 205 (`c8cancel205`) and job 207 (`c8output207`). GUI confirmation read “Cancel accepted”; exact-job `sacct` returned `CANCELLED+`, and `squeue` had no active row.
- The Outputs overview is blank until an output stream tab is selected. For job 207, `Standard Output + Standard Error` showed `GUI_OUTPUT_MARKER_207` and `compute01`, matching `/home/hpctest/gui_c7_ui_acceptance/output-207.out`. GUI Terminal `whoami` returned `hpctest`; its prompt identified `login-control01`.
- One job 206 run showed a stale SSH message; a later same-package GUI run performed Terminal input, refreshed Jobs successfully, and cancelled the job. A separate UIA-only Connection-tab retry did not confirm connection within 60 seconds. The successful coordinate-selected connection plus terminal/output/cancel journey is recorded; the isolated retry remains a harness/navigation flake pending broader repeat.
- Latest canonical LOCAL_REAL `lab-test.ps1`: `LOCAL_REAL_READY`, 23 required, 0 failed (2026-10-10 12:04 UTC). See `candidate8-final-job-actions-receipt.json` for exact test identities and screenshots.


## Candidate 8 follow-up — language controls

Packaged Candidate 8 was launched in the Windows 11 interactive session after verifying the executable SHA-256. The GUI Language menu successfully switched to Turkish and back to English. UI Automation visible labels changed with each selection, and four screenshots were indexed. See `artifacts/candidate7-full-e2e/candidate8-language-acceptance.json`. This follow-up does not change Candidate 7 coverage or acceptance status; Candidate 8's overall verdict remains blocked by unexecuted coverage.


Candidate 8 supplementary run also passed Help > About: the packaged GUI opened the About dialog and displayed version 1.5.9 with repository, license, third-party notices, and close controls. Evidence: `artifacts/candidate7-full-e2e/candidate8-about-acceptance.json` and indexed screenshots. The controls linking externally were enumerated but not activated.


Candidate 8 supplementary Settings run passed: the GUI opened Settings, showed the remote listing cache, SHA-256 verification, transfer parallelism, SSH timeout, Apply and Close controls. SHA-256 verification was toggled on through the dialog, applied, and read as On after a full app restart; it was then restored to Off. Other settings and bounds remain untested. Evidence: `artifacts/candidate7-full-e2e/candidate8-settings-acceptance.json`.


Candidate 8 Logs follow-up: Logs page rendered; Copy Log Path copied the exact `app.log` path shown by the page. The test-only profile had not created that log file yet, as the GUI disclosed, so only clipboard/path-label agreement was asserted. Other Logs actions remain untested. UIA did not provide InvokePattern for Copy Log Path; a coordinate fallback was used against the captured 1366x768 screenshot. See `artifacts/candidate7-full-e2e/candidate8-logs-acceptance.json`.


Candidate 8 Files/SFTP follow-up partially passed on LOCAL_REAL. The GUI navigated from remote `/` to the disposable `/home/hpctest/gui_c7_ui_acceptance` path, created a unique folder and empty file, refreshed the listing, and kept both entries visible. The canonical lab SSH helper independently confirmed the directory, regular empty file, size 0, and SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`. The earlier `/` mkdir returned the expected permission-denied dialog; there is no product bug finding from that result. The harness mistakenly selected the local Favorites folder, so Favorites remains untested. Evidence: `artifacts/candidate7-full-e2e/candidate8-files-acceptance.json`.


## Candidate 8 supplementary keyboard navigation

Ctrl+1 through Ctrl+7 were sent separately in the hash-verified packaged GUI at 1366x768. UI Automation confirmed selected tabs for six shortcuts; Ctrl+3 showed the Jobs/Outputs page selected in the captured screenshot, though its page tab did not expose a UIA selection pattern. Receipt and screenshots: rtifacts/candidate7-full-e2e/candidate8-accelerator-acceptance.json. This supplementary Candidate 8 evidence does not change Candidate 7 catalog counts. F1 and other accelerator/context-menu actions remain uncovered.

F1 was also sent separately; a distinct top-level Help window appeared. It is recorded as PASS in candidate8-accelerator-acceptance.json with screenshot evidence.

Candidate 8 Files/SFTP follow-up then verified Favorites: GUI selected the existing gui_c7_ui_acceptance favorite from /home/hpctest, returned to /home/hpctest/gui_c7_ui_acceptance, and UIA read back the exact path. The same journey created a unique empty file/folder; strict-known-host LOCAL_REAL SSH independently confirmed them and the empty-file SHA-256. A prior harness variant failed when retyping the parent path; this rerun used the screenshot-verified remote Up button, then completed. See candidate8-files-acceptance.json, candidate8-files-favorite-runner-receipt.json, and the indexed screenshots. This does not cover remaining Files/transfer actions.

Candidate 8 Files navigation follow-up: remote Back returned to /home/hpctest; Forward returned to /home/hpctest/gui_c7_ui_acceptance. The History popup displayed both visited full paths. The harness's basename-only menu check false-failed because labels contain full paths; screenshots provide visible evidence. Back/Forward/History are recorded as PASS in the supplemental Candidate 8 files receipt; remaining transfer and file actions are still uncovered.

Candidate 8 remote Files filter follow-up: the Slurm tab was selected through UI Automation. The remote pane showed Slurm fixture entries such as c8_save_submit_fresh.slurm and did not show the non-Slurm gui_c7_file.txt fixture. A fresh unique folder/empty file again passed refresh and independent strict-known-host SSH size/hash checks. Receipts and screenshot are in candidate8-files-acceptance.json, candidate8-files-navigation-runner-receipt.json, and SCREENSHOT_INDEX.json.

Candidate 8 GUI upload passed on LOCAL_REAL. The GUI accepted the destination directory, the Completed queue showed the upload status Successful, and independent strict-known-host SSH confirmed the 41-byte remote file SHA-256 exactly matched the disposable Windows fixture SHA-256 9912cbe443c468fe45f6374675b21fcfaf7c2ad9be3c400745351819b086d04b. The first incomplete attempt is retained as harness debug evidence and is not counted. See the files acceptance receipt and screenshot index.

Candidate 8 real SFTP download passed. From the remote Slurm filter the GUI selected `c8_save_submit_fresh.slurm`, opened the native “Choose local download folder” picker, and wrote the file into a run-specific local fixture folder. The Completed queue showed upload and download as Successful. The local downloaded SHA-256 `0cb72469582b2b2ccdfad9462887c4702dfe9ebdb5321119bf63fd727b0f0728` matched the independently measured LOCAL_REAL source hash. Evidence: `candidate8-files-download-runner-receipt.json`, `candidate8-files-acceptance.json`, and screenshot index.

Candidate 8 Delete/Undo follow-up remains BLOCKED_HARNESS. The remote directory listing displayed the run-specific test folder, but the harness did not establish that the remote row was selected; the screenshot showed the local row still selected and no confirmation dialog. Delete was not executed, so there was no destructive effect and no product finding. The runner and screenshot evidence are indexed; this action remains uncovered.

### Delete/Undo debug update

The failure was confirmed as harness mis-targeting: the remote row was near/below the right pane viewport, while the pointer landed on a same-y local file row. Strict-host-key SSH confirmed the original unique remote directory still existed. The disposable harness was changed to scroll inside the remote pane, require the exact remote row to be wholly visible, select it through UI Automation `SelectionItemPattern`, and refuse Delete unless `IsSelected` reads true. Candidate 8 EXE SHA-256 remained `2b3123260134ae68e9255560aa2cc3e17bd7cf4419e8badb41e47677756f2e05`; PowerShell parsing passed. A corrected packaged-GUI rerun was launched, but its interactive runner did not return a result during the observation window while transferring the large screenshot-bearing stdout. That run is unverified and is not counted; Delete/Undo remains `BLOCKED_HARNESS`, with no product bug conclusion. No push.
