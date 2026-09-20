# W05 Wave Report — Truth-freeze governance and report consistency

Wave: `W05`
Canonical report path: `docs/wave-reports/v2/opencode/W05_WAVE_REPORT.md`
Repository: `mskomek/hpc-client-gui`
Branch: `develop`
Baseline SHA (session pin): `0f8902a023bac76071527232c2287af96478ed2b`
Current HEAD: `0f8902a023bac76071527232c2287af96478ed2b`
Tested implementation state: `HEAD 0f8902a0` + working tree exactly as recaptured 2026-09-19 (repair cycle 1, `DEF-W05-001` closeout; zero product-behavior edits by this Wave — only three SUPERSEDED-banner governance edits + these two reports; all other working-tree entries are pre-existing/concurrent foreign-Wave changes preserved byte-for-byte, see §Repository truth / §Diff review)
Plugin repo: `D:/Projeler/hpc-client-gui-plugins` on `develop` / `f0abb7e7037e66ab451d463c699fecf4e00c89eb` (clean except untracked `.github/social-preview.jpg`, preserved)
First started: 2026-09-18
Last updated: 2026-09-19 (UTC) — repair cycle 1 of max 2: `DEF-W05-001` (Luna audit REOPEN, report/diff identity stale) CLOSED by full working-tree/diff recapture + evidence rebind below; no product edits
Session status: COMPLETE (repair 1)
Wave decision: PASS
Executable authority: `waves/pending/W05.md` (exactly one copy; `waves/bak/` never read for execution)
Execution model: `opencode-go/muse-spark-1.3-contributor`
Dependency: `W04` — `docs/wave-reports/v2/opencode/W04_WAVE_REPORT.md` decision `PASS`, audit `PASS`; entry revalidated (same pins `0f8902a0` / plugin `f0abb7e7`, no owned W04 blocker touches this scope)

## Repository truth (before edits)

| Identity | Value |
|---|---|
| main branch / HEAD | `develop` / `0f8902a023bac76071527232c2287af96478ed2b` (2026-09-18T22:37:38+03:00) |
| main remote pin | `git ls-remote origin refs/heads/develop` → `0f8902a023bac76071527232c2287af96478ed2b` (2026-09-18T22:37:47+03:00) — identical to local HEAD, VERIFIED |
| plugin branch / HEAD | `develop` / `f0abb7e7037e66ab451d463c699fecf4e00c89eb`, working tree clean except untracked sidecar |
| plugin remote pin | `git ls-remote origin refs/heads/develop` (plugin) → `f0abb7e7037e66ab451d463c699fecf4e00c89eb` — identical to checkout, VERIFIED |
| runtime truth | `Python 3.12.4`, `wxPython 4.3.1 msw (phoenix) wxWidgets 3.3.3` |
| packaging runtime default | `src/hpc_gui/runtime.py:3` → `DEFAULT_GUI_RUNTIME = "qt"` (recorded, not changed; wx cutover owned by W10/W56–W57) |
| working tree (recaptured 2026-09-19T18:1x+03:00, verbatim `git status --porcelain=v1 --untracked-files=all`) | **14 tracked modifications + 33 untracked entries** (full per-entry attribution in §Diff review). All non-W05 entries are pre-existing/concurrent foreign-Wave changes — preserved byte-for-byte, none reverted, none absorbed into W05 claims. W05-owned tracked edits: exactly the three SUPERSEDED banners (§Canonical-report closeout). This recapture closes `DEF-W05-001` (2026-09-18 tree record of 7 tracked mods was stale). |

SHA distinctions (`HPC-W01-TODO-W01-SHA-001`): documentation-audit baseline (non-pinning) `731357c6a9e69da121f6783e07d5d65ad3a8539c` ≠ tested implementation SHA `0f8902a0`+tree ≠ current HEAD `0f8902a0` (tree dirty, stated) ≠ evidence-only closure commit (none — this session commits nothing) ≠ plugin SHA `f0abb7e7`. No stale SHA is called current.

## Owned requirements (37 source-derived)

35 MANDATORY + 2 SUPERSEDED (verify-only, `087`/`091` under `HPC-GOV-017`). All traced requirement → live implementation owner → test → evidence.

| ID | Wording (short) | Live truth / owner | Status |
|---|---|---|---|
| `HPC-W01-TRUTH-001` | auditable map of what the app exposes; no broad repair | map = W01 inventory + W04 56-row freeze `artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md`; this session changes no behavior | VERIFIED |
| `HPC-W01-TRUTH-002` | main `develop` fetched and pinned | local `0f8902a0` == `origin/develop` tip via `ls-remote`, `EV-W05-PIN-001` | VERIFIED |
| `HPC-W01-TRUTH-003` | plugin repo fetched and pinned | checkout `develop f0abb7e7` == plugin `origin/develop` tip via `ls-remote`, `EV-W05-PIN-001` | VERIFIED |
| `HPC-W01-TRUTH-004` | application can launch in dev environment | real wx launch `EV-W05-GUI-001` PASS (exit 0), not pytest | VERIFIED |
| `HPC-W01-TRUTH-005` | no destructive cleanup needed | none performed; `git status` preserved; FFSync sidecars untouched | VERIFIED |
| `HPC-W01-TRUTH-006` | rediscover anchors at pinned HEAD; stale names not treated as current | all 18 planning anchors present at HEAD (`wx_shell/connection/connection_dialog/terminal/terminal_webview/jobs/local_files/remote_files_view/directories_view/transfer_workspace/editor/editor_view/plugins/plugins_view/settings/settings_view/logs_view/updater_view`); no historical name phantomed | VERIFIED |
| `HPC-W01-TRUTH-007…021` | scope boundaries (startup/profile, connection, terminal, local, remote/SFTP, transfers, editor, jobs/Slurm, plugins/providers, settings, updater, menus/toolbars/dialogs, compat runtime, provider caps, packaging) | every boundary inventoried in W01 report + W04 freeze rows; this session re-observed shell (7 tabs, 5 menus) via `EV-W05-GUI-001` | VERIFIED (15/15) |
| `HPC-W01-TRUTH-022…025` | non-scope (no broad fixes, no code-exists=SUPPORTED, no legacy removal, no capability reclass without live contract) | zero product-behavior edits; no disposition changed; legacy Qt surface untouched | VERIFIED (4/4) |
| `HPC-W01-TRUTH-026` | failure mode 4: no SUPPORTED from source wiring while W08 owns proof | sweep of all 24 SUPPORTED freeze rows: interactive Plugin Manager surfaces (`PLUGIN-BROWSE/MANAGE/UPDATES/ROOTS`) are `EXPERIMENTAL`, installer is `REQUIRES_EXTERNAL_VALIDATION`; SUPPORTED provider rows (`PROVIDER-LABEL/SELECTOR/VALIDATION/QUOTA`, `CAPS-DECLARED`) carry source-contract + GUI/contract-test evidence and their `→ W08` gaps are packaged-discovery *replay*, not missing required backend proof (Required class is source-contract/GUI, not package lifecycle) | VERIFIED — no premature SUPPORTED, no demotion needed |
| `HPC-W01-TRUTH-073` | plugin `develop` HEAD fetched and recorded | `EV-W05-PIN-001`: both repos pinned to remote tips, recorded here | VERIFIED |
| `HPC-W01-TRUTH-074/075` | unfetched plugin ⇒ provider rows NOT EVIDENCED/BLOCKED; no GO on mandatory rows | fetch gate satisfied, so no row is NOT EVIDENCED on this ground | VERIFIED (antecedent false, gate PASS) |
| `HPC-W01-TRUTH-084` | one canonical W01 report; `W01_COMPLETION_REPORT.md` + `WAVE_01_SESSION_REPORT.md` as separate authorities forbidden | three tracked competitors neutralized (see §Canonical-report closeout); single decision-owner = `docs/wave-reports/v2/opencode/W01_WAVE_REPORT.md` | VERIFIED — CLOSED by this session |
| `HPC-W01-TRUTH-085/086/088/089` | canonical owns final decision, severity counts, resume state, final audit | all four present in `W01_WAVE_REPORT.md` (PASS; P0 0/P1 0; resume; audit PASS) | VERIFIED |
| `HPC-W01-TRUTH-087` | FIX-A/FIX-B proof ownership | SUPERSEDED_BY_HPC-GOV-017 — verify-only: carried, no quota applied | VERIFIED (superseded) |
| `HPC-W01-TRUTH-090` | complete inventory before selecting fixes | order honored: W01 full inventory + W04 freeze precede; this session selects zero fixes (governance only) | VERIFIED |
| `HPC-W01-TRUTH-091` | close post-FIX P0/P1 before GO | SUPERSEDED_BY_HPC-GOV-017 — verify-only: owned P0/P1 = 0, nothing left open | VERIFIED (superseded) |

## Owned TODO details (7)

| ID | Status | Decision / truth |
|---|---|---|
| `HPC-W01-TODO-W01-REPORT-001` | CLOSED | Exactly one canonical W01 report at `docs/wave-reports/v2/opencode/W01_WAVE_REPORT.md`. Three older files repointed to it with `SUPERSEDED (W05, 2026-09-18)` banners carrying no competing decision (see §Canonical-report closeout). |
| `HPC-W01-TODO-W01-LAUNCH-001` | CLOSED | Real wx launch evidence `EV-W05-GUI-001` (exit 0): 5 menus `Menu\|Plugins\|Help\|Language\|v1.5.9`, 7 tabs `Connection\|Terminal\|Jobs & Outputs\|Directories\|Files\|Script Editor\|Logs`, `STATUS=Ready`, About real dialog, controlled shutdown. Pytest alone not used as proof. |
| `HPC-W01-TODO-W01-SENSITIVITY-001` | SUPERSEDED_BY_HPC-GOV-017 | Verify-only: no FIX-A/FIX-B quota in this overlay; carried W01/W04 sensitivity evidence stands, nothing re-proven here. |
| `HPC-W01-TODO-W01-SHA-001` | CLOSED | Five-way SHA distinction recorded in §Repository truth; stale SHAs (`afd4fb1d`, `2c1c7ce9`, `4d609cd5`, `eb86dea6`) appear only inside superseded history, never as current. |
| `HPC-W01-TODO-W01-CONSISTENCY-001` | CLOSED | Agreement verified: canonical P0 0/P1 0 == freeze totals 24/17/11/2/2/0/0 (56) == findings (0 owned open) == TODO states == evidence exits (all 0). Old `~95 SUPPORTED` counts live only in superseded history. |
| `HPC-W01-TODO-CLI-SURFACE-001` | CLOSED | Release ships a CLI (`build/windows/hpc-client-cli.spec`, entry `src/hpc_gui/cli/__main__.py`). Live inventory `EV-W05-CLI-001`: groups `gui, version, commands, profile (list/show/create/update/delete/test), doctor (environment/connection/smoke), files (ls/stat/checksum/mkdir/upload/download/cp/mv/rm), edit, sh, run, terminal, interactive, jobs (list/status/accounting/lssrv/submit/cancel)` + 15 root aliases + exit codes `0/1/2/3/124`. |
| `HPC-W01-TODO-CLI-SURFACE-002` | VERIFIED with honest deferral | Source-level legs proven: docs (`src/hpc_gui/docs/CLI_GUIDE_en.md`, `CLI_GUIDE_tr.md`, README §CLI), exit codes (`0 SUCCESS, 1 OPERATION_FAILED, 2 USAGE, 3 CONNECTION, 124 TIMEOUT`), JSON contract (`--format json version` live), profile/security rules (no-secret `list/show`, `--password-stdin`, `--no-saved-password`, `--strict-host-key`). Packaged-operation leg on the final release artifact is N/A in W05 (no artifact bound, no SHA cited) and routes to release waves (W10/W57); no packaged CLI claim is made here. |

## Mandatory source sections read

- `opencode/sources/WAVE_V2_FINAL_01.md` → Outcome (§14–16), Entry criteria (§32–37), Verified starting anchors (§39–64), Scope (§66–84), Explicit non-scope (§86–91), Known prior failure modes (§94–109, modes 1–10 incl. mode 4), W01-A (§320–329), W01-F (§410–429), W01-H (§432–448).
- Owned rows: `opencode/REQUIREMENT_REGISTRY.md` TRUTH-001…026, 073…075, 084…091. Owned TODOs: `opencode/TODO_OWNERSHIP_MAP.md` lines 7, 9, 12, 14, 15, 141, 142.
- Governance: `opencode/protocol/CORE_EXECUTION_RULES.md`. Wave contract: `waves/pending/W05.md` only.
- Live code inspected before edits: `wx_shell.py` (dispatch/anchors), `runtime.py` (default runtime), `pyproject.toml` (no `[project.scripts]`), `build/windows/hpc-client-cli.spec` (CLI packaging truth), `src/hpc_gui/cli/main.py` + `errors.py` (commands/exit codes), `artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md` (56 rows, failure-mode-4 sweep surface).

## Canonical-report closeout (TRUTH-084 / REPORT-001)

Single decision-owner: `docs/wave-reports/v2/opencode/W01_WAVE_REPORT.md` (PASS, current pins). Neutralized competitors (history preserved, zero competing decisions remain):

1. `artifacts/v2-final/W01/W01_COMPLETION_REPORT.md` — banner repointed from the stale R5 path to the overlay canonical.
2. `artifacts/v2-final/W01/WAVE_01_SESSION_REPORT.md` — banner repointed likewise.
3. `docs/wave-reports/v2/WAVE_V2_FINAL_01_REPORT.md` — prepended `SUPERSEDED (W05, 2026-09-18)` banner (was a BLOCKED/NO-GO snapshot on stale pins `2c1c7ce9`/`4d609cd5` with `W01-PLUGIN-PIN-001` open; that P1 is CLOSED by current pin truth).

## Tests and evidence

| Evidence | Exact command | Timestamp | Exit | Result |
|---|---|---|---|---|
| `EV-W05-PIN-001` repo pins (re-verified repair 1) | `git rev-parse HEAD`, `git status --porcelain=v1 --untracked-files=all`, `git diff --stat/--numstat/--check`, `git ls-remote origin refs/heads/develop` (main) + `git -C D:/Projeler/hpc-client-gui-plugins {rev-parse,branch,status,ls-remote}` | 2026-09-19T18:1x+03:00 | 0 | main `develop 0f8902a023bac76071527232c2287af96478ed2b` == remote tip (unchanged); plugin `develop f0abb7e7037e66ab451d463c699fecf4e00c89eb` == remote tip; plugin tree clean except untracked `.github/social-preview.jpg` (preserved) |
| `EV-W05-PIN-001` repo pins (original) | same commands | 2026-09-18T22:37–22:38+03:00 | 0 | same pins (unchanged across repair 1) |
| `EV-W05-BASE-001` narrow baseline (pre-edit) | `python -m pytest tests/test_w04_support_freeze.py -q -p no:cacheprovider -k "matrix__"` | 2026-09-18T22:37+03:00 | 0 | 8 passed, 20 deselected |
| `EV-W05-REBIND-001` freeze pins re-run on current tree (repair 1) | `python -m pytest tests/test_w04_support_freeze.py -q -p no:cacheprovider -k "matrix__"` | 2026-09-19T18:1x+03:00 | 0 | 8 passed, 20 deselected — binds freeze evidence to the recaptured 14-mod tree |
| `EV-W05-GUI-001` real wx launch/runtime probe (original) | `python C:\Users\mskomek\AppData\Local\Temp\opencode\w05_probe.py` (Temp, outside repo; real `wx.App` + `create_shell_frame(defer_terminal_webview=True)` + real `EVT_MENU` About routing with `ShowModal` intercepted only at the modal boundary + controlled shutdown) | 2026-09-18T22:41+03:00 | 0 | `W05_TOP_MENUS=Menu\|Plugins\|Help\|Language\|v1.5.9`, `W05_TABS=Connection\|Terminal\|Jobs & Outputs\|Directories\|Files\|Script Editor\|Logs`, `W05_STATUS=Ready`, `W05_ABOUT_DIALOG=PASS`, `W05_GUI_PROBE=PASS` (non-fatal duplicate image-handler noise only) |
| `EV-W05-GUI-002` real wx re-probe on current tree (repair 1) | `python C:\Users\mskomek\AppData\Local\Temp\opencode\w05_repair1_probe.py` (Temp, outside repo; `load_language("en")` + real `wx.App` + `create_shell_frame(defer_terminal_webview=True)` + menubar/notebook/status enumeration via `GetMenuBar`/`GetPageText`/`GetStatusBar().GetStatusText()` + real `EVT_MENU` About routing with `show_about` intercepted only at the modal boundary + controlled shutdown) | 2026-09-19T18:1x+03:00 | 0 | `W05_TOP_MENUS=Menu\|Plugins\|Help\|Language\|v1.5.9`, `W05_TABS=Connection\|Terminal\|Jobs & Outputs\|Directories\|Files\|Script Editor\|Logs` (7 tabs), `W05_STATUS=Ready`, `W05_ABOUT_DIALOG=PASS`, `W05_GUI_PROBE=PASS` (identical to GUI-001 modulo non-fatal duplicate image-handler noise + trailing `UnregisterClass 0x584` teardown noise, exit 0) — binds GUI evidence to the recaptured tree |
| `EV-W05-CLI-001` CLI surface inventory (source runtime) | `python -m hpc_gui.cli commands`, `python -m hpc_gui.cli version`, `python -m hpc_gui.cli --format json version` | 2026-09-18T22:38+03:00 | 0 | full group/alias inventory + exit-code table + `version: 1.5.9` text/JSON parity |
| `EV-W05-CLI-002` CLI re-inventory on current tree (repair 1) | `python -m hpc_gui.cli commands` (+ `version`, `--version`, `python --version`, wx version) | 2026-09-19T18:1x+03:00 | 0 | same groups/aliases/exit codes `0/1/2/3/124`, `version: 1.5.9`, `Python 3.12.4`, `wxPython 4.3.1` — binds CLI evidence to the recaptured tree |
| `EV-W05-AFTER-001` post-edit freeze pins | same as BASE-001 | 2026-09-18T22:42+03:00 | 0 | 8 passed, 20 deselected |
| `EV-W05-IMPACT-001` CLI lanes (original) | `python -m pytest tests/test_cli.py tests/test_cli_entrypoint.py -q -p no:cacheprovider` | 2026-09-18T22:42+03:00 | 0 | 164 passed |
| `EV-W05-IMPACT-002` CLI lanes re-run on current tree (repair 1) | same as IMPACT-001 | 2026-09-19T18:1x+03:00 | 0 | 164 passed — binds impact evidence to the recaptured tree |

Evidence classes: required class for W05 is `GUI` — satisfied by `EV-W05-GUI-001` (real wx event/runtime). Package class: N/A with justification (no artifact bound; package-dependent rows defer to W08/W10; no SHA-256 cited). External class: N/A (backend rows carry `REQUIRES_EXTERNAL_VALIDATION` with owner waves; no live-cluster claim). No test weakening, no new skips/xfails, no mocks standing in for behavior under test (modal-boundary capture only, same legitimate boundary as W04).

## Diff review (recaptured 2026-09-19, repair cycle 1 — closes DEF-W05-001)

Verbatim `git status --porcelain=v1 --untracked-files=all` (2026-09-19T18:1x+03:00, HEAD `0f8902a0`, branch `develop`):

```text
M CONTRIBUTING.md
M README.md
M artifacts/v2-final/W01/W01_COMPLETION_REPORT.md
M artifacts/v2-final/W01/WAVE_01_SESSION_REPORT.md
M docs/wave-reports/v2/WAVE_V2_FINAL_01_REPORT.md
M src/hpc_gui/i18n/en.json
M src/hpc_gui/i18n/tr.json
M src/hpc_gui/plugins/loader.py
M src/hpc_gui/plugins/validator.py
M src/hpc_gui/services/connection_controller.py
M src/hpc_gui/wx_connection.py
M src/hpc_gui/wx_settings_view.py
M src/hpc_gui/wx_shell.py
M tests/test_wave10_release_gate.py
?? artifacts/v2-final/W02/OWNERSHIP_MAP.md
?? artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md
?? docs/wave-reports/v2/opencode/W01_AUDIT_REPORT.md
?? docs/wave-reports/v2/opencode/W01_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W02_AUDIT_REPORT.md
?? docs/wave-reports/v2/opencode/W02_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W03_AUDIT_REPORT.md
?? docs/wave-reports/v2/opencode/W03_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W04_AUDIT_REPORT.md
?? docs/wave-reports/v2/opencode/W04_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W05_AUDIT_REPORT.md
?? docs/wave-reports/v2/opencode/W05_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W06_AUDIT_REPORT.md
?? docs/wave-reports/v2/opencode/W06_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W07_AUDIT_REPORT.md
?? docs/wave-reports/v2/opencode/W07_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W08_AUDIT_REPORT.md
?? docs/wave-reports/v2/opencode/W08_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W09_AUDIT_REPORT.md
?? docs/wave-reports/v2/opencode/W09_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W10_AUDIT_REPORT.md
?? docs/wave-reports/v2/opencode/W10_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W11_AUDIT_REPORT.md
?? docs/wave-reports/v2/opencode/W11_WAVE_REPORT.md
?? hpc-client-gui.ffs_gui
?? sync.ffs_db
?? src/hpc_gui/core/wx_errors.py
?? tests/test_w03_settings_provider_inventory.py
?? tests/test_w04_support_freeze.py
?? tests/test_w08_schema_isolation.py
?? tests/test_w09_main_plugin_compat.py
?? tests/test_w11_ssh_lifecycle.py
?? tests/test_wx_dispatch_error_gov.py
```

Verbatim `git diff --stat` (same instant; CRLF advisory warnings only, see check):

```text
CONTRIBUTING.md                                  |  15 ++-
README.md                                        |   3 +-
artifacts/v2-final/W01/W01_COMPLETION_REPORT.md  |   6 +-
artifacts/v2-final/W01/WAVE_01_SESSION_REPORT.md |   6 +-
docs/wave-reports/v2/WAVE_V2_FINAL_01_REPORT.md  |   6 ++
src/hpc_gui/i18n/en.json                         |   8 +-
src/hpc_gui/i18n/tr.json                         |   8 +-
src/hpc_gui/plugins/loader.py                    |   8 +-
src/hpc_gui/plugins/validator.py                 |  56 ++++++-----
src/hpc_gui/services/connection_controller.py    |  25 ++++-
src/hpc_gui/wx_connection.py                     |  72 ++++++++++++-
src/hpc_gui/wx_settings_view.py                  |  29 ++++--
src/hpc_gui/wx_shell.py                          | 122 ++++++++++++++++-------
tests/test_wave10_release_gate.py                |  22 +++-
14 files changed, 301 insertions(+), 85 deletions(-)
```

Verbatim `git diff --numstat` (same instant):

```text
11	4	CONTRIBUTING.md
2	1	README.md
4	2	artifacts/v2-final/W01/W01_COMPLETION_REPORT.md
4	2	artifacts/v2-final/W01/WAVE_01_SESSION_REPORT.md
6	0	docs/wave-reports/v2/WAVE_V2_FINAL_01_REPORT.md
7	1	src/hpc_gui/i18n/en.json
7	1	src/hpc_gui/i18n/tr.json
7	1	src/hpc_gui/plugins/loader.py
33	23	src/hpc_gui/plugins/validator.py
24	1	src/hpc_gui/services/connection_controller.py
71	1	src/hpc_gui/wx_connection.py
19	10	src/hpc_gui/wx_settings_view.py
88	34	src/hpc_gui/wx_shell.py
18	4	tests/test_wave10_release_gate.py
```

Verbatim `git diff --check` (same instant): exit 0; output is only the four pre-existing LF→CRLF advisories (`W01_COMPLETION_REPORT.md`, `WAVE_01_SESSION_REPORT.md`, `en.json`, `tr.json`); zero whitespace errors.

Per-entry attribution (preserve, not absorb — W05 touches nothing else):

- **W05-owned (3 tracked):** `artifacts/v2-final/W01/W01_COMPLETION_REPORT.md`, `artifacts/v2-final/W01/WAVE_01_SESSION_REPORT.md`, `docs/wave-reports/v2/WAVE_V2_FINAL_01_REPORT.md` — SUPERSEDED-banner governance edits only (§Canonical-report closeout). This report + `W05_AUDIT_REPORT.md` are the only other W05 files (untracked canonical pair, `??` above).
- **Foreign concurrent tracked (11, preserved):** `CONTRIBUTING.md`, `README.md` (docs lanes, other waves); `src/hpc_gui/i18n/en.json`, `tr.json` (i18n lanes); `src/hpc_gui/plugins/loader.py`, `validator.py` (plugin/provenance lanes, W08/W09); `src/hpc_gui/services/connection_controller.py`, `src/hpc_gui/wx_connection.py`, `src/hpc_gui/wx_settings_view.py`, `src/hpc_gui/wx_shell.py` (wx behavior lanes, W03/W06/W07+); `tests/test_wave10_release_gate.py` (W10). W05 makes no behavior claim over them and reverts none; re-run evidence (`EV-W05-REBIND-001`, `EV-W05-GUI-002`, `EV-W05-IMPACT-002`, `EV-W05-CLI-002`) is bound to this exact tree instead.
- **Untracked (preserved, not absorbed):** `artifacts/v2-final/W02/OWNERSHIP_MAP.md` → W02; `artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md` → W04 (W05 reads, never edits); `docs/wave-reports/v2/opencode/W01–W04, W06–W11` report pairs → their owner Waves (W05 owns only the W05 pair); `hpc-client-gui.ffs_gui`, `sync.ffs_db` → local FFSync sidecars; `src/hpc_gui/core/wx_errors.py`, `tests/test_wx_dispatch_error_gov.py` → dispatch-error governance lane (W03 family); `tests/test_w03_settings_provider_inventory.py` → W03; `tests/test_w04_support_freeze.py` → W04; `tests/test_w08_schema_isolation.py` → W08; `tests/test_w09_main_plugin_compat.py` → W09; `tests/test_w11_ssh_lifecycle.py` → W11.
- Secret safety (re-checked repair 1): no credentials, `.env`, keys, PEM/PFX, `.ssh`, tokens, or secret directories in diff, probe scripts (both live in Temp, outside the repo), fixtures, or reports. Probe scripts never enter the repo.

Supersedes the stale 2026-09-18 §Diff review paragraph (7 tracked mods) that caused `DEF-W05-001`.

## Findings and ownership routing (repair cycle 1)

- `DEF-W05-001` (P1, owned, Luna audit REOPEN 2026-09-19: report/diff identity stale) — **CLOSED** by this recapture + evidence rebind (`EV-W05-REBIND-001`, `EV-W05-GUI-002`, `EV-W05-CLI-002`, `EV-W05-IMPACT-002`, fresh pins). No product defect was found; no product edit was needed or made.
- In-scope P0/P1 opened: 0 (besides the now-closed `DEF-W05-001`). New defects introduced: 0. Zero-defect PASS remains valid per `HPC-GOV-017`.
- The stale-pointer/`BLOCKED`-snapshot condition (REPORT-001) was the owned blocker and is CLOSED above.
- Cross-wave: nothing absorbed. `DEF-W03-001` → W37, `DEF-W03-002` → W35, packaged CLI operation → W10/W57, wx runtime cutover → W10/W56–W57, plugin `develop` evolution → W08/W09: cited, untouched.

## Resume state

Completed: all 35 MANDATORY + 2 SUPERSEDED IDs and 7 TODOs traced and evidenced; pins current (`0f8902a0` == `origin/develop`, plugin `f0abb7e7` == plugin `origin/develop`, re-verified 2026-09-19); anchors rediscovered; mode-4 sweep clean; canonical-report singularity restored; launch + CLI inventory proven **and rebound to the recaptured 14-mod tree** (`EV-W05-REBIND-001` 8 passed / `EV-W05-GUI-002` PASS / `EV-W05-CLI-002` parity / `EV-W05-IMPACT-002` 164 passed); `DEF-W05-001` CLOSED; reports current.
In progress: none. Open P0/P1 (owned): 0. Pending tests/evidence: none for this Wave — fresh-context re-audit is the only remaining step.
In progress: none. Open P0/P1 (owned): 0. Pending tests/evidence: none for this Wave.
Next: none in this Wave — stop. `W06` may be planned only after its dependency/prerequisite checks are revalidated; this session starts nothing.
