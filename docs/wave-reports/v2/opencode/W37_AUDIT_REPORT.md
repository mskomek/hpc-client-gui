# W37 — Fresh-Context Audit Report (worker self-check; controller audit authoritative)

Wave: W37
Canonical audit path: docs/wave-reports/v2/opencode/W37_AUDIT_REPORT.md
Repository: mskomek/hpc-client-gui
Branch: develop
Tested implementation SHA: c8293d3ca309526ed250c794c3b294f7c54ef369 + W37 diff (src/hpc_gui/wx_settings.py, src/hpc_gui/wx_settings_view.py, src/hpc_gui/wx_shell.py APP-SETTINGS hunk, tests/test_w37_settings_persistence.py)
Audit scope: settings schema, persistence and plugin/provider settings (all 59 W37 owned IDs)
Audit verdict: PASS (worker fresh-context check; controller independent audit still required for close)

## Independence

This audit re-read the Wave spec, registry/TODO rows, mandatory source sections, and live code/tests at the tested SHA without reusing prior PASS text. Conclusions bind only to the tested SHA above.

## Requirement audit (all owned IDs verified via report trace)

- All 35 source-derived + 24 TODO-detail IDs carry IMPLEMENT with live owner → test → evidence in W37_WAVE_REPORT.md, except SOAK-LONG-001 which is truthfully EXTERNAL_BLOCKED (hours-scale packaged soak cannot run in-phase; resume point recorded; not claimed as done).
- No NOT_APPLICABLE_ACCEPTED without proof; no AWAITING_INPUT (all inputs present); no DEFERRED except the controller-scheduled soak (justified).
- Cross-Wave refs (W34/W38/W39/W40/W41) treated as hints only; no other Wave started/stopped/repaired/closed. DEF-W37-003 (sibling editor surface) routed, not opportunistically fixed.

## Evidence audit

- EV-W37-001 (31 passed), EV-W37-002 (GUI FULL event→storage→reopen + negative zero-OK), EV-W37-003 (87 + 5 + 36 regression green), EV-W37-004 (pre-existing editor-flow crash + sibling-owned assertion, both independent of the W37 diff) all record exact commands, exit codes, counts, and tested SHA. Discovery-only ops not used as execution proof. GUI FULL uses real wx 4.3.1 event/runtime + storage readback. No weakened tests, no new skips/xfails, no mock-of-unit-under-test (tmp config/plugin roots, MessageBox/error-report spies, one save_config failure injection — all legitimate boundaries).
- Diff review: `git diff --check` clean on owned files; owned diff limited to 3 product files (one hunk in wx_shell.py) + 1 test file; sibling dirty files preserved; no secrets/noise.
- Single-fix wave: one coherent persistence-wiring fix (DEF-W37-001/002 share one root cause and one evidence chain); routed/blocked items are not second fixes.

## Sub-gates

- Test-quality gate: PASS
- Evidence-identity gate: PASS (tested SHA recorded; candidate identity binds to c8293d3c + owned diff)
- Inventory completeness: PASS (8 key-level rows, all fields, 5 flags evaluated)
- Cross-document consistency: PASS (report/audit/tests agree; no competing canonical reports)
- No open P0/P1; no required PARTIAL.

## Verdict

AUDIT PASS (worker level). Controller must still run its fresh independent audit before close; this file does not replace it.


## Controller-persisted fresh independent audit — 2026-09-24T18:17:48.872754+00:00

- Wave: `W37`
- Normalized receipt: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-203154-ca45d2b7\0012-W37-audit-normalized.json`
- Phase log: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-203154-ca45d2b7\0012-W37-audit-opencode.log`
- Controller receipt status: `PASS`

The auditor executed independently; controller persistence is the durable artifact handoff.

```text
AC_WAVE_MODELS_LIST_EMPTY: 'opencode models --standalone' returned no entries; deferring to 'opencode run' fail-closed model validation for opencode-go/muse-spark-1.3-contributor

> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .opencode/protocol/WAVE_PROJECT_PROFILE.json 
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md 
✱ Glob "waves/**/W37*" 0 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves 
✱ Glob "**/W37.md" 0 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/pending 
→ Read waves/waves 
→ Read waves/done 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/pending/W37.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git rev-parse HEAD; echo ---SHA-END---; git status --porcelain=v1 | Select-Object -First 100; echo ---STATUS-END---; git log --oneline -5; echo ---LOG-END---

c8293d3ca309526ed250c794c3b294f7c54ef369
---SHA-END---
/usr/bin/bash: line 1: Select-Object: command not found
---STATUS-END---
c8293d3c Sync Agent Core runtime 21c15de7; align controller regression tests with canonical API
3e9635ba Sync Agent Core runtime fdd19ce1: provider quota wait, error-only failure classification
917f7916 Record Wave W19-W25 evidence, audit outputs and wave reports
d0d544c1 Wave W19-W25 product and test work (W26 editor identity in progress)
0d02da56 Ignore Agent Core skill quarantine and wave patch backups
---LOG-END---
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git status --porcelain=v1 | head -n 100; echo ---STATUS-END---; git diff --stat HEAD | head -n 100; echo ---DIFFSTAT-END---
M README.md
 M src/hpc_gui/docs/HELP_en.md
 M src/hpc_gui/docs/HELP_tr.md
 M src/hpc_gui/docs/PLUGINS_en.md
 M src/hpc_gui/docs/PLUGINS_tr.md
 M src/hpc_gui/i18n/en.json
 M src/hpc_gui/i18n/tr.json
 M src/hpc_gui/plugins/installer.py
 M src/hpc_gui/plugins/loader.py
 M src/hpc_gui/plugins/models.py
 M src/hpc_gui/plugins/validator.py
 M src/hpc_gui/services/files_ssh.py
 M src/hpc_gui/services/output_follower.py
 M src/hpc_gui/services/slurm_models.py
 M src/hpc_gui/ui/dialogs/plugin_manager_dialog.py
 M src/hpc_gui/wx_editor_view.py
 M src/hpc_gui/wx_jobs.py
 M src/hpc_gui/wx_plugins.py
 M src/hpc_gui/wx_plugins_view.py
 M src/hpc_gui/wx_settings.py
 M src/hpc_gui/wx_settings_view.py
 M src/hpc_gui/wx_shell.py
?? ".agent-legacy-backup (1)/"
?? NUL
?? artifacts/opencode/wave_W26/
?? artifacts/opencode/wave_W27/
?? artifacts/opencode/wave_W28/
?? artifacts/opencode/wave_W29/
?? artifacts/opencode/wave_W30/
?? artifacts/opencode/wave_W31/
?? artifacts/opencode/wave_W32/
?? artifacts/opencode/wave_W33/
?? artifacts/opencode/wave_W34/
?? artifacts/opencode/wave_W36/
?? artifacts/wave_W29/
?? artifacts/wave_W32/
?? artifacts/wave_W33/
?? artifacts/wave_W35/
?? docs/wave-reports/v2/opencode/W26_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W27_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W28_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W29_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W30_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W31_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W32_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W33_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W34_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W35_AUDIT_REPORT.md
?? docs/wave-reports/v2/opencode/W35_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W36_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W37_AUDIT_REPORT.md
?? docs/wave-reports/v2/opencode/W37_WAVE_REPORT.md
?? "new 4.ps1"
?? src/hpc_gui/plugins/discovery.py
?? src/hpc_gui/plugins/lifecycle.py
?? src/hpc_gui/plugins/providers.py
?? src/hpc_gui/plugins/settings.py
?? src/hpc_gui/services/job_identity.py
?? src/hpc_gui/services/job_list_filter_sort.py
?? src/hpc_gui/services/job_submit_cancel.py
?? src/hpc_gui/services/jobs_refresh_state.py
?? "tests/contracts (1)/"
?? "tests/contracts (2)/"
?? tests/test_w26_run_supplement.py
?? tests/test_w27_editor_conflicts.py
?? tests/test_w28_jobs_identity_refresh.py
?? tests/test_w29_job_outputs.py
?? tests/test_w30_submit_cancel.py
?? tests/test_w31_race_lifecycle.py
?? tests/test_w32_discovery_manifest.py
?? tests/test_w33_lifecycle_isolation.py
?? tests/test_w34_provider_settings.py
?? tests/test_w35_plugin_manager_gui.py
?? tests/test_w36_packaged_docs.py
?? tests/test_w37_settings_persistence.py
---STATUS-END---
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_en.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_tr.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/en.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/tr.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins_view.py', LF will be replaced by CRLF the next time Git touches it
 README.md                                       |   5 +-
 src/hpc_gui/docs/HELP_en.md                     |   3 +-
 src/hpc_gui/docs/HELP_tr.md                     |   4 +-
 src/hpc_gui/docs/PLUGINS_en.md                  |  65 +++-
 src/hpc_gui/docs/PLUGINS_tr.md                  |  62 +++-
 src/hpc_gui/i18n/en.json                        |  13 +-
 src/hpc_gui/i18n/tr.json                        |  13 +-
 src/hpc_gui/plugins/installer.py                |   7 +
 src/hpc_gui/plugins/loader.py                   |   7 +
 src/hpc_gui/plugins/models.py                   |   5 +
 src/hpc_gui/plugins/validator.py                |  99 +++++-
 src/hpc_gui/services/files_ssh.py               |  20 +-
 src/hpc_gui/services/output_follower.py         |   5 +
 src/hpc_gui/services/slurm_models.py            |  81 +++++
 src/hpc_gui/ui/dialogs/plugin_manager_dialog.py |   8 +
 src/hpc_gui/wx_editor_view.py                   | 306 ++++++++++++++++-
 src/hpc_gui/wx_jobs.py                          | 315 +++++++++++++++--
 src/hpc_gui/wx_plugins.py                       | 284 +++++++++++++++-
 src/hpc_gui/wx_plugins_view.py                  | 433 +++++++++++++++++++++---
 src/hpc_gui/wx_settings.py                      | 338 +++++++++++++++++-
 src/hpc_gui/wx_settings_view.py                 |  32 +-
 src/hpc_gui/wx_shell.py                         |  63 +++-
 22 files changed, 2026 insertions(+), 142 deletions(-)
---DIFFSTAT-END---
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read tests/test_w37_settings_persistence.py 
→ Read docs/wave-reports/v2/opencode/W37_WAVE_REPORT.md 
→ Read docs/wave-reports/v2/opencode/W37_AUDIT_REPORT.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -c "import hpc_gui.wx_settings as m; print('INVENTORY', len(m.SETTINGS_INVENTORY)); print('FLAGS', m.INVENTORY_FLAGS); print('GLOBAL', sorted(m.GLOBAL_STORAGE_KEYS.keys())); print('PROFILE', sorted(m.PROFILE_STORAGE_KEYS.keys())); print('LIVE', sorted(m.LIVE_APPLY_KEYS)); print('RESTART', m.RESTART_REQUIRED_KEYS); print('has_builder', hasattr(m,'build_model_from_storage')); print('has_persist', hasattr(m,'persist_model_snapshot')); print('has_load', hasattr(m,'load_persisted_snapshot'))"
echo ---IMPL-END---
git diff --check -- src/hpc_gui/wx_settings.py src/hpc_gui/wx_settings_view.py src/hpc_gui/wx_shell.py; echo "diff-check-exit:$?"
echo ---CHECK-END---
git diff --stat -- src/hpc_gui/wx_settings.py src/hpc_gui/wx_settings_view.py src/hpc_gui/wx_shell.py tests/test_w37_settings_persistence.py
echo ---STAT-END---
INVENTORY 8
FLAGS ('dead keys: none � every inventoried key has a named consumer above', 'duplicate sources of truth: none � transfer_parallelism single-sourced to profiles[] after v1.4.0 migration', 'implicit type coercion: none � storage getters coerce fail-closed to documented defaults; plugin validators reject mistyped values', 'UI default != runtime default: none � dialog controls initialize from the same storage getters the runtime consumes', 'core/plugin key collisions: none � plugin keys live under plugins.<id>.<key> and core keys are reject-listed')
GLOBAL ['jobs_outputs_refresh_interval', 'remote_directory_cache', 'shortcut_preferences', 'transfer_checksum']
PROFILE ['keepalive_interval_seconds', 'ssh_timeout', 'transfer_parallelism', 'x11_enabled']
LIVE ['jobs_outputs_refresh_interval', 'keepalive_interval_seconds', 'remote_directory_cache', 'shortcut_preferences', 'ssh_timeout', 'transfer_checksum', 'transfer_parallelism', 'x11_enabled']
RESTART frozenset()
has_builder True
has_persist True
has_load True
---IMPL-END---
diff-check-exit:0
---CHECK-END---
 src/hpc_gui/wx_settings.py      | 338 +++++++++++++++++++++++++++++++++++++++-
 src/hpc_gui/wx_settings_view.py |  32 +++-
 src/hpc_gui/wx_shell.py         |  63 +++++++-
 3 files changed, 417 insertions(+), 16 deletions(-)
---STAT-END---
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ PYTHONIOENCODING=utf-8 python -m pytest tests/test_w37_settings_persistence.py -q 2>&1 | tail -n 20; echo "EXIT:$?"
...............................                                          [100%]
31 passed in 2.02s
EXIT:0
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ PYTHONIOENCODING=utf-8 python -m pytest tests/test_wx_settings.py tests/test_config_storage_atomic.py tests/test_w03_settings_provider_inventory.py tests/test_w34_provider_settings.py tests/test_w35_plugin_manager_gui.py tests/test_w36_packaged_docs.py tests/test_connection_advanced_settings.py tests/test_live_tracking_settings.py tests/test_profile_storage_areas.py tests/test_profile_transfer_settings.py -q 2>&1 | tail -n 10; echo "EXIT:$?"
PYTHONIOENCODING=utf-8 python -m pytest tests/test_wx_shell.py tests/test_wx_dispatch_error_gov.py -q 2>&1 | tail -n 10; echo "EXIT:$?"
........................................................................ [ 82%]
...............                                                          [100%]
87 passed in 9.66s
EXIT:0
        assert "def save_remote(path, content)" in shell_src
        assert "files.write_text(path, content)" in shell_src
        # Local save: local filesystem through the editor view.
>       assert "Path(snapshot.path).write_text" in editor_src
E       assert 'Path(snapshot.path).write_text' in '"""Native wx editor adapter for the framework-neutral editor model."""\n\nfrom __future__ import annotations\n\nimpor...rsion)\n\n\n__all__ = ["show_editor", "build_editor_panel", "editor_binary_guard_reason", "BINARY_GUARD_SIZE_BYTES"]\n'

tests\test_wx_dispatch_error_gov.py:349: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_wx_dispatch_error_gov.py::test_editor_save__local_and_remote_paths_have_distinct_owners
1 failed, 41 passed in 6.08s
EXIT:0
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -c "import pathlib; txt=pathlib.Path('tests/test_w37_settings_persistence.py').read_text(encoding='utf-8'); print('skip:', txt.count('skip')); print('xfail:', txt.count('xfail')); print('mock_boundaries:', txt.count('monkeypatch')+txt.count('mock_patch')+txt.count('importorskip'))"
echo ---TQ-END---
git diff --name-only HEAD -- src/hpc_gui/wx_editor_view.py src/hpc_gui/wx_jobs.py src/hpc_gui/wx_plugins.py; echo ---SIBLING-END---
git diff --check; echo "full-diff-check:$?"
echo ---FULLCHECK-END---
python -c "import inspect; from hpc_gui import wx_shell; s=inspect.getsource(wx_shell._dispatch); i=s.find('APP-SETTINGS'); print(s[max(0,i-200):i+800])"
skip: 3
xfail: 0
mock_boundaries: 19
---TQ-END---
warning: in the working copy of 'src/hpc_gui/wx_plugins.py', LF will be replaced by CRLF the next time Git touches it
src/hpc_gui/wx_editor_view.py
src/hpc_gui/wx_jobs.py
src/hpc_gui/wx_plugins.py
---SIBLING-END---
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_en.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_tr.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/en.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/tr.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins_view.py', LF will be replaced by CRLF the next time Git touches it
full-diff-check:0
---FULLCHECK-END---
nd_id: str, parent=None, lifecycle=None, session_state=None) -> None:
    if command_id == "APP-HELP":
        from hpc_gui.wx_help import show_help

        show_help(parent)
    elif command_id == "APP-SETTINGS":
        from hpc_gui.wx_settings_view import show_settings
        try:
            # W37 SETTINGS-PERSIST-001: inject the real settings/profile
            # state plus a real persistence callback. Apply without
            # persistence is forbidden.
            from hpc_gui.wx_settings import build_model_from_storage, persist_model_snapshot
            _model = build_model_from_storage(
                apply=lambda snapshot: persist_model_snapshot(snapshot),
            )
            show_settings(parent=parent, model=_model)
        except Exception as exc:
            # W02 ERROR-GOV: a settings failure must be visible, never silent.
            report_wx_action_error(parent, area="SETTINGS", message_key="settings.open_failed", exc=exc)
    elif command_id == "APP-UPDAT
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -c "import pathlib,re; txt=pathlib.Path('tests/test_w37_settings_persistence.py').read_text(encoding='utf-8'); [print(repr(l)) for l in txt.splitlines() if 'skip' in l.lower()]"
'    wx = pytest.importorskip("wx")'
'    wx = pytest.importorskip("wx")'
'    wx = pytest.importorskip("wx")'
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
AC_WAVE_BRIDGE_STDOUT_BEGIN
Executing W37 audit — loading canonical skill and evidence.
Wave report and test inventory captured — now verifying implementation and evidence independently.
# W37 Audit — Fresh Independent Audit (opencode)

Wave: W37 — Settings schema, persistence and plugin/provider settings
Candidate: HEAD `c8293d3ca309526ed250c794c3b294f7c54ef369` + uncommitted W37 diff
Controller content_identity: `4685efb3155347bd0b9f027f208c0c22a08f4172ee3fd543450a0bf978e7cec7`
Audit mode: fresh-context, read-only for product code (no repairs made)

## Scope verified

- `waves/pending/W37.md` (35 source-derived + 24 TODO-detail IDs, evidence `GUI`, audit `fresh-independent`)
- `docs/wave-reports/v2/opencode/W37_WAVE_REPORT.md` (worker GO, pending audit)
- `docs/wave-reports/v2/opencode/W37_AUDIT_REPORT.md` (worker self-check only — not reused as authority)
- `tests/test_w37_settings_persistence.py` (31 tests, read in full)
- Live owners: `src/hpc_gui/wx_settings.py`, `src/hpc_gui/wx_settings_view.py`, `src/hpc_gui/wx_shell.py` (APP-SETTINGS hunk)

## Independent verification performed

1. **Implementation owners live**: `SETTINGS_INVENTORY` 8 rows, `INVENTORY_FLAGS` 5 evaluated, `GLOBAL_STORAGE_KEYS`/`PROFILE_STORAGE_KEYS` maps, `LIVE_APPLY_KEYS` 8 keys, `RESTART_REQUIRED_KEYS` empty (declared), `build_model_from_storage` / `persist_model_snapshot` / `load_persisted_snapshot` all present. Shell `_dispatch APP-SETTINGS` source confirmed to inject real builder + real callback with visible-error path.
2. **Focused suite**: `pytest tests/test_w37_settings_persistence.py -q` → **31 passed**, exit 0. Includes 2 GUI FULL wx tests (event→storage→readback + negative zero-OK).
3. **Regression**: 10-suite settings/profile/plugin batch → **87 passed**; `test_wx_shell.py` + `test_wx_dispatch_error_gov.py` → 41 passed + 1 failed on `test_editor_save__local_and_remote_paths_have_distinct_owners`, a source-text assertion against sibling-dirty `src/hpc_gui/wx_editor_view.py` (untouched by W37 diff) — identical to worker-routed DEF-W37-003. Correctly routed, not a W37 blocker.
4. **Diff review**: `git diff --check` on owned files clean; full-tree `git diff --check` clean; owned diff limited to 3 product files + 1 new test file; sibling dirty files (editor/jobs/plugins/services/docs/i18n) preserved, not opportunistically edited. No secrets, no generated/binary noise observed in owned hunks.
5. **Test quality**: no `skip`/`xfail` added (`skip` hits are 3× legitimate `pytest.importorskip("wx")` guards; wx present, GUI tests ran). Mocks limited to tmp config/plugin roots, MessageBox/error-report spies, one `save_config`/`os.replace` failure injection — legitimate boundaries. Negative controls (corruption matrix, write-failure, wrong-type, unknown-key, absent-plugin) assert fail-safe behavior.
6. **Dispositions**: all owned IDs carry IMPLEMENT with requirement→owner→test→evidence trace except `HPC-W09-TODO-SOAK-LONG-001` = truthful `EXTERNAL_BLOCKED` (hours-scale packaged soak cannot run in-phase; resume point recorded). No `AWAITING_INPUT`. Cross-Wave refs treated as hints only. Single coherent fix (DEF-W37-001/002 shared root cause); routed/blocked items are not second fixes.
7. **Evidence identity**: binds to tested SHA `c8293d3c` + owned W37 diff (exact files listed in report §Evidence). Commands, counts, exit codes recorded and re-proven by this audit.

## Verdict

All owned requirements met or truthfully blocked (soak only), required GUI evidence is real runtime proof, diff is clean and minimal, no open P0/P1 owned defects. Sibling failure is out-of-scope and correctly routed.

**AUDIT: PASS**

AC_WAVE_MACHINE_RESULT_BEGIN
WAVE_PHASE_STATUS: PASS
AC_WAVE_MACHINE_RESULT_END
```

WAVE_PHASE_STATUS: PASS
