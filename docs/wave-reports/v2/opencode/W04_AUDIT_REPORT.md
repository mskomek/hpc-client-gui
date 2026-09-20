# W04 Fresh-Context Audit Report

Wave: `W04`  
Implementation report: `docs/wave-reports/v2/opencode/W04_WAVE_REPORT.md`  
Audit date: 2026-09-19 UTC  
Decision: **PASS**

## Authority and identity

- Audited exactly `waves/pending/W04.md`; it is present and unambiguous. No
  `waves/bak/` material was used.
- Re-read `opencode/protocol/CORE_EXECUTION_RULES.md`,
  `opencode/prompts/30_AUDIT_WAVE.md`, all 34 owned registry/index rows
  (`HPC-W01-TRUTH-047…072`, `076…083`), all 3 owned TODO rows, and every
  mandatory `WAVE_V2_FINAL_01.md` section named by W04.
- Main: `develop` / `0f8902a023bac76071527232c2287af96478ed2b`.
- Plugin: `develop` / `f0abb7e7037e66ab451d463c699fecf4e00c89eb`; working tree
  has only the pre-existing untracked `.github/social-preview.jpg`.
- Runtime: Windows, Python 3.12.4, wxPython 4.3.1 msw / wxWidgets 3.3.3.

## Requirement and implementation trace

The canonical W04 report and `artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md`
trace all 34 requirements and 3 TODO details requirement → live owner → test
→ evidence. The freeze contains 56 unique rows with exact totals
`SUPPORTED 24 / EXPERIMENTAL 17 / REQUIRES_EXTERNAL_VALIDATION 11 /
DEPRECATED 2 / NOT-IN-V2 2 / HIDDEN 0 / UNSUPPORTED 0`; required evidence and
verification-owner columns are distinct. W01-C/W01-D/W01-E ledger, ownership,
absence, routing, contract, and sensitivity claims are pinned by the dedicated
tests. Package and external claims remain honestly deferred/N/A.

`DEF-W04-001` remains closed: live `wx_shell.py`, `wx_errors.py`, and en/tr
bundles visibly report coded plugin failures for stale and exception paths.

`DEF-W04-002` is closed and independently re-verified. `_header_download`
forwards the selected entries and current directory to the same remote
`run_action` path as the toolbar, with an empty-selection fallback that
terminates. The test helper only auto-cancels native `FileDialog`/`DirDialog`
at the OS-modal boundary; real wx button events, panels, run-action wrappers,
and routing assertions remain under test. No assertion was weakened and no
skip/xfail was added.

## Fresh evidence

| Check | Exact command / identity | Result |
|---|---|---|
| Isolated termination pin | `python -m pytest tests/test_w04_support_freeze.py -q -p no:cacheprovider -k header_upload_download` | **1 passed in 1.90s** |
| Full W04 pin suite | `python -m pytest tests/test_w04_support_freeze.py -q -p no:cacheprovider` | **28 passed in 18.28s** |
| GUI proof | `python C:\Users\mskomek\AppData\Local\Temp\opencode\w04_gui_probe.py` | **exit 0; W04_GUI_PROBE=PASS** — 5 menus, 7 tabs, `Ready`, real About dialog contract, stale plugin coded error |
| Dispatch/release lanes | `python -m pytest tests/test_wx_dispatch_error_gov.py tests/test_wave10_release_gate.py -q -p no:cacheprovider` | **53 passed in 4.53s** |
| Shell/truth/sensitivity lanes | `python -m pytest tests/test_wx_shell.py tests/test_wx_shell_w01_truth.py tests/test_w01_sensitivity.py -q -p no:cacheprovider` | **24 passed in 0.89s** |

The GUI probe emitted known wx duplicate-image-handler/WebView diagnostic
noise but terminated successfully with its explicit PASS result. The isolated
pin now terminates; the prior REOPEN condition is not present.

## Diff, routing, and safety review

- Re-read the full relevant `wx_shell.py` diff and the complete untracked W04
  test file. FIX-W04-B is the claimed handler change plus the native-modal test
  boundary; FIX-W04-A/W02 changes are already carried working-tree changes and
  were not misattributed. `git diff --check` is clean apart from normal
  pre-existing CRLF warnings.
- Current checkout remains dirty with unrelated/concurrent files and
  untracked artifacts/tests; all were preserved. This audit changed only this
  canonical audit report and did not edit product files.
- Header upload/download routing is single-path and the diagnostic probe plus
  fresh pin confirm termination and dispatch. Cross-wave gaps remain routed to
  W35/W37/W08/W10 and are not absorbed by W04.
- No credentials, tokens, `.env`, private keys, PEM/P12/PFX, `.ssh` material,
  or signing secrets were exposed in the reviewed diff, tests, reports, or
  GUI evidence. No package artifact or external-cluster claim is made.

## Final decision

**PASS** — all W04-owned requirements/TODO details are traced, current GUI and
termination evidence is reproducible, both W04 defects are closed, routing and
secret checks are clean, and no owned blocker remains. No next Wave was started.
