# GUI audit — real Windows screenshots

Date: 2026-09-04  
Platform: Windows 11  
Repository commit: `8987079b5b4160f9d639402fa45266c6d3475fd5`  

The images below are cropped captures of the actual application window. Each
tab was selected with a real mouse click before capture. No screenshot was
created from a mock, test fixture, or source rendering.

## Existing Qt GUI

| Surface | Real screenshot | Visible controls / binding audit |
|---|---|---|
| Main / Connection | [connection.png](gui-screenshots/qt/connection.png) | Add Connection and Connect Selected visible; disconnected state visible. |
| Jobs & Outputs | [jobs.png](gui-screenshots/qt/jobs.png) | Jobs tab opened; no active job data without a cluster session. |
| Directories | [directories.png](gui-screenshots/qt/directories.png) | Directory surface opened; connection-dependent controls are empty while disconnected. |
| Files | [files.png](gui-screenshots/qt/files.png) | Files surface opened; connection-dependent controls are empty while disconnected. |
| Script Editor | [editor.png](gui-screenshots/qt/editor.png) | Open, New from Template, Lint and Save are visible; remote editor path is populated. |
| Logs | [logs.png](gui-screenshots/qt/logs.png) | Logs surface opened and rendered. |
| Main window | [main.png](gui-screenshots/qt/main.png) | Top-level Update, Plugins, Send Logs, Settings and Help controls visible. |

## New wx GUI

| Surface | Real screenshot | Visible controls / binding audit |
|---|---|---|
| Files | [files.png](gui-screenshots/wx/files.png) | Real wx tab selected; Files navigation button visible and wired to `NAV-FILES`. |
| Directories | [directories.png](gui-screenshots/wx/directories.png) | Real wx tab selected; Directories navigation button visible and wired to `NAV-DIRECTORIES`. |
| Script Editor | [editor.png](gui-screenshots/wx/editor.png) | Real wx tab selected; Script Editor navigation button visible and wired to `NAV-EDITOR`. |
| Terminal | [terminal.png](gui-screenshots/wx/terminal.png) | Real embedded terminal output and input controls visible. |
| Jobs & Outputs | [jobs.png](gui-screenshots/wx/jobs.png) | Real wx tab selected; Jobs navigation button visible and wired to `NAV-JOBS`. |
| Main window | [main.png](gui-screenshots/wx/main.png) | Help and Language menus, five navigation tabs, and Ready status visible. |

## Binding results

`PROVEN` means a real GUI event path was exercised by wx tests or the
production Qt surface. `VISIBLE` means the control is present in the captured
window but its backend requires a live cluster/session. `NOT EXECUTED` means a
button was not clicked during this disconnected screenshot campaign.

| GUI | Control / path | Result |
|---|---|---|
| Qt | Main tab switching | PROVEN by the captured real tab transitions. |
| Qt | Editor Open / Save / Lint / template actions | VISIBLE; not clicked in this campaign because no remote session was connected. |
| Qt | Add Connection / Connect Selected | VISIBLE; not executed to avoid submitting credentials or connecting to a real cluster. |
| Qt | Update / Plugins / Send Logs / Settings / Help | VISIBLE; not executed in this campaign. |
| wx | Five navigation tabs | PROVEN by real mouse selection and `tests/test_wx_shell_i18n.py`. |
| wx | Files, Directories, Editor, Jobs navigation buttons | PROVEN by production dispatch wiring and focused wx tests; session-dependent windows were not opened without a connection. |
| wx | Terminal input/output surface | PROVEN visible; backend I/O requires a connected SSH session. |
| wx | Language menu | PROVEN by real wx menu tests; English/Türkçe check state and bitmap fallback covered. |

## Limitations

- This is a disconnected local screenshot campaign. No credentials, cluster
  host, private key, or real job data were entered.
- Qt and wx surfaces were captured on Windows only.
- Buttons requiring a live connection are not claimed as end-to-end backend
  success from these screenshots alone.
- The wx GUI is an alternate runtime launched with `python -m hpc_gui --wx`;
  the production default remains Qt.
