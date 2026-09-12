# Packet L: Legacy migration and parity ownership

This is a behavior-based ownership review. Qt remains a production runtime;
wx remains active migration/runtime work. A direct-import scan found 122
PySide6/PyQt import statements under `src/hpc_gui`. The reviewed suites are
retained unless a specific test body lacks unique behavior evidence.

| File | Current owner/evidence type | Finding |
| --- | --- | --- |
| `tests/test_parity_matrix.py` | Reporting | Exercises `render_status` output and rejects incomplete or unjustified mappings. It validates the parity report format; it does not establish GUI behavior. |
| `tests/test_gui_feature_parity_baseline.py` | Audit | Checks uniqueness and required surface IDs in a static feature baseline. It does not execute either GUI. |
| `tests/test_qt_removal_gate.py` | Audit | Tests tracked-source/dependency/package scans and evidence/gate decisions using temporary Git repositories and synthetic evidence. `test_true_go_fixture` proves only the gate accepts a complete fixture; it does not mean the current repository is GO. Current production still contains Qt imports, so removal remains NO-GO. |
| `tests/test_wx_terminal_parity_evidence.py` | GUI behavior with real wx/WebView/xterm and a fake SSH adapter in subprocesses; historical evidence is separate | Ten behavior tests exercise rendered VT fixtures, adapter callbacks, resize, reconnect, and close boundaries when WebView is available. The adapter is not a PTY; these tests do not launch a PTY process, prove packaged runtime, or exercise a live cluster. Removed `test_generate_parity_evidence`: it only wrote a hard-coded dictionary to `docs/v2/GUI_TERM_001_EXECUTION_EVIDENCE.json`, including a stale packaged-PASS claim, then asserted the file existed. Search found no production caller or test depending on it. The historical JSON itself is retained unchanged. |
| `tests/test_wave2_wx_ui_parity.py` | GUI behavior | Uses real wx controls and dispatched actions for local Files selection, context menus, clipboard/path actions, labels, navigation buttons, and status. Dialogs/filesystem inputs are local fixtures. Its teardown now drains deferred wx events and asserts no top-level test windows remain before destroying the app. It tests wx behavior; the filename does not mean it compares Qt and wx. |
| `tests/test_wave9_ci_unicode_matrix.py` | Audit | Inspects inventory files, fixture text, localization JSON, source text, and workflow policy. Since `.github/workflows/ci.yml` is absent, its workflow check validates the archived `docs/ci-disabled/ci.yml`; this test is not evidence that automatic CI runs. |
| `tests/test_wave10_release_gate.py` | Mixed: service/storage behavior, static audit, and local fixture behavior | Config atomicity/round-trip and navigation encryption use temporary paths; source scans and documentation assertions are static audit checks; local filename and editor-model cases are narrow runtime behavior. No test launches a packaged artifact. The prior `test_favorites_history_persistence` only asserted that a class existed; it now writes a Unicode favorite and visit to a temporary encrypted store and verifies both after constructing a fresh store. |

The current `docs/v2/WX_MIGRATION_WAVE_STATUS.md` ledger remains PARTIAL for
GUI-TERM-001. Windows packaged terminal input/readback is still FAIL/PARTIAL;
Linux wx and macOS packaged runtime evidence remain NOT EVIDENCED. Static gate
fixtures, fake-SSH WebView tests, and historical JSON do not upgrade those
claims.

Node delta: removed
`tests/test_wx_terminal_parity_evidence.py::test_generate_parity_evidence`.
No equivalent rename is claimed. Its old output-writing behavior had no unique
runtime assertion or external selector; its only file-existence assertion was
self-fulfilling. The documented behavior owners remain the ten real GUI tests
and existing history stays in the evidence JSON. The weak Wave 10 node was
strengthened in place, so its nodeid remains unchanged. No production code or
automatic CI workflow changed.
