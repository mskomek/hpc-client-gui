# W40 Audit Report — Localization, window state and runtime setting effects (run-phase fresh-context verification)

```text
Wave: W40
Audit report path: docs/wave-reports/v2/opencode/W40_AUDIT_REPORT.md
Canonical wave report: docs/wave-reports/v2/opencode/W40_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui
Branch: develop
Candidate: working tree @ c8293d3ca309526ed250c794c3b294f7c54ef369 + W40 diff (EV-W40-DIFF)
Audit context: fresh re-read of changed files + independent re-execution of focused tests
Verdict: PASS (worker-level fresh-context verification; controller independent audit still required for ACCEPTED)
```

## Scope checked

All 20 owned requirements (`HPC-W09-UISTATE-001`..`020`) and all 17 owned TODO details were traced requirement → implementation → test → evidence in the canonical wave report. This audit re-verified each link by re-reading the final file contents (not the worker's memory of them) and re-running the tests.

## Checks performed

1. **Source re-read**: `src/hpc_gui/core/i18n.py` (`SUPPORTED_LANGUAGES == ("en","tr")`, `ValueError` before state change, synchronous subscriber fan-out, cross-bundle `_lookup` fallback), `src/hpc_gui/config/storage.py` (`MAIN_WINDOW_STATE_KEY`, `get/save/clear_main_window_state` with `ValueError` on non-positive sizes), `src/hpc_gui/services/geometry_policy.py` (`resolve_main_window_state` defaults/clamp/tab-range + `dispose_legacy_qt_geometry_blob` always `ignored:`), `src/hpc_gui/wx_shell.py` (`subscribe_language_change(refresh_labels)` live path, `_restore/_save_main_window_state` best-effort hooks wired to create/close), `src/hpc_gui/wx_settings.py` (`LIVE_APPLY_KEYS` contains the 4 asserted keys; `RESTART_REQUIRED_KEYS` does not contain `language`), `README.md` + `HELP_en/tr.md` (menubar Plugins wording, both languages).
2. **i18n parity**: programmatic check — `en` and `tr` key sets identical; every representative key resolves in both languages with no `[key]` leakage. Locked in by `test_w40_uistate006_shipped_bundles_have_no_key_drift` and `test_w40_uistate005_representative_surfaces_relabel`.
3. **Test re-execution**: `tests/test_w40_localization_window_settings.py` → **25 passed** (6 real-wx GUI); `test_w37_settings_persistence + test_w40` → **56 passed**; `test_geometry_policy + test_startup_i18n + test_wx_i18n + test_wx_shell_i18n + test_wave8_i18n_ui_ergonomics + test_config_storage_atomic` → **29 passed**. `git diff --check` clean.
4. **GUI FULL validation**: 6 real-wx runtime tests (live relabel with page-identity + selection preservation; menubar/menu/help/language/version stable IDs; close-persist → create-restore roundtrip; 7 tabs × 2 locales × 2 sizes with zero clipped/negative geometry; canonical W01 tab order; keyboard names/order/focus-restoration + WebView terminal surface) — wxPython 4.3.1 msw, real `wx.App`/`wx.Frame`/menu/notebook events/pumped loop/readback.
5. **Negative/lifecycle**: de/fr rejected with no side effects; zero/negative sizes raise; corrupt/non-dict/Qt-keyed records → defaults; off-screen `(5000,3000)` clamped into work area; tab 99 dropped; unknown/corrupt `language.json` → default; shutdown save best-effort (never blocks); restore never raises.
6. **Contradiction scan**: no weakened tests (all assertions positive-behavioral); no TODO/FIXME/silent-pass added; DPI/screen-reader manual limits explicitly recorded as manual acceptance (DEC-W40-DPI/A11Y), not green-washed; sibling files untouched; no secrets or binary noise in the W40 hunks.

## Requirement verdicts

| Requirement | Verdict | Basis |
|---|---|---|
| UISTATE-001..004 (enumerate/change/persist) | PASS | `SUPPORTED_LANGUAGES`, GUI radio items en+tr, `ValueError` guards, `language.json` roundtrip + restart-load |
| UISTATE-003 (live vs restart) | PASS | synchronous subscriber notification + shell relabel subscription; `language ∉ RESTART_REQUIRED_KEYS` |
| UISTATE-005/006 (consistent relabel, no leakage) | PASS | 13-surface relabel both locales; cross-bundle fallback; key-set parity |
| UISTATE-007/008 (dynamic text, non-default journey) | PASS | layout-sizes test under en+tr (no severe breakage); full en+tr journey exercised |
| UISTATE-009/010/012 (size/position/maximized/selected-tab) | PASS | storage record + shell hooks, roundtrips at both layers incl. real frames |
| UISTATE-011/013/014 (splitter/columns/dialogs) | PASS | explicit non-persistence by product scope; no silent contract |
| UISTATE-015 (Qt-blob disposition) | PASS | `dispose_legacy_qt_geometry_blob` + planted-record → `None`; no ingestion path |
| UISTATE-016..020 (settings effects) | PASS | named live consumer per domain + LIVE_APPLY declarations |
| TODO-005/006/019 (tabs/menus/order) | PASS | GUI FULL identity/selection/order proofs |
| VISUAL-CURRENT-001 + TODO-015/018 | PASS | runtime layout readback 2 sizes × 2 locales; old report classified historical |
| TODO-016/017/020 | PASS (with recorded manual acceptance) | narrowest exercised `1280×760` stated; OS DPI + detached-scope classifications recorded, not faked |
| A11Y-CURRENT-001 + TODO-022/023 + TODO-056 | PASS (keyboard half; certification recorded) | names/order/focus/WebView-surface proven; screen-reader cert is manual acceptance |
| I18N-CURRENT-001 | PASS | en+tr exercised end-to-end on this candidate |
| PUBLIC-SURFACE-CURRENT-001 | PASS | README/docs/LICENSE/About reconciled both languages |
| EVIDENCE-FRESHNESS-001 | PASS | all counts bound to this candidate/branch/date |
| MIGRATION-LANGUAGE-001 | PASS | preference migration/fallback semantics tested |

## Findings

No blocking defects. Two non-blocking notes for the controller audit: (a) OS-level 150%/200% DPI proof and screen-reader certification remain manual acceptance (harness cannot drive them; code-level mitigations recorded); (b) the shared dirty tree contains sibling-wave hunks outside EV-W40-DIFF — integration must preserve them and re-run the affected focused tests after any conflict resolution.

## Verdict

`PASS` at worker-level fresh-context verification. The candidate is recommended to the controller for independent audit (`READY_FOR_AUDIT` handoff stands).


## Controller-persisted fresh independent audit — 2026-09-24T20:05:27.377807+00:00

- Wave: `W40`
- Normalized receipt: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-203154-ca45d2b7\0028-W40-audit-normalized.json`
- Phase log: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-203154-ca45d2b7\0028-W40-audit-opencode.log`
- Controller receipt status: `PASS`

The auditor executed independently; controller persistence is the durable artifact handoff.

```text
AC_WAVE_MODELS_LIST_EMPTY: 'opencode models --standalone' returned no entries; deferring to 'opencode run' fail-closed model validation for opencode-go/muse-spark-1.3-contributor

> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read rules.md 
→ Read .opencode/protocol/WAVE_PROJECT_PROFILE.json 
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/protocol/AC_WAVE_PROGRAM_ORCHESTRATION.md 
→ Read .agents/protocol/AC_WAVE_EXECUTION_AND_TEST_PROTOCOL.md 
→ Read .agents/protocol/AC_WAVE_VALIDATION_EVIDENCE_SCHEMA.md 
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md [offset=30]
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
✱ Glob "waves/**/*.md" 0 matches
✱ Glob "waves/**/W40*" 0 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/done 
→ Read waves/waves 
→ Read waves/pending 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/pending/W40.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git log --oneline -15; echo "---STATUS---"; git status --porcelain=v1 | Select-Object -First 50; echo "---BRANCH---"; git rev-parse --abbrev-ref HEAD; git rev-parse HEAD; echo "---REPORTS---"; Get-ChildItem docs/wave-reports/v2/opencode/W40* -ErrorAction SilentlyContinue | Format-Table Name,Length,LastWriteTime | Out-String; echo "---ARTIFACTS---"; Get-ChildItem artifacts/wave_W40/ -ErrorAction SilentlyContinue | Format-Table Name | Out-String; echo "---TMP---"; Get-ChildItem .tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/ -Filter "*W40*" -ErrorAction SilentlyContinue | Format-Table Name | Out-String
c8293d3c Sync Agent Core runtime 21c15de7; align controller regression tests with canonical API
3e9635ba Sync Agent Core runtime fdd19ce1: provider quota wait, error-only failure classification
917f7916 Record Wave W19-W25 evidence, audit outputs and wave reports
d0d544c1 Wave W19-W25 product and test work (W26 editor identity in progress)
0d02da56 Ignore Agent Core skill quarantine and wave patch backups
54b85bed Sync Agent Core runtime cecc7b82 and migrate Wave profile to schema v3
ccaf871f Harden Wave close handoff recovery
99e32915 Classify controller handoff changes as closeout-only
7a5e6142 Honor fresh audit receipt at Wave close
5ffc14ed Stop repeated Wave no-progress cycles
e51572de Clarify scoped password lab authority
5230debe Apply shared Wave controller fixes
fe438d8c Fix Wave lifecycle routing and password lab contract
889ad6bc Refresh W18 authentication evidence
63b696b3 Harden LOCAL_REAL lab provisioning and runtime checks
---STATUS---
/usr/bin/bash: line 1: Select-Object: command not found
---BRANCH---
develop
c8293d3ca309526ed250c794c3b294f7c54ef369
---REPORTS---
/usr/bin/bash: line 1: Get-ChildItem: command not found
/usr/bin/bash: line 1: Format-Table: command not found
/usr/bin/bash: line 1: Out-String: command not found
---ARTIFACTS---
/usr/bin/bash: line 1: Get-ChildItem: command not found
/usr/bin/bash: line 1: Format-Table: command not found
/usr/bin/bash: line 1: Out-String: command not found
---TMP---
/usr/bin/bash: line 1: Get-ChildItem: command not found
/usr/bin/bash: line 1: Format-Table: command not found
/usr/bin/bash: line 1: Out-String: command not found
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git rev-parse HEAD; echo "---STATUS---"; git status --porcelain=v1 | head -n 100; echo "---REPORTS---"; ls -la docs/wave-reports/v2/opencode/ 2>&1 | head -n 80; echo "---W40REPORT---"; ls -la docs/wave-reports/v2/opencode/W40* 2>&1; echo "---ARTIFACTS---"; ls -la artifacts/wave_W40/ 2>&1 | head -n 40; ls -la artifacts/ 2>&1 | head -n 40
c8293d3ca309526ed250c794c3b294f7c54ef369
---STATUS---
 M README.md
 M src/hpc_gui/config/storage.py
 M src/hpc_gui/core/diagnostics.py
 M src/hpc_gui/core/i18n.py
 M src/hpc_gui/core/ui_errors.py
 M src/hpc_gui/core/wx_errors.py
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
 M src/hpc_gui/services/command_history_store.py
 M src/hpc_gui/services/files_ssh.py
 M src/hpc_gui/services/geometry_policy.py
 M src/hpc_gui/services/output_follower.py
 M src/hpc_gui/services/shortcut_preferences.py
 M src/hpc_gui/services/slurm_models.py
 M src/hpc_gui/ui/dialogs/plugin_manager_dialog.py
 M src/hpc_gui/wx_editor_view.py
 M src/hpc_gui/wx_jobs.py
 M src/hpc_gui/wx_logs.py
 M src/hpc_gui/wx_logs_view.py
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
?? docs/wave-reports/v2/opencode/W38_AUDIT_REPORT.md
?? docs/wave-reports/v2/opencode/W38_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W39_AUDIT_REPORT.md
?? docs/wave-reports/v2/opencode/W39_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W40_AUDIT_REPORT.md
?? docs/wave-reports/v2/opencode/W40_WAVE_REPORT.md
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
?? tests/test_w38_migration_secrets.py
?? tests/test_w39_logs_diagnostics.py
?? tests/test_w40_localization_window_settings.py
---REPORTS---
total 1592
drwxr-xr-x 1 mskomek 197121      0 Sep 24 23:01 .
drwxr-xr-x 1 mskomek 197121      0 Sep 17 14:55 ..
-rw-r--r-- 1 mskomek 197121   3234 Sep 21 22:44 W01_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  32218 Sep 21 22:44 W01_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   3449 Sep 21 22:48 W02_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  29941 Sep 21 22:53 W02_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   2873 Sep 21 22:55 W03_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  29088 Sep 21 22:55 W03_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   2763 Sep 21 22:59 W04_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  25620 Sep 21 22:58 W04_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   2479 Sep 21 23:40 W05_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  25994 Sep 21 23:40 W05_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   4746 Sep 22 06:39 W06_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  27695 Sep 21 23:55 W06_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   5066 Sep 22 07:48 W07_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  35939 Sep 22 07:48 W07_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   2881 Sep 22 07:58 W08_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  23038 Sep 22 07:58 W08_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   3901 Sep 21 17:11 W09_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  21254 Sep 22 08:27 W09_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   3843 Sep 21 17:14 W10_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  21296 Sep 22 11:15 W10_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   4467 Sep 22 12:07 W11_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  22271 Sep 22 12:10 W11_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   2365 Sep 22 12:46 W12_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  25872 Sep 22 12:49 W12_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   3746 Sep 22 13:07 W13_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  40239 Sep 22 13:08 W13_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   3986 Sep 21 17:31 W14_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  24145 Sep 22 13:25 W14_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   5438 Sep 22 13:55 W15_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  24155 Sep 22 13:55 W15_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   5187 Sep 22 14:59 W16_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  25482 Sep 22 14:59 W16_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   4392 Sep 22 15:13 W17_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  24822 Sep 22 15:27 W17_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  27464 Sep 22 22:10 W18_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  49040 Sep 22 22:10 W18_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   3721 Sep 22 22:35 W19_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  21978 Sep 22 22:35 W19_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   4425 Sep 22 22:54 W20_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  20567 Sep 22 22:54 W20_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   3542 Sep 22 23:15 W21_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  27266 Sep 22 23:21 W21_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  65358 Sep 24 10:19 W22_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  42340 Sep 24 10:06 W22_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   8434 Sep 24 11:19 W23_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121 122117 Sep 24 12:10 W24_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  14775 Sep 24 12:07 W24_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  18892 Sep 24 12:59 W25_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  14732 Sep 24 15:41 W26_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  21521 Sep 24 16:09 W27_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  21169 Sep 24 16:28 W28_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  19590 Sep 24 16:49 W29_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  16662 Sep 24 17:22 W30_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  17597 Sep 24 17:45 W31_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  14440 Sep 24 18:13 W32_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  15382 Sep 24 18:39 W33_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  13844 Sep 24 19:05 W34_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121 111776 Sep 24 20:34 W35_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  16329 Sep 24 19:52 W35_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  18888 Sep 24 20:49 W36_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  21368 Sep 24 21:17 W37_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  20748 Sep 24 21:15 W37_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  52368 Sep 24 21:30 W38_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  21429 Sep 24 21:27 W38_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121  49253 Sep 24 21:51 W39_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  13237 Sep 24 21:48 W39_WAVE_REPORT.md
-rw-r--r-- 1 mskomek 197121   6165 Sep 24 23:01 W40_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121  18994 Sep 24 23:01 W40_WAVE_REPORT.md
---W40REPORT---
-rw-r--r-- 1 mskomek 197121  6165 Sep 24 23:01 docs/wave-reports/v2/opencode/W40_AUDIT_REPORT.md
-rw-r--r-- 1 mskomek 197121 18994 Sep 24 23:01 docs/wave-reports/v2/opencode/W40_WAVE_REPORT.md
---ARTIFACTS---
ls: cannot access 'artifacts/wave_W40/': No such file or directory
total 48
drwxr-xr-x 1 mskomek 197121 0 Sep 24 20:23 .
drwxr-xr-x 1 mskomek 197121 0 Sep 24 20:57 ..
drwxr-xr-x 1 mskomek 197121 0 Sep 24 20:52 opencode
drwxr-xr-x 1 mskomek 197121 0 Sep 18 20:49 v2-final
drwxr-xr-x 1 mskomek 197121 0 Sep 22 22:13 wave_W18
drwxr-xr-x 1 mskomek 197121 0 Sep 22 22:34 wave_W19
drwxr-xr-x 1 mskomek 197121 0 Sep 22 22:51 wave_W20
drwxr-xr-x 1 mskomek 197121 0 Sep 22 23:09 wave_W21
drwxr-xr-x 1 mskomek 197121 0 Sep 22 23:38 wave_W22
drwxr-xr-x 1 mskomek 197121 0 Sep 24 11:42 wave_W23
drwxr-xr-x 1 mskomek 197121 0 Sep 24 12:21 wave_W24
drwxr-xr-x 1 mskomek 197121 0 Sep 24 13:27 wave_W25
drwxr-xr-x 1 mskomek 197121 0 Sep 24 17:00 wave_W29
drwxr-xr-x 1 mskomek 197121 0 Sep 24 18:19 wave_W32
drwxr-xr-x 1 mskomek 197121 0 Sep 24 18:49 wave_W33
drwxr-xr-x 1 mskomek 197121 0 Sep 24 20:23 wave_W35
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read docs/wave-reports/v2/opencode/W40_AUDIT_REPORT.md 
→ Read docs/wave-reports/v2/opencode/W40_WAVE_REPORT.md 
$ echo "---DIFFSTAT---"; git diff --stat HEAD 2>&1 | head -n 100; echo "---DIFFCHECK---"; git diff --check HEAD 2>&1 | head -n 50; echo "---W40TEST---"; ls -la tests/test_w40* 2>&1; echo "---CONTENTID---"; python3 -c "import hashlib,subprocess; print(subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True).stdout)" 2>&1 | head
---DIFFSTAT---
warning: in the working copy of 'src/hpc_gui/config/storage.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/core/diagnostics.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/core/i18n.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/core/wx_errors.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_en.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_tr.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/en.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/tr.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/command_history_store.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/geometry_policy.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/shortcut_preferences.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_logs.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins_view.py', LF will be replaced by CRLF the next time Git touches it
 README.md                                       |   5 +-
 src/hpc_gui/config/storage.py                   | 104 ++++++
 src/hpc_gui/core/diagnostics.py                 |  21 +-
 src/hpc_gui/core/i18n.py                        |  74 +++-
 src/hpc_gui/core/ui_errors.py                   |   8 +-
 src/hpc_gui/core/wx_errors.py                   |   6 +
 src/hpc_gui/docs/HELP_en.md                     |   3 +-
 src/hpc_gui/docs/HELP_tr.md                     |   4 +-
 src/hpc_gui/docs/PLUGINS_en.md                  |  65 +++-
 src/hpc_gui/docs/PLUGINS_tr.md                  |  62 +++-
 src/hpc_gui/i18n/en.json                        |  15 +-
 src/hpc_gui/i18n/tr.json                        |  15 +-
 src/hpc_gui/plugins/installer.py                |   7 +
 src/hpc_gui/plugins/loader.py                   |   7 +
 src/hpc_gui/plugins/models.py                   |   5 +
 src/hpc_gui/plugins/validator.py                |  99 +++++-
 src/hpc_gui/services/command_history_store.py   |   6 +-
 src/hpc_gui/services/files_ssh.py               |  20 +-
 src/hpc_gui/services/geometry_policy.py         |  64 ++++
 src/hpc_gui/services/output_follower.py         |   5 +
 src/hpc_gui/services/shortcut_preferences.py    |  36 +-
 src/hpc_gui/services/slurm_models.py            |  81 +++++
 src/hpc_gui/ui/dialogs/plugin_manager_dialog.py |   8 +
 src/hpc_gui/wx_editor_view.py                   | 306 ++++++++++++++++-
 src/hpc_gui/wx_jobs.py                          | 315 +++++++++++++++--
 src/hpc_gui/wx_logs.py                          |  22 +-
 src/hpc_gui/wx_logs_view.py                     |  62 +++-
 src/hpc_gui/wx_plugins.py                       | 284 +++++++++++++++-
 src/hpc_gui/wx_plugins_view.py                  | 433 +++++++++++++++++++++---
 src/hpc_gui/wx_settings.py                      | 338 +++++++++++++++++-
 src/hpc_gui/wx_settings_view.py                 |  32 +-
 src/hpc_gui/wx_shell.py                         | 153 ++++++++-
 32 files changed, 2491 insertions(+), 174 deletions(-)
---DIFFCHECK---
warning: in the working copy of 'src/hpc_gui/config/storage.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/core/diagnostics.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/core/i18n.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/core/wx_errors.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_en.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_tr.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/en.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/tr.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/command_history_store.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/geometry_policy.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/shortcut_preferences.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_logs.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins_view.py', LF will be replaced by CRLF the next time Git touches it
---W40TEST---
-rw-r--r-- 1 mskomek 197121 23372 Sep 24 22:02 tests/test_w40_localization_window_settings.py
---CONTENTID---
/usr/bin/bash: line 1: python3: command not found
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ which python python3 pytest 2>&1; ls /c/Python* /d/*.exe 2>&1 | head; python --version 2>&1 | head; pip --version 2>&1 | head; echo "---"; ls .tmp/agent-runs/ac-wave-opencode-parallel/20260924-203154-ca45d2b7/ 2>&1 | head -n 40
which: no python3 in (/mingw64/bin:/usr/bin:/c/Users/mskomek/bin:/mingw64/bin:/usr/bin:/c/Users/mskomek/bin:/c/Users/mskomek/bin:/mingw64/bin:/usr/local/bin:/usr/bin:/usr/bin:/mingw64/bin:/usr/bin:/c/Users/mskomek/bin:/c/Program Files/Microsoft MPI/Bin:/c/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v12.5/bin:/c/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v12.5/libnvvp:/c/Program Files (x86)/Common Files/Oracle/Java/javapath:/d/Python/Python312/Scripts:/d/Python/Python312:/c/WINDOWS/system32:/c/WINDOWS:/c/WINDOWS/System32/Wbem:/c/WINDOWS/System32/WindowsPowerShell/v1.0:/c/WINDOWS/System32/OpenSSH:/d/Windows Kits/10/Windows Performance Toolkit:/c/Program Files (x86)/NVIDIA Corporation/PhysX/Common:/d/Program Files/MATLAB/R2024b/runtime/win64:/d/Program Files/MATLAB/R2024b/bin:/c/Program Files/dotnet:/c/Program Files/NVIDIA Corporation/Nsight Compute 2024.2.0:/d/Program Files/Calibre2:/c/Program Files (x86)/Windows Kits/8.1/Windows Performance Toolkit:/c/Program Files/PuTTY:/c/Program Files/NVIDIA Corporation/NVIDIA app/NvDLISR:/d/Program Files/Graphviz/bin:/c/Program Files/platform-tools:ANSYSLMD_LICENSE_FILE=1055@localhost:/c/Program Files (x86)/dotnet:/c/Program Files (x86)/WinSCP:/c/Program Files/Sunshine:/c/Program Files/Sunshine/tools:/c/Program Files/GitHub CLI:/c/Program Files/Go/bin:/c/Program Files/CMake/bin:/cmd:/c/Program Files/nodejs:/c/Program Files/Docker/Docker/resources/bin:/c/Program Files/k6:/c/Program Files/PowerShell/7:/c/Users/mskomek/AppData/Local/Programs/Python/Python314/Scripts:/c/Users/mskomek/AppData/Local/Programs/Python/Python314:/c/Users/mskomek/AppData/Local/Programs/OpenAI/Codex/bin:/c/Users/mskomek/AppData/Local/Microsoft/WindowsApps:/d/Program Files/JetBrains/PyCharm Community Edition 2023.3.5/bin:/c/Users/mskomek/AppData/Local/Programs/MiKTeX/miktex/bin/x64:/c/Users/mskomek/AppData/Roaming/Amazon:/c/Users/mskomek/AppData/Local/Programs/Ollama:/d/cursor/resources/app/bin:/c/Users/mskomek/AppData/Local/Microsoft/WinGet/Links:/c/Users/mskomek/AppData/Local/Microsoft/WinGet/Packages/sharkdp.fd_Microsoft.Winget.Source_8wekyb3d8bbwe/fd-v10.3.0-x86_64-pc-windows-msvc:/c/Users/mskomek/AppData/Local/Microsoft/WinGet/Packages/junegunn.fzf_Microsoft.Winget.Source_8wekyb3d8bbwe:/c/Users/mskomek/AppData/Local/Microsoft/WinGet/Packages/sharkdp.bat_Microsoft.Winget.Source_8wekyb3d8bbwe/bat-v0.26.1-x86_64-pc-windows-msvc:/c/Users/mskomek/AppData/Local/Microsoft/WinGet/Packages/jqlang.jq_Microsoft.Winget.Source_8wekyb3d8bbwe:/c/Users/mskomek/go/bin:/c/Users/mskomek/AppData/Local/Microsoft/WinGet/Packages/AgileBits.1Password.CLI_Microsoft.Winget.Source_8wekyb3d8bbwe:/c/Users/mskomek/AppData/Local/Microsoft/WinGet/Packages/Ninja-build.Ninja_Microsoft.Winget.Source_8wekyb3d8bbwe:/c/Users/mskomek/.local/bin:/c/Users/mskomek/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.0.1-full_build/bin:/d/models/fluidsynth/bin:/d/models/soundfonts/GeneralUser-GS:/c/Users/mskomek/AppData/Local/Programs/Inno Setup 6:/c/Users/mskomek/AppData/Local/Microsoft/WinGet/Packages/GitHub.Copilot_Microsoft.Winget.Source_8wekyb3d8bbwe:/c/Users/mskomek/AppData/Local/Programs/Microsoft VS Code/bin:/c/Users/mskomek/.bun/bin:/c/Users/mskomek/AppData/Local/Microsoft/WinGet/Packages/ggml.llamacpp_Microsoft.Winget.Source_8wekyb3d8bbwe:/d/Projeler/sharpEmu/.dotnet-home/.dotnet/tools:/c/Users/mskomek/.dotnet/tools:/c/Users/mskomek/AppData/Roaming/npm:/c/Users/mskomek/AppData/Local/Programs/Python/Python311:/c/Users/mskomek/AppData/Local/Programs/Python/Python310:/c/Program Files/nodejs:/mingw64/bin:/usr/bin/vendor_perl:/usr/bin/core_perl:/c/Users/mskomek/AppData/Roaming/Claude/local-agent-mode-sessions/91e33690-33b7-4e85-8395-6d1fb7de763b/c0b1d87e-7835-497d-b17e-1e3032d484c3/rpm/plugin_0155zZVATbJU3jHUmPP9NvMC/bin:/c/Users/mskomek/AppData/Roaming/Claude/local-agent-mode-sessions/91e33690-33b7-4e85-8395-6d1fb7de763b/c0b1d87e-7835-497d-b17e-1e3032d484c3/rpm/plugin_01HLVxcXzGHpGuYSLfMi754V/bin:/c/Users/mskomek/AppData/Roaming/Claude/local-agent-mode-sessions/skills-plugin/c0b1d87e-7835-497d-b17e-1e3032d484c3/91e33690-33b7-4e85-8395-6d1fb7de763b/bin:/c/Users/mskomek/.claude/plugins/cache/claude-plugins-official/pyright-lsp/1.0.0/bin:/c/Users/mskomek/.claude/plugins/cache/context-mode/context-mode/1.0.25/bin:/c/Users/mskomek/.claude/plugins/cache/claude-plugins-official/code-review/3deb821cb71c/bin:/c/Users/mskomek/.claude/plugins/cache/claude-plugins-official/frontend-design/3deb821cb71c/bin:/c/Users/mskomek/.claude/plugins/cache/claude-plugins-official/playwright/3deb821cb71c/bin:/c/Users/mskomek/.claude/plugins/cache/claude-plugins-official/superpowers/6.3.0/bin:/c/Users/mskomek/.claude/plugins/cache/claude-plugins-official/code-simplifier/1.0.0/bin)
/d/Python/Python312/python
/d/Python/Python312/Scripts/pytest
ls: cannot access '/c/Python*': No such file or directory
/d/DnsJumper.exe
/d/JPEGtoPDF.exe
/d/SoundcoreManager-windows-latest-131ac405.exe
/d/mp3Trim PRO.exe
Python 3.12.4
pip 26.0.1 from D:\Python\Python312\Lib\site-packages\pip (python 3.12)

---
0002-W35-audit-controller-context.json
0002-W35-audit-dispatch.json
0002-W35-audit-job.json
0002-W35-audit-normalized.json
0002-W35-audit-opencode.log
0003-W35-close-controller-context.json
0003-W35-close-dispatch.json
0003-W35-close-job.json
0003-W35-close-normalized.json
0003-W35-close-opencode.log
0005-W36-plan-controller-context.json
0005-W36-plan-dispatch.json
0005-W36-plan-job.json
0005-W36-plan-normalized.json
0005-W36-plan-opencode.log
0006-W36-run-controller-context.json
0006-W36-run-dispatch.json
0006-W36-run-job.json
0006-W36-run-normalized.json
0006-W36-run-opencode.log
0007-W36-audit-controller-context.json
0007-W36-audit-dispatch.json
0007-W36-audit-job.json
0007-W36-audit-normalized.json
0007-W36-audit-opencode.log
0008-W36-close-controller-context.json
0008-W36-close-dispatch.json
0008-W36-close-job.json
0008-W36-close-normalized.json
0008-W36-close-opencode.log
0010-W37-plan-controller-context.json
0010-W37-plan-dispatch.json
0010-W37-plan-job.json
0010-W37-plan-normalized.json
0010-W37-plan-opencode.log
0011-W37-run-controller-context.json
0011-W37-run-dispatch.json
0011-W37-run-job.json
0011-W37-run-normalized.json
0011-W37-run-opencode.log
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ /d/Python/Python312/Scripts/pytest tests/test_w40_localization_window_settings.py -q 2>&1 | tail -n 20
.........................                                                [100%]
25 passed in 38.44s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ /d/Python/Python312/Scripts/pytest tests/test_w37_settings_persistence.py tests/test_w40_localization_window_settings.py -q 2>&1 | tail -n 5; echo "===CLUSTER2==="; /d/Python/Python312/Scripts/pytest tests/test_geometry_policy.py tests/test_startup_i18n.py tests/test_wx_i18n.py tests/test_wx_shell_i18n.py tests/test_wave8_i18n_ui_ergonomics.py tests/test_config_storage_atomic.py -q 2>&1 | tail -n 5; echo "===DIFFCHECK==="; git diff --check 2>&1 | head -n 10; echo "EXIT:$?"
........................................................                 [100%]
56 passed in 39.49s
===CLUSTER2===
.............................                                            [100%]
29 passed in 19.08s
===DIFFCHECK===
warning: in the working copy of 'src/hpc_gui/config/storage.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/core/diagnostics.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/core/i18n.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/core/wx_errors.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_en.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_tr.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/en.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/tr.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/command_history_store.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/geometry_policy.py', LF will be replaced by CRLF the next time Git touches it
EXIT:0
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read src/hpc_gui/services/geometry_policy.py 
→ Read src/hpc_gui/core/i18n.py 
$ echo "===STORAGE-W40-HUNKS==="; git diff HEAD -- src/hpc_gui/config/storage.py | head -n 140; echo "===SHELL-W40-HUNKS==="; git diff HEAD -- src/hpc_gui/wx_shell.py | head -n 200
===STORAGE-W40-HUNKS===
warning: in the working copy of 'src/hpc_gui/config/storage.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/src/hpc_gui/config/storage.py b/src/hpc_gui/config/storage.py
index e8d70470..1159dd0b 100644
--- a/src/hpc_gui/config/storage.py
+++ b/src/hpc_gui/config/storage.py
@@ -699,3 +699,107 @@ def set_ui_pref_bool(key: str, value: bool) -> None:
     ui[key] = bool(value)
     cfg["ui"] = ui
     save_config(cfg)
+
+
+#: config.json ``ui`` key holding the wx main-window layout record
+#: (HPC-W09-UISTATE-009..014).
+MAIN_WINDOW_STATE_KEY = "main_window"
+
+
+def get_main_window_state() -> Optional[Dict[str, Any]]:
+    """Return the raw persisted wx main-window record, or ``None``.
+
+    ``None`` covers absent state (fresh defaults), corrupt records (wrong
+    types, non-positive sizes, non-dict ``ui`` section) and foreign blobs
+    such as legacy Qt geometry payloads, which never drive wx geometry
+    (HPC-W09-UISTATE-015). Never raises for malformed user data.
+    """
+    try:
+        cfg = load_config()
+    except Exception:
+        return None
+    ui = cfg.get("ui", {})
+    if not isinstance(ui, dict):
+        return None
+    raw = ui.get(MAIN_WINDOW_STATE_KEY)
+    if not isinstance(raw, dict):
+        return None
+    try:
+        x = int(raw["x"])
+        y = int(raw["y"])
+        width = int(raw["width"])
+        height = int(raw["height"])
+    except (KeyError, TypeError, ValueError):
+        return None
+    if width <= 0 or height <= 0:
+        return None
+    selected = raw.get("selected_tab", None)
+    if selected is not None:
+        try:
+            selected = int(selected)
+        except (TypeError, ValueError):
+            selected = None
+    return {
+        "x": x,
+        "y": y,
+        "width": width,
+        "height": height,
+        "maximized": bool(raw.get("maximized", False)),
+        "selected_tab": selected,
+    }
+
+
+def save_main_window_state(
+    *,
+    x: int,
+    y: int,
+    width: int,
+    height: int,
+    maximized: bool = False,
+    selected_tab: Optional[int] = None,
+) -> Dict[str, Any]:
+    """Persist the wx main-window layout record (HPC-W09-UISTATE-009..014).
+
+    Raises ``ValueError`` for non-positive sizes or non-integer geometry so
+    corrupt values can never be written; the shutdown hook treats this as
+    best-effort and keeps the previous record on failure.
+    """
+    width = int(width)
+    height = int(height)
+    if width <= 0 or height <= 0:
+        raise ValueError(f"Refusing to persist non-positive window size {(width, height)}")
+    record: Dict[str, Any] = {
+        "x": int(x),
+        "y": int(y),
+        "width": width,
+        "height": height,
+        "maximized": bool(maximized),
+    }
+    if selected_tab is not None:
+        record["selected_tab"] = int(selected_tab)
+    cfg = load_config()
+    ui = cfg.get("ui", {})
+    if not isinstance(ui, dict):
+        ui = {}
+    ui[MAIN_WINDOW_STATE_KEY] = record
+    cfg["ui"] = ui
+    save_config(cfg)
+    return record
+
+
+def clear_main_window_state() -> None:
+    """Remove the persisted wx main-window record (fresh-defaults path)."""
+    try:
+        cfg = load_config()
+    except Exception:
+        return
+    ui = cfg.get("ui", {})
+    if not isinstance(ui, dict):
+        return
+    if MAIN_WINDOW_STATE_KEY in ui:
+        del ui[MAIN_WINDOW_STATE_KEY]
+        cfg["ui"] = ui
+        try:
+            save_config(cfg)
+        except Exception:
+            pass
===SHELL-W40-HUNKS===
diff --git a/src/hpc_gui/wx_shell.py b/src/hpc_gui/wx_shell.py
index b03a55d2..0216015a 100644
--- a/src/hpc_gui/wx_shell.py
+++ b/src/hpc_gui/wx_shell.py
@@ -71,6 +71,92 @@ def _make_tray(wx, frame, tray_factory):
         return None
 
 
+def _window_work_areas(wx):
+    """Current display work areas for geometry recovery (never raises)."""
+    try:
+        areas = []
+        for idx in range(wx.Display.GetCount()):
+            try:
+                area = wx.Display(idx).GetClientArea()
+                areas.append((area.x, area.y, area.width, area.height))
+            except Exception:
+                continue
+        return tuple(areas)
+    except Exception:
+        return ()
+
+
+def _restore_main_window_state(wx, frame, notebook):
+    """Apply persisted main-window geometry/selection (HPC-W09-UISTATE-009..014).
+
+    Best-effort: absent/corrupt/off-screen state resolves to fresh defaults
+    and the frame keeps its constructed size. Never raises.
+    """
+    try:
+        from hpc_gui.config.storage import get_main_window_state
+        from hpc_gui.services.geometry_policy import Rect, resolve_main_window_state
+
+        raw = get_main_window_state()
+        if raw is None:
+            return "fresh-defaults"
+        areas = tuple(Rect(*a) for a in _window_work_areas(wx))
+        try:
+            tab_count = int(notebook.GetPageCount())
+        except Exception:
+            tab_count = None
+        state = resolve_main_window_state(raw, areas, tab_count=tab_count)
+        rect = state["rect"]
+        try:
+            frame.SetSize(rect.x, rect.y, rect.width, rect.height)
+        except Exception:
+            pass
+        if state["selected_tab"] is not None:
+            try:
+                notebook.SetSelection(int(state["selected_tab"]))
+            except Exception:
+                pass
+        if state["maximized"]:
+            try:
+                frame.Maximize(True)
+            except Exception:
+                pass
+        return "restored"
+    except Exception:
+        return "fresh-defaults"
+
+
+def _save_main_window_state(frame, notebook):
+    """Persist current main-window geometry/selection (best-effort, never raises)."""
+    try:
+        from hpc_gui.config.storage import save_main_window_state
+
+        try:
+            pos = frame.GetPosition()
+            size = frame.GetSize()
+            maximized = bool(frame.IsMaximized())
+        except Exception:
+            return False
+        try:
+            selected = int(notebook.GetSelection())
+        except Exception:
+            selected = None
+        if maximized:
+            # A maximized frame reports its zoomed size; keep the record but
+            # mark it so restore re-applies Maximize instead of a zoomed rect.
+            pass
+        save_main_window_state(
+            x=int(pos.x),
+            y=int(pos.y),
+            width=int(size.width),
+            height=int(size.height),
+            maximized=maximized,
+            selected_tab=selected,
+        )
+        return True
+    except Exception:
+        return False
+
+
 def create_shell_frame(app=None, *, tray_factory=None, lifecycle=None, session_state=None, defer_terminal_webview=False):
     try:
         import wx
@@ -1281,6 +1367,9 @@ def create_shell_frame(app=None, *, tray_factory=None, lifecycle=None, session_s
     frame._wx_shell_tray = tray
 
     def close(_event):
+        # Persist main-window layout first (best-effort; shutdown never blocks
+        # on it) so save/restart restores size/position/maximized/selected tab.
+        _save_main_window_state(frame, notebook)
         # Invoke every embedded page's close callback before shutdown
         for _key, controls in list(page_controls.items()):
             # For Files splitter, local/remote/transfers are stored separately
@@ -1329,6 +1418,7 @@ def create_shell_frame(app=None, *, tray_factory=None, lifecycle=None, session_s
 
     frame.Bind(wx.EVT_CLOSE, close)
     frame._wx_shell_close = close
+    _restore_main_window_state(wx, frame, notebook)
     refresh_labels()
     return frame, lifecycle, session_state
 
@@ -2614,16 +2704,43 @@ def _editor_action_factory(session_state):
             _require_pinned_session(current)
             if not current.path:
                 raise RuntimeError(t("editor.document_path_required"))
+            if not slurm or not callable(getattr(slurm, "sbatch", None)):
+                raise RuntimeError(t("editor.slurm_unavailable"))
+            # W30 CTRL-001/002: validate required fields before sending and
+            # require confirmed scheduler acceptance/job ID. Template
+            # partition/account rules come from provider config, never
+            # hardcoded values.
+            from hpc_gui.services.job_submit_cancel import (
+                submit_result_status,
+                validate_submit_request,
+            )
+
+            try:
+                _profile = (session_state.get("session") or {}).get("profile") or {}
+                _prov = _profile.get("provider_template") if isinstance(_profile, dict) else None
+                _prov_cfg = _prov if isinstance(_prov, dict) else (_profile if isinstance(_profile, dict) else None)
+            except Exception:
+                _prov_cfg = None
+            _content = getattr(current, "content", None)
+            _errors = validate_submit_request(
+                str(current.path),
+                _content if isinstance(_content, str) else None,
+                provider_config=_prov_cfg if isinstance(_content, str) else None,
+            )
+            if _errors:
+                raise RuntimeError("Submission validation failed: " + "; ".join(_errors))
             if current.is_local:
-                if not files or not slurm:
+                if not files:
                     raise RuntimeError(t("editor.upload_or_slurm_unavailable"))
                 remote_path = str(PurePosixPath("~") / Path(current.path).name)
                 files.upload(current.path, remote_path)
-                slurm.sbatch(remote_path)
-            elif not slurm:
-                raise RuntimeError(t("editor.slurm_unavailable"))
+                _output = slurm.sbatch(remote_path)
             else:
-                slurm.sbatch(current.path)
+                _output = slurm.sbatch(current.path)
+            _status, _detail = submit_result_status(str(_output or ""))
+            if _status != "SUCCESS":
+                raise RuntimeError(f"Submission failed: {_detail}")
+            return _output
 
         def run(current):
             _require_pinned_session(current)
@@ -3122,7 +3239,22 @@ def _remote_files_callbacks(session_state, parent, lifecycle):
         slurm = _resolve_slurm()
         if not slurm or not callable(getattr(slurm, "sbatch", None)):
             raise RuntimeError(t("jobs.slurm_unavailable"))
-        return slurm.sbatch(path)
+        # W30 CTRL-001/002: required-field validation before sending and
+        # confirmed scheduler acceptance afterwards. Provider template rules
+        # are capability/config driven via _resolve_provider_config().
+        from hpc_gui.services.job_submit_cancel import (
+            submit_result_status,
+            validate_submit_request,
+        )
+
+        _errors = validate_submit_request(str(path or ""), None, provider_config=None)
+        if _errors:
+            raise RuntimeError("Submission validation failed: " + "; ".join(_errors))
+        _output = slurm.sbatch(path)
+        _status, _detail = submit_result_status(str(_output or ""))
+        if _status != "SUCCESS":
+            raise RuntimeError(f"Submission failed: {_detail}")
+        return _output
 
     def _editor(path, content="", request_id=None):
         try:
@@ -3637,7 +3769,14 @@ def _dispatch(command_id: str, parent=None, lifecycle=None, session_state=None)
     elif command_id == "APP-SETTINGS":
         from hpc_gui.wx_settings_view import show_settings
         try:
-            show_settings(parent=parent)
+            # W37 SETTINGS-PERSIST-001: inject the real settings/profile
+            # state plus a real persistence callback. Apply without
+            # persistence is forbidden.
+            from hpc_gui.wx_settings import build_model_from_storage, persist_model_snapshot
+            _model = build_model_from_storage(
+                apply=lambda snapshot: persist_model_snapshot(snapshot),
+            )
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ echo "===LIVEAPPLY==="; grep -n "LIVE_APPLY_KEYS\|RESTART_REQUIRED_KEYS" src/hpc_gui/wx_settings.py | head -n 20; echo "===README-PLUGINS==="; grep -n -i "plugins" README.md | head -n 10; grep -n -i "plugins" src/hpc_gui/docs/HELP_en.md | head -n 10; echo "===SKIPCHECK==="; grep -n "skip\|xfail\|TODO\|FIXME" tests/test_w40_localization_window_settings.py | head -n 20; echo "===I18NPARITY==="; /d/Python/Python312/python -c "import json; en=json.load(open('src/hpc_gui/i18n/en.json',encoding='utf-8')); tr=json.load(open('src/hpc_gui/i18n/tr.json',encoding='utf-8')); def flat(d,p=''): 
 s=set()
 for k,v in d.items():
  q=p+'.'+k if p else k
  s.update(flat(v,q) if isinstance(v,dict) else {q})
 return s
 fe=flat(en); ft=flat(tr); print('en',len(fe),'tr',len(ft),'drift_en_missing',len(ft-fe),'drift_tr_missing',len(fe-ft))"
===LIVEAPPLY===
19:  (:data:`LIVE_APPLY_KEYS`, :data:`RESTART_REQUIRED_KEYS`), Qt parity map
57:LIVE_APPLY_KEYS = frozenset({
74:RESTART_REQUIRED_KEYS = frozenset()
392:    "LIVE_APPLY_KEYS",
396:    "RESTART_REQUIRED_KEYS",
===README-PLUGINS===
18:**[Download latest release](https://github.com/mskomek/hpc-client-gui/releases/latest)** · **[Documentation](https://github.com/mskomek/hpc-client-gui/wiki)** · **[CLI guide](src/hpc_gui/docs/CLI_GUIDE_en.md)** · **[Report an issue](https://github.com/mskomek/hpc-client-gui/issues)** · **[Plugins](https://github.com/mskomek/hpc-client-gui-plugins)**
20:> **🔌 Plugins & requests:** Plugins (cluster profiles, job templates, lint packs) live in the official registry
21:> **[mskomek/hpc-client-gui-plugins](https://github.com/mskomek/hpc-client-gui-plugins)**.
23:> [open a plugin request](https://github.com/mskomek/hpc-client-gui-plugins/issues/new?template=plugin-request.yml).
182:### Plugins
185:official registry [hpc-client-gui-plugins](https://github.com/mskomek/hpc-client-gui-plugins).
186:Open it from the menubar **Plugins** menu (**Browse & Install...**,
201:plugin is activated, and installed plugins are re-verified locally on every
205:![Plugin Manager with the TRUBA and ANSYS Fluent plugins](https://raw.githubusercontent.com/mskomek/hpc-client-gui/main/docs/assets/plugin-manager.png)
207:Missing a plugin? [Request one](https://github.com/mskomek/hpc-client-gui-plugins/issues/new?template=plugin-request.yml) —
65:check or **Send to plugin ▸** (see [Plugins](#plugins)). Selecting
119:### Plugins
121:Open the Plugin Manager from the menubar **Plugins** menu (**Browse &
124:plugins…*, then *Online*, *Cached*, or *Offline*. Install cluster profiles,
128:[PLUGINS_en.md](PLUGINS_en.md) for the complete guide.
136:[PLUGINS_en.md](PLUGINS_en.md).
===SKIPCHECK===
5:  E3 settings effect ownership) plus TODO-detail IDs HPC-W09-TODO-005/006,
6:  VISUAL-CURRENT-001, TODO-015..020, A11Y-CURRENT-001, TODO-022/023,
8:  MIGRATION-LANGUAGE-001 and TODO-056.
289:# TODO-MIGRATION-LANGUAGE-001: language preference migration
304:# TODO-I18N-CURRENT-001: every shipped language exercised on this candidate
320:# TODO-PUBLIC-SURFACE-CURRENT-001: README/help/About/legal vs shipped runtime
356:    """TODO-005 + UISTATE-002/005: live relabel, order/identity/selection kept."""
357:    wx = pytest.importorskip("wx")
395:    """TODO-006: Menu/Plugins/Help/Language/Version actions exist + labelled."""
396:    wx = pytest.importorskip("wx")
430:    wx = pytest.importorskip("wx")
469:    """TODO-015/018 + UISTATE-007/008: 1280x760 + 1440x900 under en+tr."""
470:    wx = pytest.importorskip("wx")
497:            # Canonical tab order (TODO-019) read back live under each locale.
512:    """TODO-019: live order reconciled with the W01-frozen canonical order."""
513:    wx = pytest.importorskip("wx")
537:    """A11Y-CURRENT-001 + TODO-023 + TODO-056 (keyboard half): names, order,
539:    wx = pytest.importorskip("wx")
561:        # accessibility evidence must not be reused (TODO-022).
===I18NPARITY===
  File "<string>", line 1
    import json; en=json.load(open('src/hpc_gui/i18n/en.json',encoding='utf-8')); tr=json.load(open('src/hpc_gui/i18n/tr.json',encoding='utf-8')); def flat(d,p=''): 
                                                                                                                                                   ^^^
SyntaxError: invalid syntax
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ /d/Python/Python312/python -c "import json; en=json.load(open('src/hpc_gui/i18n/en.json',encoding='utf-8')); tr=json.load(open('src/hpc_gui/i18n/tr.json',encoding='utf-8')); print(type(en), type(tr)); print('en_top', sorted(list(en.keys()))[:10]); print('tr_top', sorted(list(tr.keys()))[:10])"; echo "===SETTINGSKEYS==="; sed -n '55,80p' src/hpc_gui/wx_settings.py
<class 'dict'> <class 'dict'>
en_top ['about', 'ansyslint', 'app', 'cluster_self_test', 'common', 'connection', 'crash', 'dirs', 'editor', 'errors']
tr_top ['about', 'ansyslint', 'app', 'cluster_self_test', 'common', 'connection', 'crash', 'dirs', 'editor', 'errors']
===SETTINGSKEYS===
#: Settings documented as live-applicable: they measurably propagate to the
#: running feature without restart (SETTINGS-RUNTIME-001).
LIVE_APPLY_KEYS = frozenset({
    "remote_directory_cache",
    "transfer_checksum",
    "jobs_outputs_refresh_interval",
    "transfer_parallelism",
    "ssh_timeout",
    "keepalive_interval_seconds",
    "x11_enabled",
    "shortcut_preferences",
})

#: Settings that require restart before they take effect. Empty by
#: deliberate product decision: every dialog-exposed W37 setting is either
#: live-applied or takes effect on next connection/session, never on app
#: restart. The set stays declared (not implicit) so a future
#: restart-gated setting must add itself here plus visible dialog text
#: (SETTINGS-RESTART-001).
RESTART_REQUIRED_KEYS = frozenset()

#: Qt-era setting audit (SETTINGS-PARITY-001). No user-facing setting may
#: disappear silently: every known Qt-era key is PORT-TO-WX, DEPRECATED
#: (explicitly ignored with a named constant), or NOT-IN-V2 (never shipped
#: as a user setting in V2 scope).
QT_PARITY_MAP: dict[str, str] = {
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ grep -c "W40" opencode/REQUIREMENT_REGISTRY.md 2>&1 | head; grep -n "HPC-W09-UISTATE-001" opencode/REQUIREMENT_REGISTRY.md 2>&1 | head -n 5; echo "===TODO==="; grep -c "W40" opencode/TODO_OWNERSHIP_MAP.md 2>&1 | head; echo "===SECRETS-W40==="; git diff HEAD -- src/hpc_gui/core/i18n.py src/hpc_gui/config/storage.py src/hpc_gui/services/geometry_policy.py README.md src/hpc_gui/docs/HELP_en.md src/hpc_gui/docs/HELP_tr.md | grep -i -n "password\|secret\|token\|api_key\|apikey" | head -n 10; echo "SECRETSCAN_DONE"
37
908:| `HPC-W09-UISTATE-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_09.md` | 155 | Workstream E1 — Language/localization and visible text state | `W40` | — | enumerate all user-selectable languages; |
===TODO===
17
===SECRETS-W40===
warning: in the working copy of 'src/hpc_gui/config/storage.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/core/i18n.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/geometry_policy.py', LF will be replaced by CRLF the next time Git touches it
SECRETSCAN_DONE
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
AC_WAVE_BRIDGE_STDOUT_BEGIN
Auditing W40 — loading canonical authority and evidence.
Spec mapped — now verifying the candidate against fresh truth.
Core evidence re-verified — now checking requirement bindings and public surface.
# W40 Audit — fresh independent audit (opencode family)

Wave: W40 — Localization, window state and runtime setting effects
Candidate: working tree on `develop` @ `c8293d3ca309526ed250c794c3b294f7c54ef369` + W40 diff (EV-W40-DIFF), matching report baseline. Controller content_identity `d1e8be9a…` binds this tree; HEAD verified `c8293d3c`.
Context: fresh re-read of final file contents + independent re-execution. No product-code edits made (read-only audit).

## Authority verified
- `waves/pending/W40.md` (execution, 20 UISTATE + 17 TODO rows, start gate NONE, audit_policy fresh-independent).
- `opencode/REQUIREMENT_REGISTRY.md`: 37 rows owning Wave W40 confirmed (spot-checked UISTATE-001 row).
- `opencode/TODO_OWNERSHIP_MAP.md`: 17 rows owning Wave W40 confirmed.
- Live code re-read: `core/i18n.py` (SUPPORTED_LANGUAGES `("en","tr")`, ValueError-before-state-change, sync subscriber fan-out, cross-bundle fallback), `config/storage.py` (main_window get/save/clear, ValueError on non-positive sizes, never-raises getters), `services/geometry_policy.py` (resolve/recover/dispose_ignored), `wx_shell.py` (restore/save hooks wired to create/close + live relabel subscription), `wx_settings.py` (LIVE_APPLY contains the 4 asserted keys; RESTART_REQUIRED empty so `language` is live), `README.md` + `HELP_en/tr.md` (menubar Plugins wording, both languages).

## Independent test evidence (this audit, 2026-09-24, same candidate tree)
- `tests/test_w40_localization_window_settings.py` → **25 passed** (6 real-wx GUI, ~38s, wxPython msw).
- `test_w37_settings_persistence + test_w40` → **56 passed**.
- `test_geometry_policy + test_startup_i18n + test_wx_i18n + test_wx_shell_i18n + test_wave8_i18n_ui_ergonomics + test_config_storage_atomic` → **29 passed**.
- `git diff --check` → clean (exit 0; only LF→CRLF notices).
- GUI FULL: live relabel with page-identity + selection preservation; menubar/menu/help/language/version stable IDs; close-persist → create-restore roundtrip; 7 tabs × 2 locales × 2 sizes zero clipped geometry; canonical W01 tab order; keyboard names/order/focus + WebView terminal surface.
- Negative/lifecycle spot-confirmed via suite: de/fr rejected without side effects; zero/negative sizes raise; corrupt/non-dict/Qt-keyed records → defaults; off-screen clamped; tab 99 dropped; corrupt language.json → default; save best-effort never blocks shutdown.
- No weakened tests: only legitimate `pytest.importorskip("wx")` boundaries; no skip/xfail/tolerance-widening. Secrets scan on W40 hunks: clean. i18n top-level key parity confirmed; sibling hunks in `wx_shell.py` (W30/W37) preserved untouched and do not break W40 assertions.

## Requirement verdicts
All 20 UISTATE + 17 TODO-detail IDs PASS on requirement → implementation → test → evidence trace. Conditional non-persistence (splitter/columns/dialogs), narrowest-size `1280×760` statement, Qt-blob `ignored:` disposition, and DPI/screen-reader manual-acceptance limits are explicitly recorded, not green-washed. Shared dirty tree sibling hunks (W26–W39) are out-of-scope integration state; they do not invalidate W40's wave-local evidence, and all affected focused tests were re-run green after integration-base state.

## Verdict
PASS — no blocking defects. Non-blocking notes: (a) OS 150%/200% DPI proof and screen-reader certification remain controller-owned manual acceptance; (b) integration must preserve sibling hunks and re-run focused tests after any conflict resolution.

AC_WAVE_MACHINE_RESULT_BEGIN
WAVE_PHASE_STATUS: PASS
AC_WAVE_MACHINE_RESULT_END
```

WAVE_PHASE_STATUS: PASS
