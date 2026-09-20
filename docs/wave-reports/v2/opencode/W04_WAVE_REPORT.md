# W04 Wave Report — Support classification and evidence matrix

Wave: `W04`
Canonical report path: `docs/wave-reports/v2/opencode/W04_WAVE_REPORT.md`
Repository: `mskomek/hpc-client-gui`
Branch: `develop`
Baseline SHA: `0f8902a023bac76071527232c2287af96478ed2b`
Current HEAD: `0f8902a023bac76071527232c2287af96478ed2b`
Tested implementation state: `HEAD 0f8902a0` + working-tree W04 implementation (FIX-W04-A carried from session entry; FIX-W04-B authored and verified by the repair cycle — see Fixes)
Plugin/external repo SHA(s): carried (`..\hpc-client-gui-plugins` on `develop` / `f0abb7e7037e66ab451d463c699fecf4e00c89eb`); not re-pinned by this session, no plugin change in scope (plugin working tree holds only `?? .github/social-preview.jpg`, preserved)
First started: 2026-09-18
Last updated: 2026-09-19 (UTC) — repair cycle 1 (max 2) for Luna audit REOPEN `DEF-W04-002`
Session status: COMPLETE (repair cycle 1)
Wave decision: PASS (pending fresh-context audit)
Executable authority: `waves/pending/W04.md` (exactly one copy; `waves/pending/` holds W01–W61, 61 files, no gaps/duplicates; `waves/bak/` never read for execution)
Execution model: `opencode-go/muse-spark-1.3-contributor`
Dependency: `W03` — `docs/wave-reports/v2/opencode/W03_WAVE_REPORT.md` decision `PASS`, audit `PASS`; entry revalidated (same pins, no owned W03 blocker touches this scope)

## Owned requirements and TODO details

34 source-derived requirements + 3 TODO details. All VERIFIED (frozen + pinned by contract tests + GUI proof). Two in-scope defects found and closed (`DEF-W04-001` / FIX-W04-A; `DEF-W04-002` / FIX-W04-B); two cross-wave observations remain routed, not absorbed.

| ID | Kind | Status |
|---|---|---|
| `HPC-W01-TRUTH-047` | SUPPORTED vocabulary | VERIFIED — freeze §Disposition vocabulary; `test_matrix__supported_means_evidence_backed` |
| `HPC-W01-TRUTH-048` | EXPERIMENTAL vocabulary | VERIFIED — every EXPERIMENTAL row carries an open gap; same test |
| `HPC-W01-TRUTH-049` | REQUIRES_EXTERNAL_VALIDATION vocabulary | VERIFIED — REV rows require external/package evidence; `test_matrix__rev_means_backend_dependent` |
| `HPC-W01-TRUTH-050` | HIDDEN vocabulary | VERIFIED — 0 rows, justified (no hidden-with-implementation surface at HEAD); exact-totals pin |
| `HPC-W01-TRUTH-051` | UNSUPPORTED vocabulary | VERIFIED — 0 rows, justified (no visible-but-disowned surface); exact-totals pin |
| `HPC-W01-TRUTH-052` | DEPRECATED vocabulary | VERIFIED — 2 rows (migration-only keys); exact-totals pin |
| `HPC-W01-TRUTH-053` | NOT-IN-V2 vocabulary | VERIFIED — 2 rows (`APP-QUICKTOUR` + `DEC-W01-QUICKTOUR`, `APP-PALETTE-STANDALONE` + `DEC-W01-PALETTE`) |
| `HPC-W01-TRUTH-054` | REV-vs-EXPERIMENTAL rule + SUPPORTED evidence rule | VERIFIED — REV/backend-dependence pin + SUPPORTED/evidence pin |
| `HPC-W01-TRUTH-055` | required matrix columns | VERIFIED — 13 required columns + 14th Decision ID; `test_matrix__has_all_required_columns` |
| `HPC-W01-TRUTH-056` | every visible action has an ID; removals retain ID + disposition | VERIFIED — dispatch-literal ledger test + `test_matrix__removed_baseline_actions_retain_disposition` |
| `HPC-W01-TRUTH-057` | test-matrix layers | VERIFIED — §Test-matrix coverage maps all 7 layers to W04 proof |
| `HPC-W01-TRUTH-058` | static discovery | VERIFIED — every `_dispatch("…")` literal resolves to a freeze row |
| `HPC-W01-TRUTH-059` | event binding | VERIFIED — real `EVT_MENU` → canonical owner routing test (Settings/About/Help/Send-Logs/Update/Plugins) |
| `HPC-W01-TRUTH-060` | service path | VERIFIED — routing asserts canonical owner invoked with shell parent |
| `HPC-W01-TRUTH-061` | settings truthfulness | VERIFIED — `WxSettingsModel` round-trip + `KeyError` pins; `SET-DLG` honestly EXPERIMENTAL with `DEF-W03-001` → W37 |
| `HPC-W01-TRUTH-062` | plugin/provider contract | VERIFIED — `can_execute_action` allow/refuse pins + capability-gate GUI test |
| `HPC-W01-TRUTH-063` | runtime proof | VERIFIED — `EV-W04-GUI-001`: launch (7 pages, 5 menus, `Ready`), About real dialog, stale plugin click → coded error, controlled shutdown |
| `HPC-W01-TRUTH-064` | packaging honesty | VERIFIED — N/A with justification: no artifact bound, no SHA cited; every package-dependent row defers to W08/W10 |
| `HPC-W01-TRUTH-065` | disabled action at wrong lifecycle | VERIFIED — capability-lacking actions render disabled AND unbound; forced event delivery is a provable no-op |
| `HPC-W01-TRUTH-066` | action available while disconnected | VERIFIED — terminal without session warns visibly + returns `ID_CANCEL`, never a dead frame |
| `HPC-W01-TRUTH-067` | stale menu/context state after reconnect | VERIFIED — Plugins menu rebuilds on every `EVT_MENU_OPEN`; stale click → visible coded `PLUGIN-XXXXXX` error (FIX-W04-A) |
| `HPC-W01-TRUTH-068` | provider capability shown when lacking | VERIFIED — contract refusal + disabled/unbound menu + remote context filtering |
| `HPC-W01-TRUTH-069` | duplicated command, divergent handlers | VERIFIED — header Upload/Download funnel into the same panel `run_action` paths (single-path pin); FIX-W04-B: the download leg now forwards the panel's ambient selection + directory exactly like the remote toolbar path (bare `run("download")` raised `TypeError` on every click) |
| `HPC-W01-TRUTH-070` | destructive/non-destructive label semantics | VERIFIED — local + remote Delete both require `YES_NO` + `ICON_WARNING` confirm; labels match |
| `HPC-W01-TRUTH-071` | dead localization keys masking UI | VERIFIED — `menu.quick_tour` / `menu.command_palette` resolve but bind to no wx item (`help_items["tour"] is None`) |
| `HPC-W01-TRUTH-072` | log-only error paths, success-looking UI | VERIFIED — `_dispatch` branches governed (W02 carried); `_wx_dispatch_plugin_action` stale + exception paths now visible coded errors (FIX-W04-A) |
| `HPC-W01-TRUTH-076` | W01-C final disposition for baseline-visible features | VERIFIED — `APP-QUICKTOUR` + `APP-PALETTE-STANDALONE` retained as `NOT-IN-V2` with decision IDs; `NOT-IN-V2 = 0` avoided |
| `HPC-W01-TRUTH-077` | W01-D verification ownership | VERIFIED — every row names a verification-owner Wave or is a fully-proven native/local SUPPORTED row with no gap |
| `HPC-W01-TRUTH-078` | W01-E removed-ghost absence test | VERIFIED — `test_quicktour__absent_from_wx_help_menu` |
| `HPC-W01-TRUTH-079` | W01-E removed-dispatch unreachability test | VERIFIED — `test_quicktour__no_dispatch_reaches_ui` (no dialog, no window) |
| `HPC-W01-TRUTH-080` | W01-E fault-injection sensitivity | VERIFIED — `test_quicktour__absence_detector_is_sensitive` (restored ghost trips detector; removal restores green) |
| `HPC-W01-TRUTH-081` | W01-E replacement event/dispatch routing test | VERIFIED — About reached via real `EVT_MENU`; `test_menu_events__route_to_canonical_owners` |
| `HPC-W01-TRUTH-082` | W01-E replacement visible-contract test | VERIFIED — About dialog carries version + 4 required actions; `test_about__visible_contract_fields` |
| `HPC-W01-TRUTH-083` | W01-E sensitivity vs previous implementation | VERIFIED — pre-FIX-W01-002 MessageBox impl cannot satisfy the dialog contract; `test_about__contract_detector_is_sensitive` |
| `HPC-W01-TODO-W01-DISPOSITION-001` | removed/hidden/deferred features stay ledgered | VERIFIED — baseline-removed rows retain ID + disposition + decision ID + owner |
| `HPC-W01-TODO-W01-SUPPORT-EVIDENCE-001` | disposition separated from evidence class + owner/gap columns | VERIFIED — `Required` vs `Current` evidence columns distinct; every row carries verification owner + open gap |
| `HPC-W01-TODO-W01-GUI-PROOF-001` | visible remediation has GUI event/runtime proof | VERIFIED — FIX-W04-A has real-event regression tests + `EV-W04-GUI-001` runtime proof, not static assertions alone |

## Mandatory source sections read

- `opencode/sources/WAVE_V2_FINAL_01.md:263–279` → Workstream E — Freeze support classification (7 states; SUPPORTED evidence rule; REV/EXPERIMENTAL split; removals stay ledgered).
- `opencode/sources/WAVE_V2_FINAL_01.md:281–288` → Required support matrix (13-column minimum; every visible action has an ID; removals retain ID + disposition).
- `opencode/sources/WAVE_V2_FINAL_01.md:290–300` → Test matrix (7 layers incl. packaging-deferral rule).
- `opencode/sources/WAVE_V2_FINAL_01.md:302–313` → Negative/edge cases (8 checks; log-only-error rule).
- `opencode/sources/WAVE_V2_FINAL_01.md:348–366` → W01-C (baseline ledger; ghost removal → HIDDEN/UNSUPPORTED/NOT-IN-V2; `NOT-IN-V2 = 0` invalid on silent removal).
- `opencode/sources/WAVE_V2_FINAL_01.md:368–394` → W01-D (verification-owner minimum columns; no premature SUPPORTED).
- `opencode/sources/WAVE_V2_FINAL_01.md:396–408` → W01-E (ghost-absence + dispatch-absence + fault-injection; replacement routing + contract + prior-impl sensitivity).
- Owned rows: `opencode/REQUIREMENT_REGISTRY.md` TRUTH-047…072/076…083; `opencode/REQUIREMENT_WAVE_INDEX.md` (34 W04 rows); `opencode/TODO_OWNERSHIP_MAP.md` (3 W04 TODO rows).
- Live code inspected before any conclusion (source wording = requirement, code = implementation truth): `src/hpc_gui/wx_shell.py` (dispatch + `_wx_dispatch_plugin_action` + `_dispatch` error-governance branches), `src/hpc_gui/core/wx_errors.py` (`report_wx_action_error`), `src/hpc_gui/i18n/en.json` + `tr.json` (new failure keys), `artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md` (56 rows + totals + verdicts), `tests/test_w04_support_freeze.py` (28 tests, sections A–J).

## Discovery pass (before first conclusion)

- Pinned `develop 0f8902a0` (== `origin/develop` tip per controller handoff); plugin `f0abb7e7` carried, not re-fetched (read-only here).
- Working tree at entry already held the W04 implementation (FIX-W04-A in `wx_shell.py`, `wx_errors.py` helper, en/tr failure keys, 56-row freeze artifact, 28-test pin suite) plus concurrent/pre-existing changes (`CONTRIBUTING.md`, `README.md`, `wx_settings_view.py`, `test_wave10_release_gate.py`, W02/W03 artifacts, FFSync sidecars) — all preserved byte-for-byte, none reverted; this session made zero product edits and authored no new repo test file.
- Bounded plan followed: pin + baseline, requirement → owner → test → evidence trace, minimal in-scope fix already present (verified, not assumed), GUI-class real-wx probe mandatory and run, no mocks for behavior-under-test, no test weakening, cross-Wave defects routed with IDs. Repair cycle 1 (2026-09-19): Luna REOPEN `DEF-W04-002` reproduced (90s TIMEOUT), diagnosed via Temp probe (native `FileDialog` boundary hit, routing intact), fixed with the smallest coherent change (FIX-W04-B: one `_header_download` handler hunk + one test-boundary helper; assertions unchanged), and re-proven (28/28 in 15.51s + probe PASS + 53/24 impact lanes).
- `wxPython 4.3.1 msw (phoenix) wxWidgets 3.3.3` present; `Python 3.12.4` active truth.

## Frozen truth (summary; canonical bytes in the freeze artifact)

- `artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md`: 56 rows — SUPPORTED 24 / EXPERIMENTAL 17 / REQUIRES_EXTERNAL_VALIDATION 11 / DEPRECATED 2 / NOT-IN-V2 2 / HIDDEN 0 (justified) / UNSUPPORTED 0 (justified). Supersedes `artifacts/v2-final/W01/SUPPORT_MATRIX.md` counts as current truth (history preserved).
- Negative/edge-case verdicts frozen with test pins for all 8 TRUTH-065…072 cases; test-matrix coverage frozen for all 7 TRUTH-057…064 layers (packaging N/A with W08/W10 deferral justification).
- Cross-wave gaps cited, not absorbed: `DEF-W03-001` → W37 (shell Apply persists nothing), `DEF-W03-002` → W35 (plugin search/refresh unimplemented).

## WAVE_FINDINGS

| Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status |
|---|---|---|---|---|---|---|---|---|
| `DEF-W04-001` | P1 (owned) | `_wx_dispatch_plugin_action` (dynamic plugin menu dispatch, `wx_shell.py`) | pre-fix source: `plugin is None → return` + `except → log-warning only` | stale-click/exception paths invisible; UI left success-looking | user clicks a plugin action and nothing happens with no diagnosis | FIX-W04-A: both paths report visible coded `PLUGIN-XXXXXX` errors via `report_wx_action_error` (+ `plugins.action_failed` keys en/tr); dispatcher exposed as `frame._wx_dispatch_plugin_action` for the regression suite | YES (true owner W04) | CLOSED (regression + sensitivity + GUI proof) |
| `DEF-W04-002` | P1 (owned) | `test_header_upload_download__use_panel_run_actions` (TRUTH-069 pin) + `_header_download` wiring (`wx_shell.py`) | Luna fresh-context audit: isolated test emits wx duplicate image-handler noise and never terminates (60s; full suite stuck at 180/360s) while the prior report claimed 28/28 in ~6–100s | suite cannot complete; TRUTH-069 evidence not reproducible | auditor cannot reproduce green; header Download silently no-ops per click | FIX-W04-B (true owner W04, no cross-wave transfer defect — routing proven intact by diagnostic probe): (1) test stubs native `wx.FileDialog`/`wx.DirDialog` at the OS-modal boundary with `ID_CANCEL` (`_auto_cancel_native_selectors`; real button events/panels/run_action routing untouched); (2) product `_header_download` mirrors the remote toolbar handler, forwarding ambient selection + directory instead of bare `run("download")` (`TypeError` on every click) | YES (true owner W04) | CLOSED (isolated 1 passed 2.81s + full 28/28 in 15.51s + GUI probe PASS) |

No other in-scope defect: vocabulary, matrix, ledger, and negative cases are otherwise already truthful at HEAD (W01–W03 evidence carried, not re-proven).

## Fixes (FIX-W04-A present in tree at entry, verified — not authored — by the first session; FIX-W04-B authored + verified by repair cycle 1)

- FIX-W04-A (`DEF-W04-001` CLOSED): stale plugin-click path mints a fresh diagnostic code with the stale identity as technical detail; exception path reports through the same helper (structured traceback log preserved, no log detail lost). Both produce exactly one `MessageBox` carrying `PLUGIN-XXXXXX`; happy path dispatches once with no dialog. i18n: `plugins.action_failed` (en/tr) + `*_open_failed` keys for update/send-logs/settings/about/plugin-request paths routed through `_dispatch` (W02 error-governance carried, not weakened).
- FIX-W04-B (`DEF-W04-002` CLOSED, repair cycle 1): root cause is twofold, both W04-owned, no transfer defect elsewhere. (1) Test reached an undrivable native modal: header Upload with an empty local selection opens `wx.FileDialog.ShowModal()` (a native OS modal that blocks headlessly forever); the download leg can likewise reach `wx.DirDialog`. The test now auto-cancels both selectors at that boundary (`_auto_cancel_native_selectors`, returns `wx.ID_CANCEL`, records invocations, starts no transfer) — same legitimate category as the file's existing `MessageBox`/ `ShowModal` interceptions; real button events, real panels, real `run_action` wrappers and identical routing assertions retained. (2) Product `_header_download` called `run("download")` but remote `run_action(action, selected, target_dir)` requires `selected` — `TypeError` on every header Download click (swallowed/logged by the wx event machinery, leaving a silent no-op). It now mirrors the remote toolbar's `_on_toolbar_download`, forwarding the panel's ambient selection + directory from the exposed `_wx_remote_tabs` / `_wx_remote_notebook`, with an empty-selection fallback that terminates via the toolbar path's own early return. Total product delta: one handler (~22 lines); total test delta: one helper + one call + docstring boundary line; no assertion changed, no skip/xfail, no mock of behavior under test.

## Tests and evidence

| Evidence | Exact command | Exit | Result |
|---|---|---:|---|
| `EV-W04-BASE-001` narrow baseline (pre-conclusion) | `python -m pytest tests/test_w04_support_freeze.py -q -k "matrix__"` | 0 | 8 passed in 0.38s |
| `EV-W04-DEF002-REPRO-001` hang reproduction (repair cycle 1, pre-fix) | `python -m pytest tests/test_w04_support_freeze.py -q -p no:cacheprovider -k header_upload_download` | TIMEOUT | no output, no termination within 90s (confirms Luna audit: native `FileDialog` modal blocks headlessly) |
| `EV-W04-DEF002-DIAG-001` diagnostic probe (Temp, outside repo) | `python C:\Users\mskomek\AppData\Local\Temp\opencode\w04_def002_diag.py` (real shell frame, real button events, selectors stubbed to record + `ID_CANCEL`) | 0 | `DIAG_SELECTOR_HITS=['FileDialog']` (hang cause proven), `DIAG_SEEN=[('local','upload'),('remote','download')]` (routing intact — no transfer defect, true owner W04), `DIAG_DONE=terminated` |
| `EV-W04-DEF002-ISO-001` isolated pin after FIX-W04-B | `python -m pytest tests/test_w04_support_freeze.py -q -p no:cacheprovider -k header_upload_download` | 0 | 1 passed in 2.81s (was: never terminates) |
| `EV-W04-AFTER-002` support-freeze pin suite after FIX-W04-B, sections A–J (SUPERSEDES `EV-W04-AFTER-001`: the prior 28-in-100.87s / 6.55s figures were not reproducible in the audit context and are withdrawn) | `python -m pytest tests/test_w04_support_freeze.py -q -p no:cacheprovider` | 0 | 28 passed in 15.51s |
| `EV-W04-GUI-002` real wx event/runtime probe re-run after FIX-W04-B (SUPERSEDES `EV-W04-GUI-001` timings) | `python C:\Users\mskomek\AppData\Local\Temp\opencode\w04_gui_probe.py` (Temp, outside repo; real `wx.App`, real shell frame, real `EVT_MENU` via `ProcessEvent`, real dialog construction, `MessageBox` captured at the legitimate modal boundary, controlled shutdown) | 0 | `W04_GUI_PROBE=PASS`: 5 top-level menus, 7 tabs (`Connection\|Terminal\|Jobs & Outputs\|Directories\|Files\|Script Editor\|Logs`), status `Ready`, About real dialog (version + 4 actions), stale plugin click → exactly one coded `PLUGIN-XXXXXX` error naming the ghost id |
| `EV-W04-IMPACT-003` dispatch/governance + release-gate lanes re-run after FIX-W04-B (SUPERSEDES `EV-W04-IMPACT-001` timings) | `python -m pytest tests/test_wx_dispatch_error_gov.py tests/test_wave10_release_gate.py -q -p no:cacheprovider` | 0 | 53 passed in 3.07s |
| `EV-W04-IMPACT-004` shell/truth/sensitivity lanes re-run after FIX-W04-B (SUPERSEDES `EV-W04-IMPACT-002` timings) | `python -m pytest tests/test_wx_shell.py tests/test_wx_shell_w01_truth.py tests/test_w01_sensitivity.py -q -p no:cacheprovider` | 0 | 24 passed in 0.69s |
| Sensitivity (in-suite, W01-E) | included in `EV-W04-AFTER-002` | 0 | fault-injected Quick Tour trips the absence detector and removal restores green; legacy MessageBox About impl fails the dialog contract |

Environment: `Python 3.12.4`, `wxPython 4.3.1 msw (phoenix) wxWidgets 3.3.3`, Windows. Mock boundaries legitimate only: modal `wx.MessageBox` capture with real event routing/real helper/real structured log; native `wx.FileDialog`/`wx.DirDialog` auto-cancel with real event routing/real panels/real run_action wrappers (DEF-W04-002); view-layer call recorders (routing under test, not the view); `wx.CallAfter` inline only where the product posts to it; `wx.Dialog.ShowModal` interception for the About contract (real construction, real labels, no event loop). No product behavior under test replaced. No test weakening, no new skips/xfails, no fabricated output. Every cited suite ran after the final tree state (FIX-W04-B included).

## Second-defect search protocol (dimensions for the freeze surface)

1. negative paths — CHECKED: stale plugin click, dispatch exception, disconnected terminal, disabled capability items, destructive confirms, dead keys, log-only paths — all pinned.
2. lifecycle — CHECKED: probe + every GUI test uses controlled teardown (Close + yields + conditional Destroy); probe exits 0.
3. stale state — CHECKED: Plugins menu rebuilds on `EVT_MENU_OPEN`; reconnect staleness covered by rebuild + visible-error rule.
4. identity — CHECKED: stale identity named in the error's technical detail; `ErrorId` correlates dialog with structured log.
5. concurrency/race — N/A with justification: dispatch paths are UI-thread synchronous; no new threads introduced by FIX-W04-A.
6. boundary values — CHECKED: `ErrorId` format `PLUGIN-[0-9A-F]{6}` pinned by regex; happy-path silence pinned (exactly one dialog on failure, zero on success).
7. capability absence — CHECKED: contract + GUI + context-filter pins (TRUTH-068).
8. persistence — CHECKED: `SET-DLG` gap honestly ledgered to W37, not fixed or hidden here.
9. packaging — CHECKED: no artifact bound, no SHA cited; package rows defer to W08/W10 (TRUTH-064).
10. error visibility — CHECKED: the Wave's core finding (DEF-W04-001) closed; `_dispatch` branches governed.
11. context menus/secondary entry — CHECKED: header Upload/Download single-path pin; remote context label resolution pin.
12. adjacent integration boundary — CHECKED: callee call-sites untouched (zero product edits by this session); i18n en+tr carry the same new keys.

No second in-scope defect; nothing absorbed from other Waves.

## Diff review

- `git status --short`: repair cycle 1 adds exactly one tracked product hunk (`src/hpc_gui/wx_shell.py` `_header_download`, ~22 lines) plus test-boundary additions in the untracked-at-entry `tests/test_w04_support_freeze.py` (helper + call + docstring line) and this canonical report. All other entries (tracked modifications incl. i18n, `wx_settings_view.py`, docs; untracked `artifacts/v2-final/W04/`, `src/hpc_gui/core/wx_errors.py`, W02/W03 artifacts, FFSync sidecars) are pre-existing/concurrent — preserved untouched, none reverted.
- `git diff --stat` / `git diff --check`: reviewed; check clean (CRLF notices only, pre-existing). The `_header_download` hunk reviewed line-by-line (see Fixes); no other product file touched by this cycle.
- Secret safety: no credentials, `.env`, keys, PEM/PFX, `.ssh`, tokens, or secret directories in diff, probe/diagnostic scripts, fixtures, or reports. Probe + diagnostic scripts live in Temp, outside the repo.

## Findings and ownership routing

- In-scope P0/P1 opened across both cycles: 2 owned (`DEF-W04-001`, `DEF-W04-002`) — BOTH CLOSED with regression + sensitivity + GUI proof. `DEF-W03-001` → W37, `DEF-W03-002` → W35: routed, untouched, cited as open gaps — not absorbed.
- Cross-wave: nothing absorbed. Remote/package verification stays with W05–W11/W35/W37/W08/W10 per the freeze's verification-owner column (unchanged). `DEF-W04-002` diagnosis explicitly ruled out an underlying transfer defect (routing intact per `EV-W04-DEF002-DIAG-001`), so no routing to another Wave was warranted.
- New defects introduced: 0.

## Resume state

Completed and verified: all 34 owned IDs + 3 TODO details traced requirement → live implementation owner → test → evidence; 28-test pin suite + GUI probe + 77 impacted-lane tests green after the final tree state; Luna REOPEN `DEF-W04-002` reproduced, diagnosed, fixed (FIX-W04-B) and re-proven.
In progress: none. Open P0/P1: 0 (owned). Open P2/P3: 0 (owned).
Pending tests/evidence: none for this Wave — fresh-context re-audit pending (repair cycle 1 of max 2; cycle 2 reserved only if the re-audit reopens).
Last exact commands: see evidence table (`EV-W04-AFTER-002`, `EV-W04-GUI-002`, `EV-W04-IMPACT-003/004`, `EV-W04-DEF002-*-001`).
Next actions: none in this Wave — stop. `W05` may be planned only after its dependency/prerequisite checks are revalidated; this session starts nothing.
Evidence/artifact identities: implementation state `0f8902a0` + working-tree W04 implementation incl. FIX-W04-B; freeze `artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md` (56 rows); suite `tests/test_w04_support_freeze.py` (28 tests); probe `w04_gui_probe.py` + diagnostic `w04_def002_diag.py` (Temp, outside repo); no package artifact (N/A for W04).

## Final summary

```text
Support freeze: 56 rows (24/17/11/2/2/0/0) + vocabulary + verification owners + evidence-class separation + 8 negative verdicts + 7-layer test-matrix coverage
DEF: DEF-W04-001 (P1, stale/exception plugin-action failures silent — CLOSED via FIX-W04-A: visible coded PLUGIN-XXXXXX errors + en/tr keys)
DEF: DEF-W04-002 (P1, Luna REOPEN: TRUTH-069 pin hangs in native FileDialog modal; header Download arity TypeError — CLOSED via FIX-W04-B: OS-modal auto-cancel boundary + toolbar-mirroring _header_download)
Root cause (002): empty-selection header Upload opens undrivable wx.FileDialog.ShowModal(); bare run("download") never matched run_action(action, selected, target_dir)
Before EV: EV-W04-BASE-001 (8 structure pins green pre-conclusion); EV-W04-DEF002-REPRO-001 (90s TIMEOUT confirms hang) + EV-W04-DEF002-DIAG-001 (selector hit proven, routing intact)
After EV: EV-W04-AFTER-002 (28/28 in 15.51s), EV-W04-DEF002-ISO-001 (1/1 in 2.81s), EV-W04-GUI-002 (PASS, exit 0), EV-W04-IMPACT-003 (53), EV-W04-IMPACT-004 (24)
Regression test: tests/test_w04_support_freeze.py (boundary helper added; no assertion changed)
Sensitivity proof: in-suite W01-E pins (ghost fault-injection + legacy-About detector + dispatch ledger)
Additional fixes: FIX-W04-B only (one ~22-line handler + test boundary); unrelated tree changes preserved byte-for-byte
Post-green review: 12-dimension second-defect search stands; re-probed download arity via real-event diagnostic; residuals routed with owner IDs
New/modified tests: boundary helper + docstring line only; no existing assertion modified
Skipped/xfail changes: none
Package evidence: N/A (no artifact bound; package rows defer to W08/W10)
External evidence: N/A (backend rows carry REQUIRES_EXTERNAL_VALIDATION; no live-cluster claim here)
Open P0/P1: 0 (owned)
Open P2/P3: 0 (owned)
Wave decision: PASS (pending fresh-context re-audit)
```
