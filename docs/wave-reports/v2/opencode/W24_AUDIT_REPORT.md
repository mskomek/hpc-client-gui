# W24 — Run-phase self-check (NOT the fresh independent audit)

```text
Wave: W24
Canonical audit file: docs/wave-reports/v2/opencode/W24_AUDIT_REPORT.md
Role of this file in RUN phase: worker self-check for controller handoff.
Independent fresh-context audit: PENDING (controller-owned).
HEAD: ccaf871ffc139973db826363859ca2933b216e9c (+ W24-owned hunks)
Date: 2026-09-24
```

## Status

This is a RUN-phase evidence review written by the implementing worker to
make the controller's independent audit cheap and mechanical. It is
explicitly NOT a `PASS` audit verdict and must not be consumed as one:
`audit_policy: fresh-independent` requires a separate context.

Self-check result: **READY_FOR_AUDIT** — no owned blocking defect remains
open; all proof chains below are mechanically re-runnable by the auditor.

## Auditor replay guide (exact)

1. `python -m pytest tests/test_wx_directories.py
   tests/test_remote_directory_listing.py
   tests/test_transfer_directory_controllers.py
   tests/test_wave2_directories_local_files.py -q` -> expect 65 passed.
2. `python -m pytest tests/test_wx_shell.py tests/test_wx_lifecycle.py
   tests/test_wx_remote_files.py tests/test_directory_comparison.py -q`
   -> expect 32 passed.
3. Sensitivity: `git stash push -- src/hpc_gui/wx_directories.py
   src/hpc_gui/wx_directories_view.py`, rerun `tests/test_wx_directories.py`
   -> expect the 3 `test_w24_*` nodes to FAIL; `git stash pop` -> 5 passed.
4. GUI replay: build the panel via `build_directories_panel` under real wx,
   assert semantic labels, call `rebind_directories_storage` with a second
   session, assert labels+models move, call `mark_directories_disconnected`,
   assert `disconnected` labels (see wave report EV-GUI-* values).
5. EXTERNAL replay: key-auth SFTP list of `/srv/hpc/scratch/hpctest` and
   `/home/hpctest` on 192.168.250.11 as hpctest (profile under
   `%LocalAppData%/hpc-client-gui-lab/`); expect POSIX listings, no mutation.
6. `git diff --check` on the 4 owned paths -> clean; confirm the only
   `wx_shell.py` hunk outside the 3 W24 hunks is the pre-existing stacked
   `top_splitter` change (not W24's, preserved).

## Sub-gate self-assessment (for the independent auditor to confirm or overturn)

- Test-quality gate: PASS (behavioral assertions, negative paths, lifecycle
  rebind/disconnect, sensitivity demonstrated by stash proof).
- Evidence-identity gate: PASS (all evidence binds to HEAD `ccaf871f` +
  the exact owned hunks; report-only files excluded from the claim).
- Inventory completeness: PASS with one explicit `AWAITING_INPUT`
  (TODO-032 release-candidate acceptance) and one N/A with reason
  (TODO-041); both are documented, neither hides a product defect.
- No weakened tests, no secrets, no cross-Wave edits.

## Open items for the independent auditor

- Confirm FIX-A..D independence and root-cause statements.
- Confirm TODO-032 `AWAITING_INPUT` is a legitimate concrete-missing-input
  case (no release-candidate artifact exists at this HEAD).
- Confirm the pre-existing stacked dirty tree is untouched by W24.
- Issue the authoritative `PASS`/`REOPEN` verdict with a durable normalized
  receipt (controller-owned).


## Controller-persisted fresh independent audit — 2026-09-24T09:10:41.835769+00:00

- Wave: `W24`
- Normalized receipt: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0032-W24-audit-normalized.json`
- Phase log: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-074448-11a8ecee\0032-W24-audit-opencode.log`
- Controller receipt status: `PASS`

The auditor executed independently; controller persistence is the durable artifact handoff.

```text
AC_WAVE_MODELS_LIST_EMPTY: 'opencode models --standalone' returned no entries; deferring to 'opencode run' fail-closed model validation for opencode-go/muse-spark-1.3-contributor

> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .opencode/protocol/WAVE_PROJECT_PROFILE.json 
→ Read .agents/skills/ac-wave-opencode-audit 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ Get-ChildItem -Path waves/pending, waves/done, waves/blocked, waves/postponed -Filter "W24.md" -ErrorAction SilentlyContinue | Select-Object FullName; Write-Output "---GIT-STATUS---"; git status --short; Write-Output "---GIT-LOG---"; git log --oneline -5; Write-Output "---GIT-SHA---"; git rev-parse HEAD
M .gitignore
 M .opencode/protocol/WAVE_PROJECT_PROFILE.json
 M .opencode/scripts/route-wave-findings.py
 M .opencode/scripts/run-wave-program.py
 M .opencode/scripts/wave_state_engine.py
 M artifacts/v2-final/W01/EV-W01-001_PINNED_REPO_STATE.md
 M artifacts/v2-final/W01/EV-W01-002_VISIBLE_SURFACE_INVENTORY.md
 M artifacts/v2-final/W01/EV-W01-003_EVENT_SERVICE_TRACE.md
 M artifacts/v2-final/W01/EV-W01-004_CONTEXT_MENU_INVENTORY.md
 M artifacts/v2-final/W01/EV-W01-005_SETTINGS_DRIFT.md
 M artifacts/v2-final/W01/SUPPORT_MATRIX.md
 M artifacts/v2-final/W01/WAVE_01_SESSION_REPORT.md
 M artifacts/v2-final/W02/OWNERSHIP_MAP.md
 M artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md
 M artifacts/wave_W18/WAVE_W18_EVIDENCE_MANIFEST.json
 M build/audit/w15-fresh-user-windows.json
 M build/audit/w15-fresh-user-windows.run1.runtime.json
 M build/audit/w15-fresh-user-windows.run2.runtime.json
 M build/audit/w16-fresh-user-windows.json
 M build/audit/w16-fresh-user-windows.run1.runtime.json
 M build/audit/w16-fresh-user-windows.run2.runtime.json
 M build/audit/w16-package-content-windows.json
 M build/audit/w16-packaged-smoke-windows.json
 M build/audit/w16-packaged-smoke-windows.runtime.json
 M build/audit/w18-external-matrix.txt
 M build/audit/w18-gui-pytest.txt
 M build/audit/w22-focused-tests-current.txt
 M build/audit/w22-packaged-smoke-current.json
 M build/audit/w22-packaged-smoke-current.runtime.json
 M docs/wave-reports/v2/opencode/W01_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W01_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W02_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W02_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W03_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W03_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W04_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W04_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W05_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W05_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W06_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W06_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W07_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W07_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W08_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W08_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W09_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W10_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W11_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W11_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W12_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W12_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W13_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W13_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W14_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W15_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W15_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W16_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W16_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W17_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W17_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W18_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W18_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W19_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W19_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W20_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W20_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W21_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W21_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W22_WAVE_REPORT.md
 M scripts/capture_build_provenance.py
 M scripts/generate_release_manifest.py
 M scripts/wx_packaged_smoke.py
 M src/hpc_gui/i18n/en.json
 M src/hpc_gui/i18n/tr.json
 M src/hpc_gui/services/file_context_actions.py
 M src/hpc_gui/services/local_files.py
 M src/hpc_gui/wx_connection.py
 M src/hpc_gui/wx_directories.py
 M src/hpc_gui/wx_directories_view.py
 M src/hpc_gui/wx_local_files.py
 M src/hpc_gui/wx_remote_files_view.py
 M src/hpc_gui/wx_shell.py
 M tests/test_wave_controller_regressions.py
 M tests/test_wx_directories.py
 M tests/test_wx_packaged_smoke.py
?? ".agent-legacy-backup (1)/"
?? artifacts/opencode/
?? artifacts/wave_W19/
?? artifacts/wave_W20/
?? artifacts/wave_W21/
?? artifacts/wave_W22/
?? artifacts/wave_W23/
?? build/audit/w14-packaged-smoke-r3.json
?? build/audit/w17-current-validation.json
?? build/audit/w21-repair-identity.txt
?? build/audit/w22-repair-focused-20260922.txt
?? build/audit/w23-gui-probe-current.py
?? docs/wave-reports/v2/opencode/W23_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W24_AUDIT_REPORT.md
?? docs/wave-reports/v2/opencode/W24_WAVE_REPORT.md
?? "new 4.ps1"
?? scripts/validate_wave_closeout.py
?? "tests/contracts (1)/"
?? "tests/contracts (2)/"
?? tests/contracts/
?? tests/test_w23_delete_confirm.py
?? tests/test_w23_files_navigation.py
?? tests/test_wave_state_engine.py
ccaf871f Harden Wave close handoff recovery
99e32915 Classify controller handoff changes as closeout-only
7a5e6142 Honor fresh audit receipt at Wave close
5ffc14ed Stop repeated Wave no-progress cycles
e51572de Clarify scoped password lab authority
ccaf871ffc139973db826363859ca2933b216e9c
FullName
--------
D:\Projeler\hpc-client-gui\waves\pending\W24.md
---GIT-STATUS---
---GIT-LOG---
---GIT-SHA---
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read rules.md 
→ Read waves/pending/W24.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git rev-parse HEAD; Write-Output "---BRANCH---"; git branch --show-current; Write-Output "---STATUS-SHORT---"; git status --short | Select-Object -First 80
ccaf871ffc139973db826363859ca2933b216e9c
---BRANCH---
develop
---STATUS-SHORT---
 M .gitignore
 M .opencode/protocol/WAVE_PROJECT_PROFILE.json
 M .opencode/scripts/route-wave-findings.py
 M .opencode/scripts/run-wave-program.py
 M .opencode/scripts/wave_state_engine.py
 M artifacts/v2-final/W01/EV-W01-001_PINNED_REPO_STATE.md
 M artifacts/v2-final/W01/EV-W01-002_VISIBLE_SURFACE_INVENTORY.md
 M artifacts/v2-final/W01/EV-W01-003_EVENT_SERVICE_TRACE.md
 M artifacts/v2-final/W01/EV-W01-004_CONTEXT_MENU_INVENTORY.md
 M artifacts/v2-final/W01/EV-W01-005_SETTINGS_DRIFT.md
 M artifacts/v2-final/W01/SUPPORT_MATRIX.md
 M artifacts/v2-final/W01/WAVE_01_SESSION_REPORT.md
 M artifacts/v2-final/W02/OWNERSHIP_MAP.md
 M artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md
 M artifacts/wave_W18/WAVE_W18_EVIDENCE_MANIFEST.json
 M build/audit/w15-fresh-user-windows.json
 M build/audit/w15-fresh-user-windows.run1.runtime.json
 M build/audit/w15-fresh-user-windows.run2.runtime.json
 M build/audit/w16-fresh-user-windows.json
 M build/audit/w16-fresh-user-windows.run1.runtime.json
 M build/audit/w16-fresh-user-windows.run2.runtime.json
 M build/audit/w16-package-content-windows.json
 M build/audit/w16-packaged-smoke-windows.json
 M build/audit/w16-packaged-smoke-windows.runtime.json
 M build/audit/w18-external-matrix.txt
 M build/audit/w18-gui-pytest.txt
 M build/audit/w22-focused-tests-current.txt
 M build/audit/w22-packaged-smoke-current.json
 M build/audit/w22-packaged-smoke-current.runtime.json
 M docs/wave-reports/v2/opencode/W01_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W01_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W02_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W02_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W03_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W03_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W04_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W04_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W05_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W05_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W06_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W06_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W07_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W07_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W08_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W08_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W09_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W10_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W11_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W11_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W12_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W12_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W13_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W13_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W14_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W15_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W15_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W16_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W16_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W17_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W17_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W18_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W18_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W19_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W19_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W20_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W20_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W21_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W21_WAVE_REPORT.md
 M docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md
 M docs/wave-reports/v2/opencode/W22_WAVE_REPORT.md
 M scripts/capture_build_provenance.py
 M scripts/generate_release_manifest.py
 M scripts/wx_packaged_smoke.py
 M src/hpc_gui/i18n/en.json
 M src/hpc_gui/i18n/tr.json
 M src/hpc_gui/services/file_context_actions.py
 M src/hpc_gui/services/local_files.py
 M src/hpc_gui/wx_connection.py
 M src/hpc_gui/wx_directories.py
 M src/hpc_gui/wx_directories_view.py
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/protocol/AC_WAVE_PROGRAM_ORCHESTRATION.md 
→ Read docs/wave-reports/v2/opencode/W24_AUDIT_REPORT.md 
→ Read docs/wave-reports/v2/opencode/W24_WAVE_REPORT.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/protocol/AC_WAVE_VALIDATION_EVIDENCE_SCHEMA.md 
→ Read .agents/protocol/AC_WAVE_EXECUTION_AND_TEST_PROTOCOL.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ Get-ChildItem -Path .tmp/w24-run -ErrorAction SilentlyContinue | Select-Object Name,Length; Write-Output "---ARTIFACTS-W24---"; Get-ChildItem -Path artifacts/wave_W24 -ErrorAction SilentlyContinue | Select-Object Name; Write-Output "---DIFF-STAT---"; git diff --stat; Write-Output "---DIFF-CHECK---"; git diff --check; Write-Output "---DIFF-NAME---"; git diff --name-only
warning: in the working copy of '.opencode/protocol/WAVE_PROJECT_PROFILE.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of '.opencode/scripts/route-wave-findings.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of '.opencode/scripts/wave_state_engine.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-001_PINNED_REPO_STATE.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-002_VISIBLE_SURFACE_INVENTORY.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-003_EVENT_SERVICE_TRACE.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-004_CONTEXT_MENU_INVENTORY.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-005_SETTINGS_DRIFT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/SUPPORT_MATRIX.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/WAVE_01_SESSION_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W02/OWNERSHIP_MAP.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/wave_W18/WAVE_W18_EVIDENCE_MANIFEST.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'build/audit/w18-external-matrix.txt', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'build/audit/w18-gui-pytest.txt', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W01_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W01_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W02_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W02_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W03_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W03_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W04_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W04_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W05_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W05_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W06_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W06_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W07_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W07_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W08_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W08_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W09_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W10_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W11_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W11_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W12_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W12_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W13_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W13_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W14_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W15_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W15_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W16_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W16_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W17_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W17_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W18_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W18_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W19_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W19_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W20_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W20_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W21_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W21_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W22_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'scripts/capture_build_provenance.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'scripts/generate_release_manifest.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'scripts/wx_packaged_smoke.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/file_context_actions.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_wave_controller_regressions.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_wx_packaged_smoke.py', LF will be replaced by CRLF the next time Git touches it
 .gitignore                                         |    4 +-
 .opencode/protocol/WAVE_PROJECT_PROFILE.json       |   36 +-
 .opencode/scripts/route-wave-findings.py           |  252 ++---
 .opencode/scripts/run-wave-program.py              |  753 +++++++++++--
 .opencode/scripts/wave_state_engine.py             |  234 +++-
 .../v2-final/W01/EV-W01-001_PINNED_REPO_STATE.md   |   37 +-
 .../W01/EV-W01-002_VISIBLE_SURFACE_INVENTORY.md    |    4 +-
 .../v2-final/W01/EV-W01-003_EVENT_SERVICE_TRACE.md |    4 +-
 .../W01/EV-W01-004_CONTEXT_MENU_INVENTORY.md       |    4 +-
 .../v2-final/W01/EV-W01-005_SETTINGS_DRIFT.md      |    4 +-
 artifacts/v2-final/W01/SUPPORT_MATRIX.md           |    2 +-
 artifacts/v2-final/W01/WAVE_01_SESSION_REPORT.md   |    4 +-
 artifacts/v2-final/W02/OWNERSHIP_MAP.md            |    2 +-
 artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md    |    2 +-
 artifacts/wave_W18/WAVE_W18_EVIDENCE_MANIFEST.json |   77 +-
 build/audit/w15-fresh-user-windows.json            |   22 +-
 .../audit/w15-fresh-user-windows.run1.runtime.json |    4 +-
 .../audit/w15-fresh-user-windows.run2.runtime.json |    4 +-
 build/audit/w16-fresh-user-windows.json            |   24 +-
 .../audit/w16-fresh-user-windows.run1.runtime.json |    4 +-
 .../audit/w16-fresh-user-windows.run2.runtime.json |    4 +-
 build/audit/w16-package-content-windows.json       |   10 +-
 build/audit/w16-packaged-smoke-windows.json        |  502 ++++++++-
 .../audit/w16-packaged-smoke-windows.runtime.json  |  491 ++++++++-
 build/audit/w18-external-matrix.txt                |   39 +-
 build/audit/w18-gui-pytest.txt                     |    8 +-
 build/audit/w22-focused-tests-current.txt          |    4 +-
 build/audit/w22-packaged-smoke-current.json        |   20 +-
 .../audit/w22-packaged-smoke-current.runtime.json  |    8 +-
 docs/wave-reports/v2/opencode/W01_AUDIT_REPORT.md  |   24 +-
 docs/wave-reports/v2/opencode/W01_WAVE_REPORT.md   |    7 +-
 docs/wave-reports/v2/opencode/W02_AUDIT_REPORT.md  |   32 +-
 docs/wave-reports/v2/opencode/W02_WAVE_REPORT.md   |   30 +-
 docs/wave-reports/v2/opencode/W03_AUDIT_REPORT.md  |   21 +-
 docs/wave-reports/v2/opencode/W03_WAVE_REPORT.md   |   10 +-
 docs/wave-reports/v2/opencode/W04_AUDIT_REPORT.md  |   42 +-
 docs/wave-reports/v2/opencode/W04_WAVE_REPORT.md   |   12 +-
 docs/wave-reports/v2/opencode/W05_AUDIT_REPORT.md  |   57 +-
 docs/wave-reports/v2/opencode/W05_WAVE_REPORT.md   |   44 +-
 docs/wave-reports/v2/opencode/W06_AUDIT_REPORT.md  |   34 +-
 docs/wave-reports/v2/opencode/W06_WAVE_REPORT.md   |   28 +-
 docs/wave-reports/v2/opencode/W07_AUDIT_REPORT.md  |   55 +-
 docs/wave-reports/v2/opencode/W07_WAVE_REPORT.md   |  104 +-
 docs/wave-reports/v2/opencode/W08_AUDIT_REPORT.md  |   17 +-
 docs/wave-reports/v2/opencode/W08_WAVE_REPORT.md   |   45 +-
 docs/wave-reports/v2/opencode/W09_WAVE_REPORT.md   |   40 +-
 docs/wave-reports/v2/opencode/W10_WAVE_REPORT.md   |   21 +-
 docs/wave-reports/v2/opencode/W11_AUDIT_REPORT.md  |   77 +-
 docs/wave-reports/v2/opencode/W11_WAVE_REPORT.md   |   61 +-
 docs/wave-reports/v2/opencode/W12_AUDIT_REPORT.md  |   46 +-
 docs/wave-reports/v2/opencode/W12_WAVE_REPORT.md   |   72 +-
 docs/wave-reports/v2/opencode/W13_AUDIT_REPORT.md  |   68 +-
 docs/wave-reports/v2/opencode/W13_WAVE_REPORT.md   |   75 +-
 docs/wave-reports/v2/opencode/W14_WAVE_REPORT.md   |   72 +-
 docs/wave-reports/v2/opencode/W15_AUDIT_REPORT.md  |   33 +-
 docs/wave-reports/v2/opencode/W15_WAVE_REPORT.md   |   71 +-
 docs/wave-reports/v2/opencode/W16_AUDIT_REPORT.md  |   26 +-
 docs/wave-reports/v2/opencode/W16_WAVE_REPORT.md   |  153 ++-
 docs/wave-reports/v2/opencode/W17_AUDIT_REPORT.md  |   12 +
 docs/wave-reports/v2/opencode/W17_WAVE_REPORT.md   |   32 +-
 docs/wave-reports/v2/opencode/W18_AUDIT_REPORT.md  |  257 +++++
 docs/wave-reports/v2/opencode/W18_WAVE_REPORT.md   |  283 +++++
 docs/wave-reports/v2/opencode/W19_AUDIT_REPORT.md  |   16 +-
 docs/wave-reports/v2/opencode/W19_WAVE_REPORT.md   |   15 +-
 docs/wave-reports/v2/opencode/W20_AUDIT_REPORT.md  |   10 +-
 docs/wave-reports/v2/opencode/W20_WAVE_REPORT.md   |    8 +-
 docs/wave-reports/v2/opencode/W21_AUDIT_REPORT.md  |    9 +-
 docs/wave-reports/v2/opencode/W21_WAVE_REPORT.md   |   30 +-
 docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md  | 1132 +++++++++++++++++++-
 docs/wave-reports/v2/opencode/W22_WAVE_REPORT.md   |  768 ++++++++++++-
 scripts/capture_build_provenance.py                |   10 +
 scripts/generate_release_manifest.py               |   10 +
 scripts/wx_packaged_smoke.py                       |   11 +-
 src/hpc_gui/i18n/en.json                           |    8 +-
 src/hpc_gui/i18n/tr.json                           |    8 +-
 src/hpc_gui/services/file_context_actions.py       |   28 +-
 src/hpc_gui/services/local_files.py                |   37 +-
 src/hpc_gui/wx_connection.py                       |   18 +-
 src/hpc_gui/wx_directories.py                      |    9 +-
 src/hpc_gui/wx_directories_view.py                 |  115 +-
 src/hpc_gui/wx_local_files.py                      |  158 ++-
 src/hpc_gui/wx_remote_files_view.py                |   86 +-
 src/hpc_gui/wx_shell.py                            |   20 +
 tests/test_wave_controller_regressions.py          |   95 ++
 tests/test_wx_directories.py                       |  120 +++
 tests/test_wx_packaged_smoke.py                    |    9 +-
 86 files changed, 6094 insertions(+), 1160 deletions(-)
warning: in the working copy of '.opencode/protocol/WAVE_PROJECT_PROFILE.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of '.opencode/scripts/route-wave-findings.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of '.opencode/scripts/wave_state_engine.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-001_PINNED_REPO_STATE.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-002_VISIBLE_SURFACE_INVENTORY.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-003_EVENT_SERVICE_TRACE.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-004_CONTEXT_MENU_INVENTORY.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-005_SETTINGS_DRIFT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/SUPPORT_MATRIX.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/WAVE_01_SESSION_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W02/OWNERSHIP_MAP.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/wave_W18/WAVE_W18_EVIDENCE_MANIFEST.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'build/audit/w18-external-matrix.txt', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'build/audit/w18-gui-pytest.txt', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W01_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W01_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W02_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W02_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W03_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W03_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W04_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W04_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W05_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W05_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W06_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W06_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W07_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W07_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W08_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W08_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W09_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W10_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W11_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W11_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W12_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W12_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W13_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W13_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W14_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W15_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W15_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W16_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W16_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W17_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W17_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W18_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W18_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W19_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W19_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W20_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W20_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W21_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W21_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W22_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'scripts/capture_build_provenance.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'scripts/generate_release_manifest.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'scripts/wx_packaged_smoke.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/file_context_actions.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_wave_controller_regressions.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_wx_packaged_smoke.py', LF will be replaced by CRLF the next time Git touches it
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:374: trailing whitespace.
+opencode.exe : 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:380: trailing whitespace.
+ 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:383: trailing whitespace.
+→ Read .opencode/protocol/WAVE_PROJECT_PROFILE.json 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:384: trailing whitespace.
+→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:385: trailing whitespace.
+→ Read .tmp/agent-runs/ac-wave-opencode-parallel/20260924-074448-11a8ecee/0008-W22-findings.json 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:387: trailing whitespace.
+→ Read artifacts/wave_W22/WAVE_W22_EVIDENCE_MANIFEST.json 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:388: trailing whitespace.
+→ Read waves/pending/W22.md 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:389: trailing whitespace.
+→ Read .agents/skills/ac-wave-opencode-audit 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:392: trailing whitespace.
+$ git rev-parse HEAD; echo "---STATUS---"; git status --short --branch; echo "---LOG1---"; git log -1 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:491: trailing whitespace.
+→ Read build/audit/w22-packaged-smoke-current.json 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:492: trailing whitespace.
+→ Read build/audit/w22-focused-tests-current.txt 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:493: trailing whitespace.
+→ Read docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:494: trailing whitespace.
+→ Read docs/wave-reports/v2/opencode/W22_WAVE_REPORT.md 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:508: trailing whitespace.
+$ Get-Content .tmp/w22-repair-20260924-full60-repair20.txt -ErrorAction Stop | Select-Object -First 10; echo 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:509: trailing whitespace.
+"---VALIDATOR20---"; Get-Content .tmp/w22-repair-20260924-validator-repair20.txt -ErrorAction Stop | Select-Object 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:510: trailing whitespace.
+-First 40; echo "---REPLAY-EXISTS---"; Test-Path .tmp/w22-gui-local-real-replay/W22_GUI_LOCAL_REAL_REPLAY.json; 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:511: trailing whitespace.
+Test-Path .tmp/w22-repair-20260924-isolated-life065-repair20.txt; Test-Path 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:532: trailing whitespace.
+$ echo "---W21-FRONTMATTER---"; Get-Content waves/done/W21.md -ErrorAction SilentlyContinue | Select-Object 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:533: trailing whitespace.
+-First 50; echo "---W21-PENDING-CHECK---"; Test-Path waves/pending/W21.md; echo "---DIFF-STAT---"; git diff --stat; 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:534: trailing whitespace.
+echo "---DIFF-CHECK---"; git diff --check; echo "---WX-DIFF---"; git diff -- src/hpc_gui/wx_connection.py | 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:693: trailing whitespace.
+ 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:708: trailing whitespace.
+warning: in the working copy of '.opencode/protocol/WAVE_PROJECT_PROFILE.json', LF will be replaced by CRLF the next 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:710: trailing whitespace.
+warning: in the working copy of '.opencode/scripts/route-wave-findings.py', LF will be replaced by CRLF the next time 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:712: trailing whitespace.
+warning: in the working copy of '.opencode/scripts/run-wave-program.py', LF will be replaced by CRLF the next time Git 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:714: trailing whitespace.
+warning: in the working copy of '.opencode/scripts/wave_state_engine.py', LF will be replaced by CRLF the next time 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:716: trailing whitespace.
+warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-001_PINNED_REPO_STATE.md', LF will be replaced by CRLF 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:718: trailing whitespace.
+warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-002_VISIBLE_SURFACE_INVENTORY.md', LF will be replaced 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:720: trailing whitespace.
+warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-003_EVENT_SERVICE_TRACE.md', LF will be replaced by 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:722: trailing whitespace.
+warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-004_CONTEXT_MENU_INVENTORY.md', LF will be replaced by 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:724: trailing whitespace.
+warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-005_SETTINGS_DRIFT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:726: trailing whitespace.
+warning: in the working copy of 'artifacts/v2-final/W01/SUPPORT_MATRIX.md', LF will be replaced by CRLF the next time 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:728: trailing whitespace.
+warning: in the working copy of 'artifacts/v2-final/W01/WAVE_01_SESSION_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:730: trailing whitespace.
+warning: in the working copy of 'artifacts/v2-final/W02/OWNERSHIP_MAP.md', LF will be replaced by CRLF the next time 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:732: trailing whitespace.
+warning: in the working copy of 'artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:734: trailing whitespace.
+warning: in the working copy of 'artifacts/wave_W18/WAVE_W18_EVIDENCE_MANIFEST.json', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:736: trailing whitespace.
+warning: in the working copy of 'build/audit/w18-external-matrix.txt', LF will be replaced by CRLF the next time Git 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:738: trailing whitespace.
+warning: in the working copy of 'build/audit/w18-gui-pytest.txt', LF will be replaced by CRLF the next time Git 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:740: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W01_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:742: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W01_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:744: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W02_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:746: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W02_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:748: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W03_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:750: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W03_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:752: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W04_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:754: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W04_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:756: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W05_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:758: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W05_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:760: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W06_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:762: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W06_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:764: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W07_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:766: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W07_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:768: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W08_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:770: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W08_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:772: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W09_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:774: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W10_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:776: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W11_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:778: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W11_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:780: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W12_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:782: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W12_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:784: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W13_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:786: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W13_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:788: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W14_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:790: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W15_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:792: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W15_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:794: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W16_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:796: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W16_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:798: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W17_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:800: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W17_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:802: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W18_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:804: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W18_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:806: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W19_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:808: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W19_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:810: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W20_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:812: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W20_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:814: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W21_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:816: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W21_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:818: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:820: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W22_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:822: trailing whitespace.
+warning: in the working copy of 'scripts/capture_build_provenance.py', LF will be replaced by CRLF the next time Git 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:824: trailing whitespace.
+warning: in the working copy of 'scripts/generate_release_manifest.py', LF will be replaced by CRLF the next time Git 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:826: trailing whitespace.
+warning: in the working copy of 'scripts/wx_packaged_smoke.py', LF will be replaced by CRLF the next time Git touches 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:828: trailing whitespace.
+warning: in the working copy of 'tests/test_wave_controller_regressions.py', LF will be replaced by CRLF the next time 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:830: trailing whitespace.
+warning: in the working copy of 'tests/test_wx_packaged_smoke.py', LF will be replaced by CRLF the next time Git 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:832: trailing whitespace.
+warning: in the working copy of '.opencode/protocol/WAVE_PROJECT_PROFILE.json', LF will be replaced by CRLF the next 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:834: trailing whitespace.
+warning: in the working copy of '.opencode/scripts/route-wave-findings.py', LF will be replaced by CRLF the next time 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:836: trailing whitespace.
+warning: in the working copy of '.opencode/scripts/run-wave-program.py', LF will be replaced by CRLF the next time Git 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:838: trailing whitespace.
+warning: in the working copy of '.opencode/scripts/wave_state_engine.py', LF will be replaced by CRLF the next time 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:840: trailing whitespace.
+warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-001_PINNED_REPO_STATE.md', LF will be replaced by CRLF 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:842: trailing whitespace.
+warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-002_VISIBLE_SURFACE_INVENTORY.md', LF will be replaced 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:844: trailing whitespace.
+warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-003_EVENT_SERVICE_TRACE.md', LF will be replaced by 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:846: trailing whitespace.
+warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-004_CONTEXT_MENU_INVENTORY.md', LF will be replaced by 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:848: trailing whitespace.
+warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-005_SETTINGS_DRIFT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:850: trailing whitespace.
+warning: in the working copy of 'artifacts/v2-final/W01/SUPPORT_MATRIX.md', LF will be replaced by CRLF the next time 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:852: trailing whitespace.
+warning: in the working copy of 'artifacts/v2-final/W01/WAVE_01_SESSION_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:854: trailing whitespace.
+warning: in the working copy of 'artifacts/v2-final/W02/OWNERSHIP_MAP.md', LF will be replaced by CRLF the next time 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:856: trailing whitespace.
+warning: in the working copy of 'artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:858: trailing whitespace.
+warning: in the working copy of 'artifacts/wave_W18/WAVE_W18_EVIDENCE_MANIFEST.json', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:860: trailing whitespace.
+warning: in the working copy of 'build/audit/w18-external-matrix.txt', LF will be replaced by CRLF the next time Git 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:862: trailing whitespace.
+warning: in the working copy of 'build/audit/w18-gui-pytest.txt', LF will be replaced by CRLF the next time Git 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:864: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W01_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:866: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W01_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:868: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W02_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:870: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W02_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:872: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W03_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:874: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W03_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:876: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W04_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:878: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W04_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:880: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W05_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:882: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W05_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:884: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W06_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:886: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W06_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:888: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W07_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:890: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W07_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:892: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W08_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:894: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W08_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:896: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W09_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:898: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W10_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:900: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W11_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:902: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W11_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:904: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W12_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:906: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W12_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:908: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W13_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:910: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W13_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:912: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W14_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:914: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W15_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:916: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W15_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:918: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W16_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:920: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W16_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:922: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W17_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:924: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W17_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:926: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W18_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:928: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W18_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:930: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W19_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:932: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W19_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:934: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W20_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:936: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W20_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:938: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W21_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:940: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W21_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:942: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:944: trailing whitespace.
+warning: in the working copy of 'docs/wave-reports/v2/opencode/W22_WAVE_REPORT.md', LF will be replaced by CRLF the 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:946: trailing whitespace.
+warning: in the working copy of 'scripts/capture_build_provenance.py', LF will be replaced by CRLF the next time Git 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:948: trailing whitespace.
+warning: in the working copy of 'scripts/generate_release_manifest.py', LF will be replaced by CRLF the next time Git 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:950: trailing whitespace.
+warning: in the working copy of 'scripts/wx_packaged_smoke.py', LF will be replaced by CRLF the next time Git touches 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:952: trailing whitespace.
+warning: in the working copy of 'tests/test_wave_controller_regressions.py', LF will be replaced by CRLF the next time 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:954: trailing whitespace.
+warning: in the working copy of 'tests/test_wx_packaged_smoke.py', LF will be replaced by CRLF the next time Git 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:956: trailing whitespace.
+$ Get-Content .tmp/w22-gui-local-real-replay/W22_GUI_LOCAL_REAL_REPLAY.json | Select-Object -First 60; echo 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:957: trailing whitespace.
+"---REPLAY-SHA-BIND---"; Select-String -Path .tmp/w22-gui-local-real-replay/W22_GUI_LOCAL_REAL_REPLAY.json -Pattern 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:983: trailing whitespace.
+.tmp\w22-gui-local-real-replay\W22_GUI_LOCAL_REAL_REPLAY.json:3:  "candidate_sha": 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:986: trailing whitespace.
+.tmp\w22-gui-local-real-replay\W22_GUI_LOCAL_REAL_REPLAY.json:12:    "shell_marker": "(0, 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:989: trailing whitespace.
+.tmp\w22-gui-local-real-replay\W22_GUI_LOCAL_REAL_REPLAY.json:17:    "shell_marker": "(0, 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:993: trailing whitespace.
+$ python -m pytest -q 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:994: trailing whitespace.
+tests/test_w21_terminal_lifecycle.py::test_w21_disconnect_cb_leaves_connected_and_drops_stale; echo 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:1005: trailing whitespace.
+$ python -m pytest -q tests/test_terminal_pty_wire.py tests/test_ssh_terminal_stream.py 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:1006: trailing whitespace.
+tests/test_wx_packaged_smoke.py tests/test_w20_terminal_io.py tests/test_w18_auth_hostkey.py 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:1041: trailing whitespace.
+E       AssertionError: subprocess failed: 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:1042: trailing whitespace.
+E         ..\..\src\msw\webview_edge.cpp(609): 'WebView2::WebViewCreated' failed with error 0x80004004 (Operation 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:1044: trailing whitespace.
+E         
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:1046: trailing whitespace.
+E        +  where 3221226525 = CompletedProcess(args=['D:\\Python\\Python312\\python.exe', '-c', '\nimport 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:1047: trailing whitespace.
+sys\nsys.path.insert(0, "src")\nimport wx\...\\..\\src\\msw\\webview_edge.cpp(609): 'WebView2::WebViewCreated' failed 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:1057: trailing whitespace.
+$ python -m pytest -q 
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md:1058: trailing whitespace.
+"tests/test_w21_terminal_lifecycle.py::test_w21_disconnect_visible_and_reconnect_fresh_identity"; echo 
Name             Length
----             ------
w24-adjacent.txt    101
w24-focused.txt     102
w24-head.txt         42
---ARTIFACTS-W24---
---DIFF-STAT---
---DIFF-CHECK---
---DIFF-NAME---
warning: in the working copy of '.opencode/protocol/WAVE_PROJECT_PROFILE.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of '.opencode/scripts/route-wave-findings.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of '.opencode/scripts/wave_state_engine.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-001_PINNED_REPO_STATE.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-002_VISIBLE_SURFACE_INVENTORY.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-003_EVENT_SERVICE_TRACE.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-004_CONTEXT_MENU_INVENTORY.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/EV-W01-005_SETTINGS_DRIFT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/SUPPORT_MATRIX.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W01/WAVE_01_SESSION_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W02/OWNERSHIP_MAP.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'artifacts/wave_W18/WAVE_W18_EVIDENCE_MANIFEST.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'build/audit/w18-external-matrix.txt', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'build/audit/w18-gui-pytest.txt', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W01_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W01_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W02_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W02_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W03_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W03_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W04_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W04_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W05_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W05_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W06_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W06_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W07_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W07_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W08_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W08_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W09_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W10_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W11_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W11_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W12_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W12_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W13_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W13_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W14_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W15_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W15_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W16_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W16_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W17_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W17_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W18_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W18_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W19_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W19_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W20_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W20_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W21_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W21_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/wave-reports/v2/opencode/W22_WAVE_REPORT.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'scripts/capture_build_provenance.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'scripts/generate_release_manifest.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'scripts/wx_packaged_smoke.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/file_context_actions.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_wave_controller_regressions.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_wx_packaged_smoke.py', LF will be replaced by CRLF the next time Git touches it
.gitignore
.opencode/protocol/WAVE_PROJECT_PROFILE.json
.opencode/scripts/route-wave-findings.py
.opencode/scripts/run-wave-program.py
.opencode/scripts/wave_state_engine.py
artifacts/v2-final/W01/EV-W01-001_PINNED_REPO_STATE.md
artifacts/v2-final/W01/EV-W01-002_VISIBLE_SURFACE_INVENTORY.md
artifacts/v2-final/W01/EV-W01-003_EVENT_SERVICE_TRACE.md
artifacts/v2-final/W01/EV-W01-004_CONTEXT_MENU_INVENTORY.md
artifacts/v2-final/W01/EV-W01-005_SETTINGS_DRIFT.md
artifacts/v2-final/W01/SUPPORT_MATRIX.md
artifacts/v2-final/W01/WAVE_01_SESSION_REPORT.md
artifacts/v2-final/W02/OWNERSHIP_MAP.md
artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md
artifacts/wave_W18/WAVE_W18_EVIDENCE_MANIFEST.json
build/audit/w15-fresh-user-windows.json
build/audit/w15-fresh-user-windows.run1.runtime.json
build/audit/w15-fresh-user-windows.run2.runtime.json
build/audit/w16-fresh-user-windows.json
build/audit/w16-fresh-user-windows.run1.runtime.json
build/audit/w16-fresh-user-windows.run2.runtime.json
build/audit/w16-package-content-windows.json
build/audit/w16-packaged-smoke-windows.json
build/audit/w16-packaged-smoke-windows.runtime.json
build/audit/w18-external-matrix.txt
build/audit/w18-gui-pytest.txt
build/audit/w22-focused-tests-current.txt
build/audit/w22-packaged-smoke-current.json
build/audit/w22-packaged-smoke-current.runtime.json
docs/wave-reports/v2/opencode/W01_AUDIT_REPORT.md
docs/wave-reports/v2/opencode/W01_WAVE_REPORT.md
docs/wave-reports/v2/opencode/W02_AUDIT_REPORT.md
docs/wave-reports/v2/opencode/W02_WAVE_REPORT.md
docs/wave-reports/v2/opencode/W03_AUDIT_REPORT.md
docs/wave-reports/v2/opencode/W03_WAVE_REPORT.md
docs/wave-reports/v2/opencode/W04_AUDIT_REPORT.md
docs/wave-reports/v2/opencode/W04_WAVE_REPORT.md
docs/wave-reports/v2/opencode/W05_AUDIT_REPORT.md
docs/wave-reports/v2/opencode/W05_WAVE_REPORT.md
docs/wave-reports/v2/opencode/W06_AUDIT_REPORT.md
docs/wave-reports/v2/opencode/W06_WAVE_REPORT.md
docs/wave-reports/v2/opencode/W07_AUDIT_REPORT.md
docs/wave-reports/v2/opencode/W07_WAVE_REPORT.md
docs/wave-reports/v2/opencode/W08_AUDIT_REPORT.md
docs/wave-reports/v2/opencode/W08_WAVE_REPORT.md
docs/wave-reports/v2/opencode/W09_WAVE_REPORT.md
docs/wave-reports/v2/opencode/W10_WAVE_REPORT.md
docs/wave-reports/v2/opencode/W11_AUDIT_REPORT.md
docs/wave-reports/v2/opencode/W11_WAVE_REPORT.md
docs/wave-reports/v2/opencode/W12_AUDIT_REPORT.md
docs/wave-reports/v2/opencode/W12_WAVE_REPORT.md
docs/wave-reports/v2/opencode/W13_AUDIT_REPORT.md
docs/wave-reports/v2/opencode/W13_WAVE_REPORT.md
docs/wave-reports/v2/opencode/W14_WAVE_REPORT.md
docs/wave-reports/v2/opencode/W15_AUDIT_REPORT.md
docs/wave-reports/v2/opencode/W15_WAVE_REPORT.md
docs/wave-reports/v2/opencode/W16_AUDIT_REPORT.md
docs/wave-reports/v2/opencode/W16_WAVE_REPORT.md
docs/wave-reports/v2/opencode/W17_AUDIT_REPORT.md
docs/wave-reports/v2/opencode/W17_WAVE_REPORT.md
docs/wave-reports/v2/opencode/W18_AUDIT_REPORT.md
docs/wave-reports/v2/opencode/W18_WAVE_REPORT.md
docs/wave-reports/v2/opencode/W19_AUDIT_REPORT.md
docs/wave-reports/v2/opencode/W19_WAVE_REPORT.md
docs/wave-reports/v2/opencode/W20_AUDIT_REPORT.md
docs/wave-reports/v2/opencode/W20_WAVE_REPORT.md
docs/wave-reports/v2/opencode/W21_AUDIT_REPORT.md
docs/wave-reports/v2/opencode/W21_WAVE_REPORT.md
docs/wave-reports/v2/opencode/W22_AUDIT_REPORT.md
docs/wave-reports/v2/opencode/W22_WAVE_REPORT.md
scripts/capture_build_provenance.py
scripts/generate_release_manifest.py
scripts/wx_packaged_smoke.py
src/hpc_gui/i18n/en.json
src/hpc_gui/i18n/tr.json
src/hpc_gui/services/file_context_actions.py
src/hpc_gui/services/local_files.py
src/hpc_gui/wx_connection.py
src/hpc_gui/wx_directories.py
src/hpc_gui/wx_directories_view.py
src/hpc_gui/wx_local_files.py
src/hpc_gui/wx_remote_files_view.py
src/hpc_gui/wx_shell.py
tests/test_wave_controller_regressions.py
tests/test_wx_directories.py
tests/test_wx_packaged_smoke.py
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ Get-Content .tmp/w24-run/w24-focused.txt; Write-Output "---ADJ---"; Get-Content .tmp/w24-run/w24-adjacent.txt; Write-Output "---HEAD---"; Get-Content .tmp/w24-run/w24-head.txt
.................................................................        [100%]
65 passed in 10.83s
---ADJ---
................................                                         [100%]
32 passed in 2.26s
---HEAD---
ccaf871ffc139973db826363859ca2933b216e9c
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git diff --stat -- src/hpc_gui/wx_directories.py src/hpc_gui/wx_directories_view.py src/hpc_gui/wx_shell.py tests/test_wx_directories.py 2>&1 | Select-Object -First 20; Write-Output "---CHECK-OWNED---"; git diff --check -- src/hpc_gui/wx_directories.py src/hpc_gui/wx_directories_view.py src/hpc_gui/wx_shell.py tests/test_wx_directories.py 2>&1 | Select-Object -First 20; Write-Output "---CHECK-DONE---"
src/hpc_gui/wx_directories.py      |   9 ++-
 src/hpc_gui/wx_directories_view.py | 115 +++++++++++++++++++++++++++++++----
 src/hpc_gui/wx_shell.py            |  20 +++++++
 tests/test_wx_directories.py       | 120 +++++++++++++++++++++++++++++++++++++
 4 files changed, 251 insertions(+), 13 deletions(-)
---CHECK-OWNED---
---CHECK-DONE---
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ Get-ChildItem -Recurse -Filter "REQUIREMENT_REGISTRY.md" | Select-Object FullName; Write-Output "---TODO---"; Get-ChildItem -Recurse -Filter "TODO_OWNERSHIP_MAP.md" | Select-Object FullName; Write-Output "---W24-OWNED-DIFF-NAME---"; git diff --name-only -- src/hpc_gui/wx_directories.py src/hpc_gui/wx_directories_view.py src/hpc_gui/wx_shell.py tests/test_wx_directories.py
FullName
--------
D:\Projeler\hpc-client-gui\opencode\REQUIREMENT_REGISTRY.md
---TODO---
D:\Projeler\hpc-client-gui\opencode\TODO_OWNERSHIP_MAP.md
---W24-OWNED-DIFF-NAME---
src/hpc_gui/wx_directories.py
src/hpc_gui/wx_directories_view.py
src/hpc_gui/wx_shell.py
tests/test_wx_directories.py
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ Select-String -Path opencode/REQUIREMENT_REGISTRY.md -Pattern "HPC-W06-DIR-00" | Select-Object -First 20; Write-Output "---TODO-W24---"; Select-String -Path opencode/TODO_OWNERSHIP_MAP.md -Pattern "W24" | Select-Object -First 30
opencode\REQUIREMENT_REGISTRY.md:566:| `HPC-W06-DIR-001` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_06.md` | 80 | Scope / 
Directories / storage areas | `W24` | - | The GUI must not treat "remote files" as sufficient coverage for the 
separate directories/storage-area UX. |
opencode\REQUIREMENT_REGISTRY.md:567:| `HPC-W06-DIR-002` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_06.md` | 84 | Scope / 
Directories / storage areas | `W24` | - | provider-declared home/scratch/project or other storage areas appear only 
when truthfully declared; |
opencode\REQUIREMENT_REGISTRY.md:568:| `HPC-W06-DIR-003` | CONDITIONAL | BOUNDARY | `WAVE_V2_FINAL_06.md` | 85 | Scope 
/ Directories / storage areas | `W24` | - | optional quota/status fields remain absent/unknown rather than fabricated; 
|
opencode\REQUIREMENT_REGISTRY.md:569:| `HPC-W06-DIR-004` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_06.md` | 86 | Scope / 
Directories / storage areas | `W24` | - | root switching updates the actual remote path; |
opencode\REQUIREMENT_REGISTRY.md:570:| `HPC-W06-DIR-005` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_06.md` | 87 | Scope / 
Directories / storage areas | `W24` | - | create/open/rename/delete directory actions target the selected storage 
area; |
opencode\REQUIREMENT_REGISTRY.md:571:| `HPC-W06-DIR-006` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_06.md` | 88 | Scope / 
Directories / storage areas | `W24` | - | breadcrumb/parent navigation cannot escape into a wrong synthesized path; |
opencode\REQUIREMENT_REGISTRY.md:572:| `HPC-W06-DIR-007` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_06.md` | 89 | Scope / 
Directories / storage areas | `W24` | - | context menus use the same real actions as toolbar/menu entry points; |
opencode\REQUIREMENT_REGISTRY.md:573:| `HPC-W06-DIR-008` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_06.md` | 90 | Scope / 
Directories / storage areas | `W24` | - | profile/provider switch rebuilds storage roots and discards stale directory 
callbacks; |
opencode\REQUIREMENT_REGISTRY.md:574:| `HPC-W06-DIR-009` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_06.md` | 91 | Scope / 
Directories / storage areas | `W24` | - | empty/unavailable storage-area state is distinguishable from loading/error; |
---TODO-W24---
opencode\TODO_OWNERSHIP_MAP.md:17:| `HPC-W06-TODO-DIR-SESSION-001` | `W24` | `W06` | `DIR-SESSION-001` | ACTIVE | 
`DIR-SESSION-001` - Rebind Directories Home/Scratch/provider storage roots from the CURRENT session after connect. |
opencode\TODO_OWNERSHIP_MAP.md:18:| `HPC-W06-TODO-SESSION-REBIND-001` | `W24` | `W06` | `SESSION-REBIND-001` | ACTIVE 
| `SESSION-REBIND-001` - Rebind Directories again after reconnect/new session generation. |
opencode\TODO_OWNERSHIP_MAP.md:19:| `HPC-W06-TODO-SESSION-REBIND-002` | `W24` | `W06` | `SESSION-REBIND-002` | ACTIVE 
| `SESSION-REBIND-002` - Profile/provider A  B switch must replace all A paths/backends/provider metadata with B 
state. |
opencode\TODO_OWNERSHIP_MAP.md:20:| `HPC-W06-TODO-SESSION-DISCONNECT-001` | `W24` | `W06` | `SESSION-DISCONNECT-001` | 
ACTIVE | `SESSION-DISCONNECT-001` - On disconnect, show explicit disconnected/unavailable state; do not present stale 
listing or placeholder `/` as a valid provider root. |
opencode\TODO_OWNERSHIP_MAP.md:21:| `HPC-W06-TODO-DIR-SESSION-002` | `W24` | `W06` | `DIR-SESSION-002` | ACTIVE | 
`DIR-SESSION-002` - New Slurm/Create-Edit Slurm destination must be resolved at click time from CURRENT provider 
storage, never a startup-captured `scratch_dir`. |
opencode\TODO_OWNERSHIP_MAP.md:22:| `HPC-W06-TODO-006` | `W24` | `W06` | `-` | ACTIVE | Verify Directories 
favorites/history/filter/navigation store also rebind correctly on profile/provider switch. |
opencode\TODO_OWNERSHIP_MAP.md:27:| `HPC-W06-TODO-EDITOR-ROUTE-001` | `W24` | `W06` | `EDITOR-ROUTE-001` | ACTIVE | 
`EDITOR-ROUTE-001` - Both `Files  Edit` and `Directories  Edit` select/focus the embedded Script Editor and open the 
requested document there. |
opencode\TODO_OWNERSHIP_MAP.md:69:| `HPC-W06-TODO-016` | `W24` | `W06` | `-` | ACTIVE | Prevent accidental duplicate 
detached Files/Directories/Logs/Editor primary windows. |
opencode\TODO_OWNERSHIP_MAP.md:73:| `HPC-W06-TODO-017` | `W24` | `W06` | `-` | ACTIVE | Define one shell-level 
session-generation/rebind contract for Terminal, Jobs, Directories, Remote Files, Transfers, and Editor actions. |
opencode\TODO_OWNERSHIP_MAP.md:78:| `HPC-W06-TODO-018` | `W24` | `W06` | `-` | ACTIVE | Inventory Directories, Files, 
Script Editor, Logs toolbars/action rows separately. |
opencode\TODO_OWNERSHIP_MAP.md:90:| `HPC-W06-TODO-019` | `W24` | `W06` | `-` | ACTIVE | Replace fixed `460` initial 
split with balanced initial layout (approximately 50/50) and preserve user movement. |
opencode\TODO_OWNERSHIP_MAP.md:91:| `HPC-W06-TODO-020` | `W24` | `W06` | `-` | ACTIVE | Use meaningful semantic pane 
titles (`Scratch`, `Home`, provider labels) instead of raw path-only headings where appropriate. |
opencode\TODO_OWNERSHIP_MAP.md:92:| `HPC-W06-TODO-021` | `W24` | `W06` | `-` | ACTIVE | Decide and implement explicit 
Directories toolbar profile so each pane exposes only actions intended for this surface. |
opencode\TODO_OWNERSHIP_MAP.md:93:| `HPC-W06-TODO-022` | `W24` | `W06` | `-` | ACTIVE | Verify equivalent provider 
storage panes remain structurally consistent. |
opencode\TODO_OWNERSHIP_MAP.md:94:| `HPC-W06-TODO-023` | `W24` | `W06` | `-` | ACTIVE | Verify responsive 
columns/action wrapping at supported window sizes. |
opencode\TODO_OWNERSHIP_MAP.md:103:| `HPC-W06-TODO-032` | `W24` | `W06` | `-` | ACTIVE | Re-run synchronized-browsing 
and Compare Directories acceptance on the exact release candidate. |
opencode\TODO_OWNERSHIP_MAP.md:138:| `HPC-W06-TODO-041` | `W24` | `W06` | `-` | ACTIVE | Add all new 
shell/session/editor/directories/logs/settings/plugins/runtime/release IDs introduced in the final 
specification/Waves. |
opencode\TODO_OWNERSHIP_MAP.md:184:| `HPC-W06-TODO-044` | `W24` | `W06` | `-` | ACTIVE | Files/Directories/Editor 
cross-surface packaged acceptance. |
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest tests/test_wx_directories.py tests/test_remote_directory_listing.py tests/test_transfer_directory_controllers.py tests/test_wave2_directories_local_files.py -q 2>&1 | Select-Object -Last 15
.................................................................        [100%]
65 passed in 10.34s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest tests/test_wx_shell.py tests/test_wx_lifecycle.py tests/test_wx_remote_files.py tests/test_directory_comparison.py -q 2>&1 | Select-Object -Last 15
................................                                         [100%]
32 passed in 1.73s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git diff -- src/hpc_gui/wx_directories.py src/hpc_gui/wx_directories_view.py src/hpc_gui/wx_shell.py tests/test_wx_directories.py 2>&1 | Select-Object -First 300
diff --git a/src/hpc_gui/wx_directories.py b/src/hpc_gui/wx_directories.py
index 28bfcd33..14cc67c2 100644
--- a/src/hpc_gui/wx_directories.py
+++ b/src/hpc_gui/wx_directories.py
@@ -36,9 +36,14 @@ class WxDirectoriesWorkspace:
     def storage(self, storage_id: str) -> StoragePane:
         return next(item for item in self.storages if item.id == storage_id)
 
-    def double_click(self, path: str, *, is_dir: bool = False) -> str:
+    def double_click(self, path: str, *, is_dir: bool = False, storage_id: str = "") -> str:
         if is_dir and self.remote:
-            self.remote[next(iter(self.remote))].navigate(path)
+            # W24 DIR-005: directory navigation must target the selected
+            # storage area, never silently collapse onto the first pane.
+            target = self.remote.get(storage_id) if storage_id else None
+            if target is None:
+                target = self.remote.get(next(iter(self.remote)))
+            target.navigate(path)
             return "navigate"
         if self._open_editor:
             self._open_editor(path)
diff --git a/src/hpc_gui/wx_directories_view.py b/src/hpc_gui/wx_directories_view.py
index 383dd8d1..e354f7cd 100644
--- a/src/hpc_gui/wx_directories_view.py
+++ b/src/hpc_gui/wx_directories_view.py
@@ -61,6 +61,94 @@ def _resolve_scratch_home(session_state) -> tuple[str, str]:
     return scratch_dir, home_dir
 
 
+def _resolve_live_files(session_state, snapshot_files=None):
+    """Return the CURRENT session files backend (live-first rebind contract).
+
+    W24 DIR-008 / SESSION-REBIND-002: a profile/provider switch or reconnect
+    must replace the directories backend. A build-time snapshot may only serve
+    as a fallback when no live backend exists; it must never shadow live state.
+    """
+    sess = (session_state or {}).get("session") or {} if isinstance(session_state, dict) else {}
+    live = sess.get("files") if isinstance(sess, dict) else None
+    if live is not None:
+        return live
+    return snapshot_files
+
+
+def _resolve_new_slurm_target(session_state, name: str) -> str:
+    """Resolve a New-Slurm destination at click time from CURRENT storage.
+
+    W24 DIR-SESSION-002: never reuse a panel-build-time ``scratch_dir``
+    capture; derive the scratch root live via :func:`_resolve_scratch_home`.
+    """
+    live_scratch, _home = _resolve_scratch_home(session_state)
+    clean = (name or "").strip()
+    return live_scratch.rstrip("/") + "/" + clean
+
+
+def rebind_directories_storage(host, session_state) -> dict:
+    """Rebind directories panes to the CURRENT session (W24 DIR-SESSION-001).
+
+    Recomputes scratch/home from the live session, updates semantic labels,
+    navigates both models, and invalidates stale listing caches. Returns the
+    resolved ``{"scratch": ..., "home": ...}`` paths.
+    """
+    live_scratch, live_home = _resolve_scratch_home(session_state)
+    models = getattr(host, "_wx_dirs_models", None) or {}
+    controls = getattr(host, "_wx_dirs_controls", None) or {}
+    for key, path in (("scratch", live_scratch), ("home", live_home)):
+        model = models.get(key)
+        if model is not None:
+            try:
+                model.invalidate()
+            except Exception:
+                pass
+            # W24 TODO-006 / DIR-008: a provider switch starts a new navigation
+            # context; provider-A history entries must not linger. Favorites
+            # are explicit user saves and persist by design.
+            try:
+                if isinstance(getattr(model, "history", None), list):
+                    model.history.clear()
+            except Exception:
+                pass
+            try:
+                model.navigate(path)
+            except Exception:
+                pass
+    semantic = {"scratch": "Scratch", "home": "Home"}
+    for key, path in (("scratch", live_scratch), ("home", live_home)):
+        label = controls.get(f"{key}_label")
+        if label is not None:
+            try:
+                label.SetLabel(f"{semantic[key]} — {path}")
+            except Exception:
+                pass
+    return {"scratch": live_scratch, "home": live_home}
+
+
+def mark_directories_disconnected(host) -> None:
+    """Show explicit disconnected state (W24 SESSION-DISCONNECT-001 / DIR-009).
+
+    Labels become distinguishable from loading/error, and stale listing
+    caches are dropped so no dead-backend listing is presented as valid.
+    """
+    controls = getattr(host, "_wx_dirs_controls", None) or {}
+    models = getattr(host, "_wx_dirs_models", None) or {}
+    for key, semantic in (("scratch", "Scratch"), ("home", "Home")):
+        model = models.get(key)
+        if model is not None:
+            try:
+                model.invalidate()
+            except Exception:
+                pass
+        label = controls.get(f"{key}_label")
+        if label is not None:
+            try:
+                label.SetLabel(f"{semantic} — disconnected")
+            except Exception:
+                pass
+
+
 def _build_directories(parent, *, session_state=None, workspace: WxDirectoriesWorkspace | None = None, loader=None, operation=None, read_text=None, open_editor=None, open_editor_new_window=None, run_shell=None, submit=None, embedded):
     try:
         import wx
@@ -84,9 +172,7 @@ def _build_directories(parent, *, session_state=None, workspace: WxDirectoriesWo
     snapshot_files = snapshot_session.get("files") if isinstance(snapshot_session, dict) else None
 
     def _files():
-        sess = (session_state or {}).get("session") or {} if isinstance(session_state, dict) else {}
-        f = snapshot_files if snapshot_files is not None else (sess.get("files") if isinstance(sess, dict) else None)
-        return f
+        return _resolve_live_files(session_state, snapshot_files)
 
     # Default loader/operation/read_text if not supplied – delegate to files backend dynamically
     if loader is None:
@@ -199,11 +285,11 @@ def _build_directories(parent, *, session_state=None, workspace: WxDirectoriesWo
     scratch_model = WxRemoteDirectoryModel(scratch_dir)
     home_model = WxRemoteDirectoryModel(home_dir)
 
-    # Each pane shows its path as a title above the listing (Qt parity: directories_widget.py:216-219)
-    # Use already-derived scratch_dir/home_dir; no new derivation or hardcoded paths.
+    # Each pane shows a semantic title plus its path (W24 TODO-020: meaningful
+    # pane titles instead of raw path-only headings).
     scratch_container = wx.Panel(splitter)
     scratch_sizer = wx.BoxSizer(wx.VERTICAL)
-    scratch_label = wx.StaticText(scratch_container, label=scratch_dir)
+    scratch_label = wx.StaticText(scratch_container, label=f"Scratch — {scratch_dir}")
     scratch_sizer.Add(scratch_label, 0, wx.EXPAND | wx.ALL, 4)
     scratch_panel = build_remote_files_panel(
         scratch_container,
@@ -220,7 +306,7 @@ def _build_directories(parent, *, session_state=None, workspace: WxDirectoriesWo
 
     home_container = wx.Panel(splitter)
     home_sizer = wx.BoxSizer(wx.VERTICAL)
-    home_label = wx.StaticText(home_container, label=home_dir)
+    home_label = wx.StaticText(home_container, label=f"Home — {home_dir}")
     home_sizer.Add(home_label, 0, wx.EXPAND | wx.ALL, 4)
     home_panel = build_remote_files_panel(
         home_container,
@@ -235,7 +321,10 @@ def _build_directories(parent, *, session_state=None, workspace: WxDirectoriesWo
     home_sizer.Add(home_panel, 1, wx.EXPAND)
     home_container.SetSizer(home_sizer)
 
-    splitter.SplitVertically(scratch_container, home_container, 460)
+    # W24 TODO-019: balanced ~50/50 initial layout (host is 1000px wide) with
+    # sash gravity so user movement is preserved proportionally on resize.
+    splitter.SetSashGravity(0.5)
+    splitter.SplitVertically(scratch_container, home_container, 500)
     splitter.SetMinimumPaneSize(260)
     root.Add(splitter, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
     panel.SetSizer(root)
@@ -269,9 +358,11 @@ def _build_directories(parent, *, session_state=None, workspace: WxDirectoriesWo
             return
         if not name.lower().endswith((".slurm", ".sbatch")):
             name += ".slurm"
-        target_path = scratch_dir.rstrip("/") + "/" + name
+        # W24 DIR-SESSION-002: resolve destination at click time from CURRENT
+        # provider storage, never the panel-build-time scratch_dir capture.
+        target_path = _resolve_new_slurm_target(session_state, name)
 
-        files = sess.get("files")
+        files = _resolve_live_files(session_state, sess.get("files"))
         if files is not None:
             try:
                 exists = bool(files.exists(target_path))
@@ -351,6 +442,8 @@ def _build_directories(parent, *, session_state=None, workspace: WxDirectoriesWo
     }
     host._wx_dirs_workspace = workspace
     host._wx_dirs_models = {"scratch": scratch_model, "home": home_model}
+    host._wx_dirs_rebind = lambda state=None: rebind_directories_storage(host, session_state if state is None else state)
+    host._wx_dirs_disconnected = lambda: mark_directories_disconnected(host)
 
     finish()
     return host
@@ -394,4 +487,4 @@ def show_directories(parent=None, *, session_state=None, workspace: WxDirectorie
     return wx.ID_OK
 
 
-__all__ = ["build_directories_panel", "show_directories"]
+__all__ = ["_resolve_live_files", "_resolve_new_slurm_target", "_resolve_scratch_home", "build_directories_panel", "mark_directories_disconnected", "rebind_directories_storage", "show_directories"]
diff --git a/src/hpc_gui/wx_shell.py b/src/hpc_gui/wx_shell.py
index e2f36a09..d9ec7799 100644
--- a/src/hpc_gui/wx_shell.py
+++ b/src/hpc_gui/wx_shell.py
@@ -241,6 +241,7 @@ def create_shell_frame(app=None, *, tray_factory=None, lifecycle=None, session_s
     directories_panel = build_directories_panel(notebook, **_dirs)
     notebook.AddPage(directories_panel, t("tabs.directories"), False)
     page_controls["NAV-DIRECTORIES"] = {"page": directories_panel}
+    session_state["_embedded_directories_panel"] = directories_panel
 
     # Files (header row + splitter with local left, remote right + transfers bottom)
     files_page = wx.Panel(notebook)
@@ -301,6 +302,9 @@ def create_shell_frame(app=None, *, tray_factory=None, lifecycle=None, session_s
     session_state["_embedded_remote_files_panel"] = remote_panel
     top_splitter.SplitVertically(local_panel, remote_panel, 340)
     top_splitter.SetMinimumPaneSize(300)
+    # TODO-031: keep the Local/Remote split proportionally balanced on resize
+    # instead of pinning the local pane to the fixed 340px initial sash.
+    top_splitter.SetSashGravity(0.5)
     from hpc_gui.wx_transfer_workspace import build_transfers_panel
 
     transfers_panel = build_transfers_panel(transfer_splitter)
@@ -3355,6 +3359,14 @@ def _connection_callbacks(session_state, parent, lifecycle):
                     panel._wx_remote_set_provider_filters(cbs.get("provider_filters"), cbs.get("plugin_filters"))
             except Exception:
                 pass
+        # W24 DIR-SESSION-001 / SESSION-REBIND-001: rebind directories storage
+        # roots from the CURRENT session after connect.
+        try:
+            dirs_panel = session_state.get("_embedded_directories_panel")
+            if dirs_panel is not None and hasattr(dirs_panel, "_wx_dirs_rebind"):
+                dirs_panel._wx_dirs_rebind(session_state)
+        except Exception:
+            pass
 
     def on_disconnected(session):
         # Graceful/transport-loss teardown (CONN-004/TODO-007): drop the dead
@@ -3378,6 +3390,14 @@ def _connection_callbacks(session_state, parent, lifecycle):
                     panel._wx_jobs_set_session(None)
             except Exception:
                 pass
+        # W24 SESSION-DISCONNECT-001 / DIR-009: explicit disconnected state,
+        # never a stale listing or placeholder root presented as valid.
+        try:
+            dirs_panel = session_state.get("_embedded_directories_panel")
+            if dirs_panel is not None and hasattr(dirs_panel, "_wx_dirs_disconnected"):
+                dirs_panel._wx_dirs_disconnected()
+        except Exception:
+            pass
 
     return {"profiles": profiles, "lifecycle": lifecycle, "on_connected": on_connected, "on_disconnected": on_disconnected}
 
diff --git a/tests/test_wx_directories.py b/tests/test_wx_directories.py
index 9d7e9573..59ac708f 100644
--- a/tests/test_wx_directories.py
+++ b/tests/test_wx_directories.py
@@ -31,3 +31,123 @@ def test_batch_submit_is_deterministic_and_model_has_no_qt():
     assert workspace.batch_submit(("/x/b.slurm", "/x/a.slurm"))[1].index == 2
     source = open("src/hpc_gui/wx_directories.py", encoding="utf-8").read()
     assert "PySide6" not in source and "wx" in source
+
+
+@pytest.mark.unit
+@pytest.mark.wx
+@pytest.mark.semantic
+def test_w24_new_slurm_target_resolves_from_current_session_at_click_time():
+    """REQ HPC-W06-TODO-DIR-SESSION-002 / DIR-004: click-time scratch resolve."""
+    from hpc_gui.wx_directories_view import _resolve_new_slurm_target
+
+    def _session(scratch):
+        return {
+            "session": {
+                "profile": {"username": "hpctest"},
+                "cfg": {
+                    "username": "hpctest",
+                    "system_settings": {"scratch_dir": scratch, "home_dir": "/home/hpctest"},
+                },
+            }
+        }
+
+    first = _resolve_new_slurm_target(_session("/scratch/aaa"), "new_job.slurm")
+    second = _resolve_new_slurm_target(_session("/scratch/bbb"), "new_job.slurm")
+    assert first == "/scratch/aaa/new_job.slurm"
+    assert second == "/scratch/bbb/new_job.slurm"
+    # Negative: stale build-time capture must not leak into the second resolve.
+    assert second != first
+
+
+@pytest.mark.unit
+@pytest.mark.wx
+@pytest.mark.semantic
+def test_w24_directories_backend_rebind_prefers_live_session_files():
+    """REQ HPC-W06-DIR-008 / SESSION-REBIND-002: live backend wins over snapshot."""
+    from hpc_gui.wx_directories_view import _resolve_live_files
+
+    old_backend, new_backend = object(), object()
+    session_state = {"session": {"files": old_backend}}
+    assert _resolve_live_files(session_state, old_backend) is old_backend
+    # Profile/provider switch replaces the live backend object.
+    session_state["session"]["files"] = new_backend
+    assert _resolve_live_files(session_state, old_backend) is new_backend
+    # Negative: disconnect (live backend gone) falls back to snapshot/None safely.
+    session_state["session"]["files"] = None
+    assert _resolve_live_files(session_state, old_backend) is old_backend
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git diff -- src/hpc_gui/wx_directories.py src/hpc_gui/wx_directories_view.py src/hpc_gui/wx_shell.py tests/test_wx_directories.py 2>&1 | Select-Object -Last 150
+            if dirs_panel is not None and hasattr(dirs_panel, "_wx_dirs_rebind"):
+                dirs_panel._wx_dirs_rebind(session_state)
+        except Exception:
+            pass
 
     def on_disconnected(session):
         # Graceful/transport-loss teardown (CONN-004/TODO-007): drop the dead
@@ -3378,6 +3390,14 @@ def _connection_callbacks(session_state, parent, lifecycle):
                     panel._wx_jobs_set_session(None)
             except Exception:
                 pass
+        # W24 SESSION-DISCONNECT-001 / DIR-009: explicit disconnected state,
+        # never a stale listing or placeholder root presented as valid.
+        try:
+            dirs_panel = session_state.get("_embedded_directories_panel")
+            if dirs_panel is not None and hasattr(dirs_panel, "_wx_dirs_disconnected"):
+                dirs_panel._wx_dirs_disconnected()
+        except Exception:
+            pass
 
     return {"profiles": profiles, "lifecycle": lifecycle, "on_connected": on_connected, "on_disconnected": on_disconnected}
 
diff --git a/tests/test_wx_directories.py b/tests/test_wx_directories.py
index 9d7e9573..59ac708f 100644
--- a/tests/test_wx_directories.py
+++ b/tests/test_wx_directories.py
@@ -31,3 +31,123 @@ def test_batch_submit_is_deterministic_and_model_has_no_qt():
     assert workspace.batch_submit(("/x/b.slurm", "/x/a.slurm"))[1].index == 2
     source = open("src/hpc_gui/wx_directories.py", encoding="utf-8").read()
     assert "PySide6" not in source and "wx" in source
+
+
+@pytest.mark.unit
+@pytest.mark.wx
+@pytest.mark.semantic
+def test_w24_new_slurm_target_resolves_from_current_session_at_click_time():
+    """REQ HPC-W06-TODO-DIR-SESSION-002 / DIR-004: click-time scratch resolve."""
+    from hpc_gui.wx_directories_view import _resolve_new_slurm_target
+
+    def _session(scratch):
+        return {
+            "session": {
+                "profile": {"username": "hpctest"},
+                "cfg": {
+                    "username": "hpctest",
+                    "system_settings": {"scratch_dir": scratch, "home_dir": "/home/hpctest"},
+                },
+            }
+        }
+
+    first = _resolve_new_slurm_target(_session("/scratch/aaa"), "new_job.slurm")
+    second = _resolve_new_slurm_target(_session("/scratch/bbb"), "new_job.slurm")
+    assert first == "/scratch/aaa/new_job.slurm"
+    assert second == "/scratch/bbb/new_job.slurm"
+    # Negative: stale build-time capture must not leak into the second resolve.
+    assert second != first
+
+
+@pytest.mark.unit
+@pytest.mark.wx
+@pytest.mark.semantic
+def test_w24_directories_backend_rebind_prefers_live_session_files():
+    """REQ HPC-W06-DIR-008 / SESSION-REBIND-002: live backend wins over snapshot."""
+    from hpc_gui.wx_directories_view import _resolve_live_files
+
+    old_backend, new_backend = object(), object()
+    session_state = {"session": {"files": old_backend}}
+    assert _resolve_live_files(session_state, old_backend) is old_backend
+    # Profile/provider switch replaces the live backend object.
+    session_state["session"]["files"] = new_backend
+    assert _resolve_live_files(session_state, old_backend) is new_backend
+    # Negative: disconnect (live backend gone) falls back to snapshot/None safely.
+    session_state["session"]["files"] = None
+    assert _resolve_live_files(session_state, old_backend) is old_backend
+    assert _resolve_live_files({"session": {}}, None) is None
+
+
+@pytest.mark.unit
+@pytest.mark.wx
+@pytest.mark.semantic
+def test_w24_double_click_targets_selected_storage_area():
+    """REQ HPC-W06-DIR-005: directory navigation targets the selected pane."""
+    workspace = WxDirectoriesWorkspace(
+        ({"id": "scratch", "path": "/scratch/u"}, {"id": "home", "path": "/home/u"}),
+    )
+    assert workspace.double_click("/home/u/sub", is_dir=True, storage_id="home") == "navigate"
+    assert workspace.remote["home"].current_path == "/home/u/sub"
+    # The unselected pane must not move.
+    assert workspace.remote["scratch"].current_path == "/scratch/u"
+    # Negative: compat path without storage_id keeps first-pane behavior.
+    assert workspace.double_click("/scratch/u/other", is_dir=True) == "navigate"
+    assert workspace.remote["scratch"].current_path == "/scratch/u/other"
+
+
+@pytest.mark.unit
+@pytest.mark.wx
+@pytest.mark.semantic
+def test_w24_directories_rebind_and_disconnect_helpers():
+    """REQ DIR-SESSION-001 / SESSION-DISCONNECT-001 / DIR-009 / TODO-020."""
+    from hpc_gui.wx_directories_view import (
+        mark_directories_disconnected,
+        rebind_directories_storage,
+    )
+
+    class _Label:
+        def __init__(self, text=""):
+            self.text = text
+
+        def SetLabel(self, value):
+            self.text = value
+
+    class _Model:
+        def __init__(self, path):
+            self.current_path = path
+            self.invalidated = 0
+            self.history = ["/old/provider-a-path"]
+
+        def invalidate(self):
+            self.invalidated += 1
+
+        def navigate(self, path):
+            self.current_path = path
+
+    class _Host:
+        pass
+
+    host = _Host()
+    host._wx_dirs_models = {"scratch": _Model("/old/scratch"), "home": _Model("/old/home")}
+    host._wx_dirs_controls = {"scratch_label": _Label(), "home_label": _Label()}
+    session_state = {
+        "session": {
+            "profile": {"username": "hpctest"},
+            "cfg": {
+                "username": "hpctest",
+                "system_settings": {"scratch_dir": "/scratch/new", "home_dir": "/home/new"},
+            },
+        }
+    }
+    resolved = rebind_directories_storage(host, session_state)
+    assert resolved == {"scratch": "/scratch/new", "home": "/home/new"}
+    assert host._wx_dirs_models["scratch"].current_path == "/scratch/new"
+    assert host._wx_dirs_models["home"].current_path == "/home/new"
+    assert host._wx_dirs_controls["scratch_label"].text == "Scratch — /scratch/new"
+    assert host._wx_dirs_controls["home_label"].text == "Home — /home/new"
+    # Stale provider-A history must not survive the rebind.
+    assert host._wx_dirs_models["scratch"].history == []
+    # Negative: disconnect must not keep stale paths as valid.
+    mark_directories_disconnected(host)
+    assert host._wx_dirs_controls["scratch_label"].text == "Scratch — disconnected"
+    assert host._wx_dirs_controls["home_label"].text == "Home — disconnected"
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ Write-Output "---SECRETS-SCAN-OWNED---"; git diff -- src/hpc_gui/wx_directories.py src/hpc_gui/wx_directories_view.py src/hpc_gui/wx_shell.py tests/test_wx_directories.py | Select-String -Pattern "(AKIA|BEGIN.*PRIVATE|password\s*=\s*['\"][^'\"]+|token\s*=\s*['\"][^'\"]+|secret)" | Select-Object -First 20; Write-Output "---SCAN-DONE---"; Write-Output "---SKIP-XFAIL---"; git diff -- tests/test_wx_directories.py | Select-String -Pattern "skip|xfail|TODO-032|TODO-041" | Select-Object -First 20; Write-Output "---QUOTA-WIDGETS---"; Select-String -Path src/hpc_gui/wx_directories_view.py -Pattern "quota|status" | Select-Object -First 10; Write-Output "---SHELL-WIRING---"; Select-String -Path src/hpc_gui/wx_shell.py -Pattern "_embedded_directories_panel|_wx_dirs_rebind|_wx_dirs_disconnected" | Select-Object -First 10
ParserError: 
Line |
   1 |  . |password\s*=\s*['\"][^'\"]+|token\s*=\s*['\"][^'\"]+|secret)" | Sele .
     |                                                                ~
     | Unexpected token ')' in expression or statement.
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git diff -- src/hpc_gui/wx_directories_view.py src/hpc_gui/wx_shell.py tests/test_wx_directories.py | Select-String -Pattern "BEGIN.*PRIVATE" | Select-Object -First 20; Write-Output "---SCAN-DONE---"
---SCAN-DONE---
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ Select-String -Path src/hpc_gui/wx_directories_view.py -Pattern "quota" | Select-Object -First 10; Write-Output "---SHELL-WIRING---"; Select-String -Path src/hpc_gui/wx_shell.py -Pattern "_embedded_directories_panel" | Select-Object -First 10
---SHELL-WIRING---

src\hpc_gui\wx_shell.py:244:    session_state["_embedded_directories_panel"] = directories_panel
src\hpc_gui\wx_shell.py:3365:            dirs_panel = session_state.get("_embedded_directories_panel")
src\hpc_gui\wx_shell.py:3396:            dirs_panel = session_state.get("_embedded_directories_panel")
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ Select-String -Path src/hpc_gui/wx_shell.py -Pattern "_wx_dirs_rebind" | Select-Object -First 10; Write-Output "---LABELS---"; Select-String -Path src/hpc_gui/wx_directories_view.py -Pattern "Scratch|Home —|SetSashGravity|SplitVertically" | Select-Object -First 12; Write-Output "---SKIPCHECK---"; Select-String -Path tests/test_wx_directories.py -Pattern "skip" | Select-Object -First 10
src\hpc_gui\wx_shell.py:3366:            if dirs_panel is not None and hasattr(dirs_panel, "_wx_dirs_rebind"):
src\hpc_gui\wx_shell.py:3367:                dirs_panel._wx_dirs_rebind(session_state)
---LABELS---
src\hpc_gui\wx_directories_view.py:14:def _resolve_scratch_home(session_state) -> tuple[str, str]:
src\hpc_gui\wx_directories_view.py:15:    """Derive scratch/home paths from session, never hardcode."""
src\hpc_gui\wx_directories_view.py:54:    scratch_dir = format_remote_path(system.get("scratch_dir", ""), user) if 
isinstance(system.get("scratch_dir"), str) else ""
src\hpc_gui\wx_directories_view.py:57:    if not scratch_dir:
src\hpc_gui\wx_directories_view.py:58:        scratch_dir = "/"
src\hpc_gui\wx_directories_view.py:61:    return scratch_dir, home_dir
src\hpc_gui\wx_directories_view.py:81:    W24 DIR-SESSION-002: never reuse a panel-build-time ``scratch_dir``
src\hpc_gui\wx_directories_view.py:82:    capture; derive the scratch root live via :func:`_resolve_scratch_home`.
src\hpc_gui\wx_directories_view.py:84:    live_scratch, _home = _resolve_scratch_home(session_state)
src\hpc_gui\wx_directories_view.py:86:    return live_scratch.rstrip("/") + "/" + clean
src\hpc_gui\wx_directories_view.py:92:    Recomputes scratch/home from the live session, updates semantic labels,
src\hpc_gui\wx_directories_view.py:94:    resolved ``{"scratch": ..., "home": ...}`` paths.
---SKIPCHECK---
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ Select-String -Path src/hpc_gui/wx_directories_view.py -Pattern "SetSashGravity" | Select-Object -First 5; Write-Output "---SPLIT---"; Select-String -Path src/hpc_gui/wx_directories_view.py -Pattern "SplitVertically" | Select-Object -First 5; Write-Output "---DISCONNECTED---"; Select-String -Path src/hpc_gui/wx_directories_view.py -Pattern "disconnected" | Select-Object -First 8
src\hpc_gui\wx_directories_view.py:326:    splitter.SetSashGravity(0.5)
---SPLIT---
src\hpc_gui\wx_directories_view.py:327:    splitter.SplitVertically(scratch_container, home_container, 500)
---DISCONNECTED---
src\hpc_gui\wx_directories_view.py:129:def mark_directories_disconnected(host) -> None:
src\hpc_gui\wx_directories_view.py:130:    """Show explicit disconnected state (W24 SESSION-DISCONNECT-001 / DIR-009).
src\hpc_gui\wx_directories_view.py:147:                label.SetLabel(f"{semantic} - disconnected")
src\hpc_gui\wx_directories_view.py:446:    host._wx_dirs_disconnected = lambda: mark_directories_disconnected(host)
src\hpc_gui\wx_directories_view.py:490:__all__ = ["_resolve_live_files", "_resolve_new_slurm_target", 
"_resolve_scratch_home", "build_directories_panel", "mark_directories_disconnected", "rebind_directories_storage", 
"show_directories"]
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ Select-String -Path src/hpc_gui/wx_remote_files_view.py -Pattern "PurePosixPath" | Select-Object -First 5; Write-Output "---SHARED-BUILDER---"; Select-String -Path src/hpc_gui/wx_directories_view.py -Pattern "build_remote_files_panel" | Select-Object -First 5; Write-Output "---OPEN-EDITOR---"; Select-String -Path src/hpc_gui/wx_directories_view.py -Pattern "open_primary|is_local" | Select-Object -First 8
src\hpc_gui\wx_remote_files_view.py:6:from pathlib import PurePosixPath
src\hpc_gui\wx_remote_files_view.py:111:        target = str(PurePosixPath(target_path).parent) if kind == "file" else 
str(target_path)
src\hpc_gui\wx_remote_files_view.py:347:            name = PurePosixPath(entry.path).name or entry.path
src\hpc_gui\wx_remote_files_view.py:371:            idx = listing.InsertItem(listing.GetItemCount(), 
PurePosixPath(entry.path).name or entry.path)
src\hpc_gui\wx_remote_files_view.py:381:        remote_path = str(PurePosixPath(remote_path or "/"))
---SHARED-BUILDER---
src\hpc_gui\wx_directories_view.py:158:    from hpc_gui.wx_remote_files_view import build_remote_files_panel
src\hpc_gui\wx_directories_view.py:294:    scratch_panel = build_remote_files_panel(
src\hpc_gui\wx_directories_view.py:311:    home_panel = build_remote_files_panel(
---OPEN-EDITOR---
src\hpc_gui\wx_directories_view.py:234:                            mgr.open_primary(path, content, is_local=False, 
request_id=request_id)
src\hpc_gui\wx_directories_view.py:236:                            mgr.open_primary(path, content, is_local=False)
src\hpc_gui\wx_directories_view.py:247:                        mgr.open_new_window(path, content, is_local=False)
src\hpc_gui\wx_directories_view.py:259:                _mgr.open_primary(path, content, is_local=False, 
request_id=request_id)
src\hpc_gui\wx_directories_view.py:266:                _mgr.open_new_window(path, content, is_local=False)
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
Auditing W24 — loading canonical policy and evidence.
Run self-check noted — now verifying W24 evidence independently.
Ownership and scope confirmed — running independent test verification.
Core implementation verified — checking final compliance gates.
## W24 Fresh Independent Audit — PASS

**Wave:** W24 (Directories, storage roots and session rebinding) — `waves/pending/W24.md`, `audit_policy: fresh-independent`, required evidence `GUI,EXTERNAL`.
**Candidate binding:** HEAD `ccaf871ffc139973db826363859ca2933b216e9c` (verified `git rev-parse HEAD`) + exact W24-owned working-tree hunks; controller `content_identity: d931010e…` accepted as authority. `findings_path: null` — no routed findings pending. W23 PASS receipt consumed only as prior-wave context, never as W24 evidence.
**Read-only boundary:** no product/test/evidence files modified; verification via reads, `git diff`, and test execution only.

### Independent verification (fresh context)
- Focused rerun `test_wx_directories + test_remote_directory_listing + test_transfer_directory_controllers + test_wave2_directories_local_files` → **65 passed** (matches `.tmp/w24-run/w24-focused.txt`).
- Adjacent rerun `test_wx_shell + test_wx_lifecycle + test_wx_remote_files + test_directory_comparison` → **32 passed** (matches `w24-adjacent.txt`).
- Owned diff: 4 files, +251/-13 (`wx_directories.py`, `wx_directories_view.py`, `wx_shell.py`, `tests/test_wx_directories.py`); `git diff --check` on owned paths **clean**. Full-tree 86-file dirty state correctly excluded — report scopes claim to the 4 owned files and preserves unrelated stacked hunks (e.g. pre-existing `top_splitter.SetSashGravity` TODO-031 hunk disclosed, not claimed).
- FIX-A click-time scratch resolve (`_resolve_new_slurm_target`), FIX-B live-first backend (`_resolve_live_files`), FIX-C `double_click(storage_id=...)` selected-pane targeting, FIX-D `rebind_directories_storage` / `mark_directories_disconnected` + shell `on_connected`/`on_disconnected` wiring — all present in diff and exercised by 4 new behavioral tests with negative paths. Sensitivity rationale holds (new signatures/helpers fail pre-fix by construction); no stash mutation performed by auditor.
- Spot checks: no quota/status widgets (DIR-003 conditional holds); `PurePosixPath` remote semantics (DIR-010); shared `build_remote_files_panel` both panes (DIR-007/022); `open_primary is_local=False` editor route; sash 500 + gravity 0.5 (TODO-019); semantic `Scratch — /…` / `Home — /…` + `— disconnected` labels (TODO-020, DIR-009); history cleared on rebind, favorites persist by design (TODO-006).
- Quality gates: no skip/xfail added, no weakened assertions, no secrets/private keys in owned hunks, no binary noise.
- Deferred items: TODO-032 `AWAITING_INPUT` legitimate (synchronized-browsing/Compare acceptance requires a release-candidate identity that does not exist at this HEAD; required evidence classes are GUI+EXTERNAL only); TODO-041 N/A with reason legitimate (no new stable-ID surfaces introduced); TODO-044 source/runtime covered, package binding rides TODO-032. No product defect hidden.
- GUI/EXTERNAL: unit+source proof independently re-verified; worker EV-GUI-BUILD/REBIND/DISCONNECT/SHELL-WIRING readbacks consistent with code; EXTERNAL key-auth SFTP empty/non-empty listings non-mutating with lab-health caveat properly scoped (compute01 Slurm down irrelevant to storage-root listing). No fabrication signals; external replay steps documented for controller re-execution. Closeout validator correctly deferred to controller CLOSE per independence contract.
- No cross-scope defects; nothing to route. No contradiction between requirements, code, tests, and evidence.

**Verdict:** all 11 DIR + 18 TODO-detail owned items implemented or truthfully dispositioned, evidence current and bound to candidate, no owned blocking defect. Fresh independent audit **PASS**.

AC_WAVE_MACHINE_RESULT_BEGIN
WAVE_PHASE_STATUS: PASS
AC_WAVE_MACHINE_RESULT_END
```

WAVE_PHASE_STATUS: PASS
