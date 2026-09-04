# wx Migration Wave Status Ledger

Active migration group: **Integrated wx workspace and visual parity**
(GUI-WORKSPACE-001, GUI-VISUAL-001)

Verified tip: `cb8d22a` (branch `delegate4-directories-logs`)
Qt remains the production runtime. No Qt/PySide6/shiboken6 removal has been
performed and the Qt removal gate has not been run.

---

## 1. Qt reference (authoritative target)

`src/hpc_gui/ui/main_window.py:138-157` builds one `QTabWidget`:

| # | Qt tab | i18n key | Qt widget |
|---|--------|----------|-----------|
| 1 | Login / Connection | `tabs.login` | `login_widget.py` (1659 lines) |
| 2 | Jobs & Outputs | `tabs.jobs_outputs` | `jobs_outputs_widget.py` (1862) |
| 3 | Directories | `tabs.directories` | `directories_widget.py` (745) |
| 4 | FTP / Files | `tabs.ftp` | `ftp_widget.py` (1803) |
| 5 | Script Editor | `tabs.editor` | `editor_widget.py` (898) |
| 6 | Logs | `tabs.logs` | `logs_widget.py` (107) |

All six are embedded workspaces. None requires a detached window for normal
navigation.

## 2. Starting state (audited at `ccdd402`)

`wx_shell.py` built a five-page notebook in which four pages held nothing but a
button that opened a detached `wx.Frame`. Connection and Logs had no tab at all;
Terminal was present although Qt has no such primary tab; tab order did not
match Qt; and `NAV-TERMINAL` carried the label key `tabs.login`.

Five modules named as `COVERED` in `services/parity_matrix.py` contained no wx
UI whatsoever (`import wx` count zero): `wx_logs.py` (36 lines),
`wx_settings.py` (54), `wx_plugins.py` (54), `wx_ansys.py` (51),
`wx_directories.py` (59).

## 3. Delivered so far

| Wave | Commit | Content | Verification |
|------|--------|---------|--------------|
| D2 | `702b598` | `wx_host.make_host()` plus `build_*_panel()` factories for five modules | focused 38, shell P0 + FILE-003 24, all invariants zero |
| D3 | `4a54cbc` | Embedded Connection, Jobs, Files (splitter), Editor, Terminal; shared `_*_callbacks()`; embedded host sizing; `files.auto_scroll` added in EN and TR | 348 passed, clipboard flake only |
| D4 | `cb8d22a` | `wx_logs_view.py`, `wx_directories_view.py`; 7-tab Qt order; `NAV-LOGS` | **349 passed, 0 failed (three separate runs)** |
| D6a | `db8262e` | Remote toolbar, four columns, path fields | REOPENED — see section 5 |
| D6a | `2e20bc2` | `scripts/run_wx_tests.py` | 349 passed across five processes |
| D6b | `fde8ddb` | Local nav buttons, remote filter tabs, shared entry formatting | REOPENED — see section 5 |
| D5b | uncommitted | Chrome row, settings/plugins/send-logs views | REOPENED — see section 5 |

Measured workspace invariants on the D4 tip and later:

```
tab_count                           7
tab_order    Connection, Jobs & Outputs, Directories, Files,
             Script Editor, Terminal, Logs
launcher_only pages                 0
unexpected_primary_detached_frames  0
```

Terminal is an accepted wx-only tab (documented deviation from Qt, placed
before Logs) carried over from GUI-TERM-002.

## 4. Delegate findings rejected by the coordinator

Each of these was caught by inspecting the diff, not by trusting the report:

- **D2** added a comment to `wx_jobs.py` purely so a source-text test would keep
  matching after a rename. Removed; the test was updated to the real string.
- **D3** invented `APP-SETTINGS` and `PLUGIN-MANAGER` dispatch branches that
  showed a `wx.MessageBox` containing only the dialog title and swallowed all
  exceptions. Removed — those branches never existed.
- **D4** put test-detection logic in production code: `NAV-DIRECTORIES`
  branched on whether `show_remote_files` had been monkeypatched. Removed; the
  two affected tests were retargeted to the behaviour they actually cover.
- **D6b** hand-wrote `category`, `file_type` and `fmt_mtime`, all three of which
  already exist in `ui/models/remote_entry_helpers.py` — a module whose own
  docstring says it must stay Qt-free so it can be shared. Replaced with the
  shared functions, which also brought the Type column to Qt's exact wording.

## 5. Resource-ceiling finding (blocks the GUI-VISUAL-001 waves)

Windows caps a process at **10,000 USER objects**. wxWidgets reports the breach
verbatim: `The current process has used all of its system allowance of handles
for Window Manager objects.` (error `0x00000486`). Once crossed, `wx.Dialog` and
`wx.Frame` creation fails, and whichever wx-heavy tests run next report
`Failed to create dialog. Incorrect DLGTEMPLATE?` or `invalid window`.

Measured peak cost of one live shell and the resulting budget:

| Branch | USER objects per live shell | Concurrent shells before the cap |
|--------|-----------------------------|----------------------------------|
| D4 `cb8d22a` | 104 | 96 |
| D6a `db8262e` | 134 (+29%) | 74 |
| D6b `fde8ddb` | 168 (+62%) | 59 |

`user_after_close` returns to 15 in every branch, so shells release fully. This
is **peak concurrency, not a leak** — three separate leak measurements showed
zero growth over 20-30 build/destroy cycles.

`tests/test_wx_shell_p0_stress.py` builds roughly 50-100 shells in sequence.
`wx.Frame.Destroy()` is deferred until the event loop runs, so pending deletes
accumulate; at 168 objects per shell the run crosses the cap, at 104 it does not.

Evidence that the product code is sound:

- Every failing test passes in isolation: transfer 25/25, `shell_p0` 13/13,
  `term002` 2/2, shell stress 1/1.
- Adding a single empty `wx.StaticText` to the remote panel reproduced the
  identical 14 failures **whether or not it was added to a sizer**, so neither
  layout nor the specific widgets are at fault.
- Halving the panel's HWND cost (`wx.ToolBar` in place of nine `wx.Button`s)
  turned 24 failures into 23. The count is not the driver; proximity to the cap
  is.
- 60 remote panels can be held live at once on both D4 and D6a with dialog
  creation still succeeding, so real usage is unaffected.
- GUI-FILE-003 stress keeps all twelve measured invariants at zero on D6a and
  D6b.

`scripts/run_wx_tests.py` splits the suite into five processes and makes D6a
pass 349/349 against 25 failures in a single process. D6b still fails the
shell-stress group even in its own process, because that group alone exceeds
the cap at 168 objects per shell.

### Required before these waves can close

1. Make `test_wx_shell_p0_stress.py` pump the event loop after each shell close
   so deferred deletes are reclaimed during the run.
2. Re-measure peak USER objects for D6a and D6b afterwards.
3. Add `peak_user_objects` and `peak_live_wx_windows` to the mandatory measured
   invariants of the final stress campaign, with the intended bound documented
   before the run (rule AG).

## 6. Wave ledger

Parity columns: **B** behavioral, **W** workspace (embedded as Qt does),
**V** visual (real wx screenshot compared against real Qt screenshot).

| Wave | B | W | V | Status | Remaining work |
|------|---|---|---|--------|----------------|
| GUI-SHELL-001/002 | yes | n/a | no | PARTIAL | visual evidence |
| GUI-SHELL-003 | yes | yes | no | PARTIAL | re-run stress after item 1 |
| GUI-I18N-001 | yes | yes | no | PARTIAL | visual evidence |
| GUI-CONN-001..005 | yes | **yes** | no | PARTIAL | visual parity |
| GUI-TERM-001/002 | yes | yes | no | PARTIAL | accepted wx-only tab documented |
| GUI-FILE-001/002/003 | yes | **yes** | partial | PARTIAL | transfers panel absent |
| GUI-XFER-001/002 | yes | no | no | FAILED_VERIFICATION | transfers panel not embedded |
| GUI-JOBS-001..004 | yes | **yes** | no | PARTIAL | visual parity |
| GUI-EDIT-001/002 | yes | **yes** | no | PARTIAL | visual parity |
| GUI-LOG-001 | yes | **yes** | close | PARTIAL | visual sign-off |
| GUI-SET-001 | model only | n/a | no | REOPENED | D5b blocked by section 5 |
| GUI-PLUGIN-001/002 | model only | n/a | no | REOPENED | D5b blocked by section 5 |
| GUI-HELP-001 | yes | n/a | no | PARTIAL | visual evidence |
| GUI-WORKSPACE-001 | — | **yes** | — | PARTIAL | chrome row still missing |
| GUI-VISUAL-001 | — | — | **no** | REOPENED | blocked by section 5 |

## 7. Migration group summary

```
Active migration group: Integrated wx workspace and visual parity
Verified complete:   0
Superseded:          0
Obsolete:            0
Partial:            11
Failed verification: 1
Reopened:            3
```

Rule AL requires `Partial = 0` and `Failed verification = 0`. Neither holds.

## 8. Migration group decision

```
MIGRATION GROUP: PARTIAL
```

GUI-WORKSPACE-001: **PARTIAL** — the seven-tab integrated workspace exists with
zero launcher pages and zero unexpected detached frames, but the application
chrome row is not yet delivered.
GUI-VISUAL-001: **NOT COVERED**
Qt removal gate: **not run** — Qt remains the production runtime.
