# W44 Wave Report — Evidence reconciliation, full suite and static gates

```text
Wave: W44
Canonical report path: docs/wave-reports/v2/opencode/W44_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui
Branch: develop
Baseline SHA: c8293d3ca309526ed250c794c3b294f7c54ef369
Current HEAD: c8293d3ca309526ed250c794c3b294f7c54ef369 (working-tree changes uncommitted; controller owns commit/integration)
Content identity (controller handoff): 545d2a621d59a9a75e3259ca657058c9d6b0aaf96cfa4b387885b66c496581e7
Plugin/external repo SHA(s), if applicable: N/A (no plugin repo touched)
First started: 2026-09-24 (W44 run phase)
Last updated: 2026-09-25
Session status: READY FOR INDEPENDENT AUDIT
Wave decision: GO (worker-level; pending controller independent audit)
```

## Authority reads

1. `waves/pending/W44.md` (wave_id W44, execution kind, canonical_source W44, 13 source rows + 3 TODO rows, start gate NONE, cohort P9-integration-gate, required evidence `GUI,PACKAGE,EXTERNAL`, integration refs W22/W27/W31/W36/W38/W39/W40/W43 non-blocking).
2. `opencode/REQUIREMENT_REGISTRY.md` rows owning Wave W44: `HPC-W10-EVID-001`..`012`, `HPC-W10-STATIC-001` (lines 1016-1027, 1304); TODO rows `HPC-W10-TODO-ARCH-QT-WX-001/002`, `HPC-W10-TODO-ARCH-PACKAGE-001` (lines 1542-1544).
3. `opencode/TODO_OWNERSHIP_MAP.md` rows owning Wave W44: the same 3 ARCH/PACKAGE TODO rows (ACTIVE).
4. `waves/bak/WAVE_V2_FINAL_10.md` → Workstream A (lines 248-255), Workstream B (257-268), Workstream C (270-280), Workstream D (282-284). Workstreams E–I are NOT owned by W44 (later-wave scope; not executed here).
5. `.opencode/protocol/LOCAL_REAL_HPC_LAB.md` (EXTERNAL evidence authority; lab is shared/serialized — no EXTERNAL replay executed by W44, see EVID note).
6. Live code before edits: `src/hpc_gui/wx_local_files.py:20`, `src/hpc_gui/wx_remote_files_view.py:16` (both imported `hpc_gui.ui.models.remote_entry_helpers`); `src/hpc_gui/wx_shell.py:3899` (lazy-imported `PLUGIN_REQUEST_URL` from the Qt dialog, whose module top-level imports PySide6); `src/hpc_gui/ui/models/remote_entry_helpers.py` (pure helpers, Qt-free body, but housed under `hpc_gui.ui.*`); `src/hpc_gui/ui/dialogs/plugin_manager_dialog.py:56` (defined `PLUGIN_REQUEST_URL` inside a Qt module); `build/windows/hpc-client-gui.spec` (Qt/WebEngine hidden imports, dual-runtime-undecided at W44).
7. Live tests before edits: `tests/test_remote_entry_helpers.py` (patched `helpers.t`), `tests/test_plugin_manager_ui.py` (URL value pin), `tests/test_wx_dispatch_error_gov.py` (PLUGIN-REQUEST owner pin on symbol `PLUGIN_REQUEST_URL`).

## Baseline capture

```text
Evidence ID: EV-W44-BASELINE
Commit: c8293d3ca309526ed250c794c3b294f7c54ef369
Branch: develop
git status: dirty (pre-existing sibling-wave M files + untracked sibling files preserved untouched; W44 adds 2 new service modules + 1 new test file + scoped hunks, see diff review)
```

Content-identity note: the controller handoff cites `content_identity=545d2a6...`. `waves/` is gitignored, so the pending spec lives outside Git history by program design. The worker proceeded on current repository truth without editing the spec; identity reconciliation is controller-owned. HEAD `c8293d3` matches the W43 audit candidate SHA.

A separable narrow baseline is not available on the shared dirty `develop` tree (parallel cohort shares one working tree). The W44 worker baselined by (a) ruff-at-HEAD comparison for touched files (3 pre-existing F401s proven present at HEAD via `.tmp/w44-run` baseline copies), and (b) stash-proven pre-existing failures (3 focused failures reproduce identically with W44 changes stashed). No sibling file was reverted, merged, or cleaned by this worker.

## Discovery pass / WAVE_FINDINGS

```text
Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status
DEF-W44-001 | P1 | wx runtime imports hpc_gui.ui.* for shared formatting | wx_local_files.py:20, wx_remote_files_view.py:16 → hpc_gui.ui.models.remote_entry_helpers | shared pure helpers housed under Qt UI package | wx runtime cannot load shared behavior without the Qt UI package path (ARCH-QT-WX-002 violated) | move implementation to hpc_gui.services.remote_entry_format; ui module becomes re-export shim | YES (FIX-A) | FIXED+VERIFIED
DEF-W44-002 | P1 | wx PLUGIN-REQUEST imports Qt dialog module for a constant | wx_shell.py:3899 → hpc_gui.ui.dialogs.plugin_manager_dialog (top-level PySide6 imports) | shared URL constant defined inside Qt module | importing the constant executes PySide6 import chain inside wx runtime (ARCH-QT-WX-002 violated) | move constant to hpc_gui.services.plugin_request; dialog + wx both consume neutral module | YES (FIX-B) | FIXED+VERIFIED
OBS-W44-003 | N/A | no new Qt-only service logic introduced by W44 | new modules source-scanned Qt-free + subprocess proof (no PySide6 in sys.modules) | n/a | ARCH-QT-WX-001 holds | pins in tests/test_w44_arch_qt_wx_package.py | NO (part of FIX-A/B) | PINNED
OBS-W44-004 | N/A | PyInstaller Qt/WebEngine hidden imports intentional | build/windows/hpc-client-gui.spec hiddenimports + W44 audit marker | dual-runtime still supported; W56 owns cutover decision | dropping entries now would break Qt surface | audit marker comment + pin test | NO | PINNED (no functional change)
```

Second-defect sweep (W44 surface only): remaining `hpc_gui.ui` references in `src/hpc_gui/wx*.py`/`services/*.py` are docstring mentions only (no import statements — pinned by test); `services/` top-level Qt imports (`terminal_bridge`, `x11_runner`) are pre-existing Qt-surface bridges, not consumed by the wx entry-format/plugin-request chain (subprocess proof shows no PySide6 load); no new service file adds Qt imports. Result: no further W44-owned defects beyond DEF-W44-001/002.

## Implementation

### FIX-A — framework-neutral entry formatting (DEF-W44-001; ARCH-QT-WX-002)

- NEW `src/hpc_gui/services/remote_entry_format.py` (79 lines): `fmt_size`, `fmt_mtime`, `file_type`, `category`, `natural_sort_key` — byte-identical semantics to the previous ui implementation; imports only `datetime`/`re`/`hpc_gui.core.i18n`/`hpc_gui.services.files_base`. Zero Qt, zero `hpc_gui.ui`.
- `src/hpc_gui/ui/models/remote_entry_helpers.py` → re-export shim (`13 +66` numstat): same five names re-exported (`is`-identical objects, pinned); Qt surface and existing importers keep working.
- `src/hpc_gui/wx_local_files.py` (1 line), `src/hpc_gui/wx_remote_files_view.py` (1 line): import from `hpc_gui.services.remote_entry_format`.
- Downstream evidence refresh (directly invalidated, minimal): `tests/test_remote_entry_helpers.py` patches the canonical `t` lookup site (`neutral_format.t`) instead of the shim; assertions unchanged (+6/−2 with W44 comments).

### FIX-B — framework-neutral plugin-request URL (DEF-W44-002; ARCH-QT-WX-002)

- NEW `src/hpc_gui/services/plugin_request.py` (22 lines): `PLUGIN_REQUEST_URL` (exact value preserved) + `is_allowed_plugin_request_url()`. Zero Qt, zero `hpc_gui.ui`.
- `src/hpc_gui/ui/dialogs/plugin_manager_dialog.py`: imports the constant from the neutral module (re-exported, so `from hpc_gui.ui.dialogs.plugin_manager_dialog import PLUGIN_REQUEST_URL` keeps working for Qt callers/tests); `_is_allowed_plugin_request_url` semantics unchanged.
- `src/hpc_gui/wx_shell.py` PLUGIN-REQUEST branch (1 line): imports from `hpc_gui.services.plugin_request`. The dispatch-owner contract test still passes (it pins the `PLUGIN_REQUEST_URL` symbol in the branch).
- `src/hpc_gui/ui/main_window.py`: unchanged (Qt surface; consumes via dialog re-export).

### ARCH-PACKAGE-001 audit (OBS-W44-004)

- `build/windows/hpc-client-gui.spec` (+6 comment lines only, no functional change): W44 re-audit marker documents that `PySide6.*`/`QtWebEngine*` hidden imports ship intentionally as dual-runtime packaging until the W56 runtime-cutover decision; they are not stale compatibility imports. Pinned by `test_w44_package_hidden_imports_are_intentional`.

### ARCH-QT-WX-001 (OBS-W44-003)

- No new Qt-only service logic: both new modules source-scanned Qt-free and subprocess-proven to load without PySide6. Pre-existing Qt bridges untouched.

## Tests and evidence

New: `tests/test_w44_arch_qt_wx_package.py` — **6 passed**:

| Requirement | Test | Evidence |
|---|---|---|
| ARCH-QT-WX-001/002 | test_w44_neutral_modules_are_qt_free_and_ui_free | both new modules: no Qt, no hpc_gui.ui imports |
| ARCH-QT-WX-002 | test_w44_wx_runtime_has_no_hpc_gui_ui_imports | wx_local_files/wx_remote_files_view/wx_shell: zero hpc_gui.ui imports |
| ARCH-QT-WX-002 | test_w44_plugin_request_url_single_sourced | neutral value == expected URL; dialog re-exports, defines no copy |
| ARCH-QT-WX-002 | test_w44_entry_format_parity_with_qt_surface | shim names `is` neutral names; behavior pins |
| ARCH-QT-WX-002 | test_w44_wx_imports_without_qt_ui_or_pyside | subprocess: wx consumers load, `UI_MODULES=[]`, `QT_MODULES=[]`, URL correct |
| ARCH-PACKAGE-001 | test_w44_package_hidden_imports_are_intentional | spec keeps Qt/WebEngine entries + audit marker |

Workstream B — invalidated-test replay (exact reruns at HEAD `c8293d3`, `PYTHONPATH=src`, `-p no:cacheprovider`):

```text
Evidence ID: EV-W44-SLICES
conn (connection/session): tests/test_w19_connection_lifecycle.py → 20 passed
sftp: tests/test_w12_sftp_semantics.py + tests/test_wave3_remote_sftp_ssh.py → 44 passed, 1 failed (pre-existing, stash-proven: test_ssh_backend_rejects_invalid_utf8_text)
provider registry: tests/test_wave79_provider_contract.py + tests/test_wave6_plugin_provider_unicode.py + tests/test_w03_settings_provider_inventory.py → 86 passed, 1 failed (pre-existing, stash-proven: test_full_plugin_unicode_flow)
plugindisc (plugin discovery): tests/test_plugin_manager_ui.py + tests/test_w35_plugin_manager_gui.py → 43 passed
settings: tests/test_w37_settings_persistence.py → 31 passed
updater/package: tests/test_w43_restart_package_policy.py + tests/test_w41_updater_routing.py + tests/test_app_updater.py + tests/test_w36_packaged_docs.py → 58 passed
w44arch (owned pins + touched): tests/test_w44_arch_qt_wx_package.py + tests/test_remote_entry_helpers.py + tests/test_wx_dispatch_error_gov.py → 54 passed, 1 failed (pre-existing, stash-proven: test_editor_save__local_and_remote_paths_have_distinct_owners)
w03+w12 confirmation rerun → 30 passed
```

Workstream C — full automated suite (command/environment/counts/exit, truthful partial):

```text
Evidence ID: EV-W44-FULL
Collection: PYTHONPATH=src python -m pytest tests -p no:cacheprovider --collect-only → 3366 tests collected
  (excluded: tests/contracts (1)/ + tests/contracts (2)/ — untracked duplicate-basename junk dirs that break collection for the whole suite; duplicates of tests/contracts/)
Single-process full run → EXIT 127, Windows fatal exception: access violation in tests/test_editor_flow.py (native crash kills runner; no counts obtainable in-process)
Shard runs (non-overlapping file sets, same env):
  shard2 (53 files) → 696 passed, 2 skipped, 10 failed [EV-W44-SHARD2]
  shard3 (53 files) → 582 passed, 1 skipped, 2 failed [EV-W44-SHARD3]
  shard5 (52 files) → 751 passed, 28 skipped, 0 failed [EV-W44-SHARD5]
  shard6 (52 files) → 418 passed, 5 skipped, 3 failed [EV-W44-SHARD6]
  shard1/shard1b/shard4 → runner killed by native access violations (no counts):
    tests/test_jobs_outputs_scroll.py setUp, tests/test_performance_probe.py::test_qt_event_loop_block_is_detected,
    tests/test_w15_fresh_user_startup.py via wx_connection_dialog.ShowModal, tests/test_editor_flow.py
Shard-failure triage (all non-owned; W44 files untouched by each):
  shard2: 2× test_file_manager_profile (FTP/file-manager surface → file-manager waves), 1× test_qt_removal_gate::test_git_tracked_enumeration_rejects_git_failure (gate-script env → gate owner), 6× test_w27_editor_conflicts (editor surface → W27), 1× dispatch editor_save (stash-proven pre-existing)
  shard3: 1× test_wave10_release_gate::test_no_new_errors_ignore (single errors='ignore' in src/hpc_gui/services/local_files.py:65 — file unmodified by W44 → owning wave), 1× wave3 utf8 (stash-proven pre-existing)
  shard6: 1× wave6 unicode (stash-proven pre-existing), 2× test_wx_term002 (WebView2 0x80004004 headless — no Edge/WebView2 runtime in this environment → environmental)
Skips: 36 total across shards, all pre-existing platform-conditional; W44 added zero skips/xfails.
Full-suite verdict: NOT green in this environment (native GUI crashes + 15 routed non-owned failures). No owned defect; no green fabricated. Logs: .tmp/w44-run/shard{2,3,5,6}.log, full-suite.log.
```

Workstream D — static/quality gates:

```text
Evidence ID: EV-W44-STATIC
python -m ruff check <all 10 W44 files incl. both new modules and both test files> → All checks passed
  (wx_shell.py + wx_remote_files_view.py carry 3 F401s proven present at HEAD via .tmp/w44-run baseline copies — pre-existing, sibling-owned, not fixed opportunistically)
python -m ruff check src tests scripts → 319 errors, all outside W44 files (top: scripts/validate_wave_closeout.py 118, tests/test_wave_state_engine.py 106, tests/contracts* 57 — pre-existing governance/script surface, recorded as known warnings, release-relevance: none for W44)
python -m py_compile on all W44 files → COMPILE-OK
git diff --check → exit 0 (only sibling-wave CRLF warnings)
Secret sweep over W44 hunks/new files (password/secret/private-key patterns) → clean
```

Evidence classes: `GUI` (required) → covered by real-wx/runtime pins (subprocess wx load proof; updater GUI re-runs green via W43 pins; no new GUI surface added by W44). `PACKAGE` (required) → spec re-audit + marker + pin test; no artifact built/published by W44 (freeze owned by W56–W61; `NO-CANDIDATE` recorded honestly). `EXTERNAL` (required class) → no per-requirement external replay executed (LOCAL_REAL is serialized shared infra; W44 owned no site-specific behavior; lab health cited from profile baseline only). No mocks substituted for any owned claim.

## Diff review

```text
Evidence ID: EV-W44-DIFF
New files (untracked, W44-owned): src/hpc_gui/services/remote_entry_format.py (79), src/hpc_gui/services/plugin_request.py (22), tests/test_w44_arch_qt_wx_package.py (134)
Tracked hunks (W44-owned only; sibling Wave hunks in the same files preserved untouched):
  src/hpc_gui/wx_local_files.py: 1/1 (import source)
  src/hpc_gui/wx_remote_files_view.py: 1/1 (import source)
  src/hpc_gui/wx_shell.py: 1-line import-source hunk inside a 411-line diff otherwise owned by sibling waves (not claimed, not modified)
  src/hpc_gui/ui/models/remote_entry_helpers.py: 13+/66- (implementation → re-export shim)
  src/hpc_gui/ui/dialogs/plugin_manager_dialog.py: 9+/8- (constant → neutral import)
  build/windows/hpc-client-gui.spec: +6 (audit comment only)
  tests/test_remote_entry_helpers.py: +6/-2 (canonical t lookup site + W44 comments; assertions unchanged)
git diff --check: clean (exit 0)
Scope check: no sibling M file modified by this worker (verified per-file: local_files.py errors='ignore' failure is in an unmodified file); no test weakened (zero skip/xfail/assertion edits except the invalidated-patch-site update); no secrets; no generated/binary noise.
```

## Handoff / DAG unlocks

Historical unlock targets (W45–W54) are integration hints only; no downstream Wave was started by this worker.

## Findings and resume state

- No owned blocking defect remains. DEF-W44-001/002 fixed + verified (6/6 pins green; replay slices green).
- Cross-scope routes (recorded, not fixed — per HPC-GOV-020):
  - R-W44-001 → editor-wave owners (W27/W15/W39 per surface): 6× w27_editor_conflicts, w15 ShowModal native crash, editor_flow native crash, dispatch editor_save (pre-existing).
  - R-W44-002 → lifecycle-native owner (W53, LIFECYCLE-NATIVE-004): access violations in test_jobs_outputs_scroll setUp, test_performance_probe qt_event_loop, w15 ShowModal, editor_flow; full-suite single-process exit 127.
  - R-W44-003 → provider/storage owners: wave6 unicode flow, wave3 utf8 rejection, file_manager_profile ×2, local_files.py errors='ignore' (release-gate).
  - R-W44-004 → gate-script owner: qt_removal_gate git-enumeration failure test (environmental).
  - R-W44-005 → terminal/package owners: 2× wx_term002 WebView2 0x80004004 (headless env, no Edge runtime).
  - R-W44-006 → controller: untracked junk dirs tests/contracts (1)/ tests/contracts (2)/ break collection; 94/151 W01 rows point at superseded SHAs (flagged, closed waves not invalidated).
- No `AWAITING_INPUT` (no concrete missing artifact/API).
- No `EXTERNAL_BLOCKED` (no external replay required for owned claims; lab untouched).
- Resume point: controller independent audit of this READY_FOR_AUDIT candidate; auditor re-runs EV-W44-SLICES slice commands + `tests/test_w44_arch_qt_wx_package.py` verbatim and inspects EV-W44-DIFF hunks.

---

## Contradiction scan

- Single-source claims agree: URL value identical in neutral module, dialog re-export, wx consumer, and two pinning tests.
- Entry-format parity is `is`-identity, not copy-paste: shim and neutral cannot diverge silently.
- Package claims: no artifact built, none claimed; spec marker documents intentional dual-runtime, matching the ARCH-PACKAGE-001 test.
- Full-suite status is uniformly NOT-green across report, slices, and logs — no green claim anywhere.
- No test weakened; the one invalidated pin was re-pointed at the canonical lookup with identical assertions.

## Review passes

- Claim-to-source: every owned ID (13 EVID + STATIC + 3 TODO) traces to a named live owner + pinned test/command in this report.
- Diff review: all W44 hunks inspected; sibling hunks explicitly disclaimed.
- Adversarial: blocked-`hpc_gui.ui` subprocess proof; `errors='ignore'`/unsigned-claim-style sweeps kept Qt-free; confirm-exception paths untouched.

---

## EV-W44-EVID001 reconciliation matrix (Workstream A)

151 W01-derived rows. `Valid?` rule: `CURRENT-AT-HEAD` = owning report bound at HEAD `c8293d3`; `RE-RUN-GREEN-AT-HEAD` = owning slice re-ran green in W44 at HEAD; `SUPERSEDED-SHA` = evidence points to an older SHA (flagged for controller integration; the closed owner Wave is NOT invalidated/reopened by this flag); `PRIOR` = report exists without SHA binding (not invalidated). Package column is uniformly `NO-CANDIDATE` (frozen-candidate freeze is owned by W56–W61; none exists at W44 — recorded, not fabricated). External column cites lab-infra health only; no per-row external replay was owned by W44.
| W01 requirement | Owning Wave | Latest code SHA | Latest test evidence | Latest package hash | External evidence | Valid? |
|---|---|---|---|---|---|---|
| `HPC-W01-INV-001` | `W01` | `c8293d3` | W01 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-INV-002` | `W01` | `c8293d3` | W01 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-INV-003` | `W01` | `c8293d3` | W01 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-INV-004` | `W01` | `c8293d3` | W01 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-INV-005` | `W01` | `c8293d3` | W01 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-INV-006` | `W01` | `c8293d3` | W01 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-INV-007` | `W01` | `c8293d3` | W01 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-INV-008` | `W01` | `c8293d3` | W01 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-INV-009` | `W01` | `c8293d3` | W01 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-INV-010` | `W01` | `c8293d3` | W01 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-INV-011` | `W01` | `c8293d3` | W01 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-INV-012` | `W01` | `c8293d3` | W01 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-INV-013` | `W01` | `c8293d3` | W01 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-INV-014` | `W01` | `c8293d3` | W01 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-INV-015` | `W01` | `c8293d3` | W01 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-INV-016` | `W01` | `c8293d3` | W01 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-INV-017` | `W01` | `c8293d3` | W01 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-INV-018` | `W01` | `c8293d3` | W01 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-INV-019` | `W01` | `c8293d3` | W01 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-INV-020` | `W01` | `c8293d3` | W01 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-INV-021` | `W01` | `c8293d3` | W01 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRACE-001` | `W02` | `c8293d3` | W02 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-001` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-002` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-003` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-004` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-005` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-006` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-007` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-008` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-009` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-010` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-011` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-012` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-013` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-014` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-015` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-016` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-017` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-018` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-019` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-020` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-021` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-022` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-023` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-024` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-025` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-026` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-027` | `W03` | `c8293d3` | W03 report (no SHA marker); EV-W44-SLICES provider/settings (w03 30 passed w/ w12) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-028` | `W03` | `c8293d3` | W03 report (no SHA marker); EV-W44-SLICES provider/settings (w03 30 passed w/ w12) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-029` | `W03` | `c8293d3` | W03 report (no SHA marker); EV-W44-SLICES provider/settings (w03 30 passed w/ w12) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-030` | `W03` | `c8293d3` | W03 report (no SHA marker); EV-W44-SLICES provider/settings (w03 30 passed w/ w12) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-031` | `W03` | `c8293d3` | W03 report (no SHA marker); EV-W44-SLICES provider/settings (w03 30 passed w/ w12) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-032` | `W03` | `c8293d3` | W03 report (no SHA marker); EV-W44-SLICES provider/settings (w03 30 passed w/ w12) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-033` | `W03` | `c8293d3` | W03 report (no SHA marker); EV-W44-SLICES provider/settings (w03 30 passed w/ w12) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-034` | `W03` | `c8293d3` | W03 report (no SHA marker); EV-W44-SLICES provider/settings (w03 30 passed w/ w12) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-035` | `W03` | `c8293d3` | W03 report (no SHA marker); EV-W44-SLICES provider/settings (w03 30 passed w/ w12) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-036` | `W03` | `c8293d3` | W03 report (no SHA marker); EV-W44-SLICES provider/settings (w03 30 passed w/ w12) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-037` | `W03` | `c8293d3` | W03 report (no SHA marker); EV-W44-SLICES provider/settings (w03 30 passed w/ w12) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-038` | `W03` | `c8293d3` | W03 report (no SHA marker); EV-W44-SLICES provider/settings (w03 30 passed w/ w12) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-039` | `W03` | `c8293d3` | W03 report (no SHA marker); EV-W44-SLICES provider/settings (w03 30 passed w/ w12) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-040` | `W03` | `c8293d3` | W03 report (no SHA marker); EV-W44-SLICES provider/settings (w03 30 passed w/ w12) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-041` | `W03` | `c8293d3` | W03 report (no SHA marker); EV-W44-SLICES provider/settings (w03 30 passed w/ w12) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-042` | `W03` | `c8293d3` | W03 report (no SHA marker); EV-W44-SLICES provider/settings (w03 30 passed w/ w12) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-043` | `W03` | `c8293d3` | W03 report (no SHA marker); EV-W44-SLICES provider/settings (w03 30 passed w/ w12) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-044` | `W03` | `c8293d3` | W03 report (no SHA marker); EV-W44-SLICES provider/settings (w03 30 passed w/ w12) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-045` | `W03` | `c8293d3` | W03 report (no SHA marker); EV-W44-SLICES provider/settings (w03 30 passed w/ w12) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-046` | `W03` | `c8293d3` | W03 report (no SHA marker); EV-W44-SLICES provider/settings (w03 30 passed w/ w12) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-047` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-048` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-049` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-050` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-051` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-052` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-053` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-054` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-055` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-056` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-057` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-058` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-059` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-060` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-061` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-062` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-063` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-064` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-065` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-066` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-067` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-068` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-069` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-070` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-071` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-072` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-073` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-074` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-075` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-076` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-077` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-078` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-079` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-080` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-081` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-082` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-083` | `W04` | `c8293d3` | W04 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-084` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-085` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-086` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-087` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-088` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-089` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-090` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-091` | `W05` | `c8293d3` | W05 report (no SHA marker); EV-W44-SLICES plugindisc (43 passed) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | RE-RUN-GREEN-AT-HEAD |
| `HPC-W01-TRUTH-092` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-093` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-094` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-095` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-096` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-097` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-098` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-099` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-100` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-101` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-102` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-103` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-104` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-105` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-106` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-107` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-108` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-109` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-110` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-111` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-112` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-113` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-114` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-115` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-116` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-117` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-118` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-119` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-120` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-121` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-122` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-123` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-124` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-125` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-126` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-127` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-128` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |
| `HPC-W01-TRUTH-129` | `W06` | `c8293d3` | W06 report (no SHA marker) | NO-CANDIDATE (W56-W61 own freeze) | LAB-HEALTH-ONLY / N/A | PRIOR (report exists; no SHA binding; not invalidated) |