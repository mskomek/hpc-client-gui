# wx Migration Wave Status Ledger

Active migration group: **Integrated wx workspace and visual parity**
(GUI-WORKSPACE-001, GUI-VISUAL-001)

Verified tip: `8beb6143719063707aaf5bf52a83e7f768fdbc37` (recovered delegate chain; focused wx suite 40 passed)
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
| D6a | `5c1a6db` | Remote toolbar, four columns, path fields | 349 passed, 0 failed |
| D6a | `2e20bc2` | `scripts/run_wx_tests.py` | 349 passed across five processes |
| D6b | `12a9f0a` | Local nav buttons, remote filter tabs, shared entry formatting, stress-test fix | 349 passed, 0 failed |
| D5b | `620cf31` | Chrome row, settings/plugins/send-logs views | 349 passed, 0 failed |

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

## 5. Resource-ceiling failures — root cause found and fixed

Runs of the full suite failed 14 to 27 tests across several branches, always in
`test_wx_transfer_ui_lifecycle.py` and `test_wx_transfer_conflict_ui.py`, with
`Failed to create dialog. Incorrect DLGTEMPLATE?` and `invalid window`.
wxWidgets eventually named the limit outright: `The current process has used all
of its system allowance of handles for Window Manager objects.` (`0x00000486`)
— the 10,000 USER-object cap.

**Root cause:** `tests/test_wx_shell_p0_stress.py::_close` called `frame.Close()`
and then only `app.ProcessPendingEvents()`. `Destroy()` is deferred, and
`ProcessPendingEvents()` does not reclaim pending deletes, so the roughly 50-100
shells the test builds accumulated until the process hit the cap. Everything
that ran afterwards — entirely unrelated tests — then failed to create windows.

**Fix:** one `wx.SafeYield()` after each close. The full suite now passes
349/349 in a single process on every branch.

This was not a product defect. Supporting measurements taken during the
investigation:

| Branch | USER objects per live shell | Concurrent shells before the cap |
|--------|-----------------------------|----------------------------------|
| D4 `cb8d22a` | 104 | 96 |
| D6a | 134 | 74 |
| D5b (chrome) | 140 | 71 |
| D6b | 168 | 59 |

`user_after_close` returns to 15 in every branch, so shells release fully; the
heavier panels only made an existing test defect visible sooner. Every failing
test passed in isolation, adding a single empty `wx.StaticText` reproduced the
identical failures whether or not it was added to a sizer, halving the panel's
HWND cost changed 24 failures into 23, and 60 remote panels can be held live at
once with dialog creation still succeeding.

The fix also makes the test measure what it claims to: resource cleanup across
repeated shell open/close cycles, which it could not verify while never
reclaiming the windows.

`scripts/run_wx_tests.py` splits the suite into five processes. It is no longer
required — the single-process run passes — but it is kept for parallelism and as
a guard against this class of accumulation.

For the final stress campaign, `peak_user_objects` and `peak_live_wx_windows`
must be added to the mandatory measured invariants with their intended bounds
documented before the run (rule AG).

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
| GUI-SET-001 | yes | n/a | no | PARTIAL | visual parity against settings_dialog.py |
| GUI-PLUGIN-001 | yes | n/a | no | PARTIAL | visual parity against plugin_manager_dialog.py |
| GUI-PLUGIN-002 | model only | n/a | no | FAILED_VERIFICATION | wx_ansys.py still has no wx view |
| GUI-HELP-001 | yes | n/a | no | PARTIAL | visual evidence |
| GUI-WORKSPACE-001 | — | **yes** | — | **COVERED** | 7 tabs, 0 launcher pages, 0 unexpected detached frames, chrome row present |
| GUI-VISUAL-001 | — | — | partial | PARTIAL | transfers panel, DPI/resize pass, canonical screenshot set |

## 7. Migration group summary

```
Active migration group: Integrated wx workspace and visual parity
Verified complete:   1  (GUI-WORKSPACE-001)
Superseded:          0
Obsolete:            0
Partial:            13
Failed verification: 2  (GUI-XFER-001/002, GUI-PLUGIN-002)
Reopened:            0
```

Rule AL requires `Partial = 0` and `Failed verification = 0`. Neither holds.

## 8. Migration group decision

```
MIGRATION GROUP: PARTIAL
```

GUI-WORKSPACE-001: **COVERED** — seven-tab integrated workspace in Qt order,
zero launcher pages, zero unexpected detached frames, chrome row present.
GUI-VISUAL-001: **PARTIAL** — toolbars, columns, filter tabs and chrome match
Qt; the transfers panel, the DPI/resize pass and the canonical screenshot set
remain.
Qt removal gate: **not run** — Qt remains the production runtime.
