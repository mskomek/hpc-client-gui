# W42 Wave Report — Updater verification and installation progress

```text
Wave: W42
Canonical report path: docs/wave-reports/v2/opencode/W42_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui
Branch: develop
Baseline SHA: c8293d3ca309526ed250c794c3b294f7c54ef369
Current HEAD: c8293d3ca309526ed250c794c3b294f7c54ef369 (working-tree changes uncommitted; controller owns commit/integration)
Plugin/external repo SHA(s), if applicable: N/A (no plugin repo touched)
First started: 2026-09-24 (W42 run phase)
Last updated: 2026-09-24
Session status: READY FOR INDEPENDENT AUDIT
Wave decision: GO (worker-level; pending controller independent audit)
```

## Authority reads

1. `waves/pending/W42.md` (wave_id W42, execution kind, canonical_source W42, 19 source rows + 2 TODO rows, start gate NONE, cohort P7-updater-integrity, required evidence `GUI,PACKAGE`, integration refs W41/W43 non-blocking).
2. `opencode/REQUIREMENT_REGISTRY.md` rows owning Wave W42: `HPC-W09-UPD-029`..`038`, `051`, `052`, `066`, `067`, `077`, `078`, `082`, `083`, `084`.
3. `opencode/TODO_OWNERSHIP_MAP.md` rows owning Wave W42: `HPC-W09-TODO-UPDATER-LIFECYCLE-001` (ACTIVE), `HPC-W09-TODO-052` (ACTIVE, updater integrity + failure-path acceptance).
4. `opencode/sources/WAVE_V2_FINAL_09.md` → Workstream H — Verification (lines 223-231), Workstream I — Installation progress / splash (233-241), Targeted tasks TASK-W09-008/009 (267-268), Test matrix rows 286-287, Acceptance criteria 300-301, STOP conditions 308-310.
5. Live code before edits: `src/hpc_gui/services/update_verification.py` (Ed25519 `verify_signed_metadata`, `validate_update_url`, `verify_artifact`), `src/hpc_gui/services/app_updater.py` (`get_latest_release` signed-metadata gate, `download_and_verify_release`, `_VERIFIED_UPDATE_ARTIFACTS`, `launch_update_installer` re-verify, `build_update_script` real-progress + rollback PS1), `src/hpc_gui/wx_updater_view.py` (`WxUpdateDialog` states incl. VERIFYING/READY/INSTALLING splash, `show_installing_splash` 620×360).
6. Live tests before edits: `tests/test_update_verification.py`, `tests/test_app_updater.py`, `tests/test_wx_updater_spec.py`, `tests/test_updater_helper.py`, `tests/test_w41_updater_routing.py`, `tests/test_installation_context.py`, `tests/test_linux_update_handoff.py`, `tests/test_deb_installer.py`.

## Baseline capture

```text
Evidence ID: EV-W42-BASELINE
Commit: c8293d3ca309526ed250c794c3b294f7c54ef369
Branch: develop
git status: dirty (pre-existing sibling-wave M files preserved untouched; W42 adds zero product/test hunks — surface already valid, see discovery)
```

Content-identity note: the controller handoff cites `content_identity=965183e8...`. `waves/` is gitignored, so the pending spec lives outside Git history by program design. The worker proceeded on current repository truth without editing the spec; identity reconciliation is controller-owned.

Narrow baseline before edits is not separable from the shared dirty tree (parallel cohort shares one working tree on `develop`). The W42 worker baselined by focused suite: all updater/verification clusters below were green before any edit consideration and re-run after (no edits made) as the acceptance regression. No sibling file was reverted, merged, or cleaned by this worker.

Pre-existing dirty files NOT owned by W42 (preserved untouched): all `M` entries from sibling waves (settings/i18n/plugins/jobs/editor/logs/services — see `git status`; W26 editor identity in progress per program log). W42 touched zero product/test files.

## Discovery pass / WAVE_FINDINGS

```text
Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status
(no W42-owned defects found; every owned requirement traces to a live owner + pinned test — see trace table)
```

Targeted defect search (W42 surface only):
- Verification bypass: `get_latest_release` raises unless signed metadata verifies (`UPDATE_METADATA.json` mandatory, `verify_signed_metadata` with `TRUSTED_UPDATE_KEYS`, artifact match on file/platform/arch/kind + URL equality); `download_and_verify_release` raises without `signed_artifact` ("requires authenticated signed metadata"); `launch_update_installer` refuses without `_VERIFIED_UPDATE_ARTIFACTS` record AND re-runs `verify_artifact` immediately before any install path. No code path reaches `build_update_script`/`_launch_packaged_helper` with an unverified payload — STOP UPD-082/084 clear.
- Private key shipment: `grep -rn "Ed25519PrivateKey|BEGIN PRIVATE" src/hpc_gui/services/app_updater.py src/hpc_gui/services/update_verification.py` → zero hits; only `Ed25519PublicKey` verification + base64 public-key constant `TRUSTED_UPDATE_KEYS` ships. SSH private-key helpers (`ssh/client.py`) are user-key loaders, not updater signing keys. STOP UPD-083 clear.
- Wrong artifact/hash: `verify_artifact` pins both size equality and SHA-256 digest equality; corrupt cached archives are deleted + re-downloaded; download failures delete the file and raise. Pinned by `test_artifact_size_and_digest_are_verified`.
- Progress honesty: `_download` reports real `(downloaded, total)` counters per 1 MiB chunk; installer PS1 accumulates `$extractDone/$extractTotal` and `$copyDone/$copyTotal` per byte with monotonic guard `[Math]::Max($script:lastProgress,...)`; per-file status text is `("Extracting: " + $entry.FullName)` / `("Copying: " + $relative)` emitted while streaming that entry's bytes — never claims a file before its bytes flow (UPD-036 conditional satisfied by real-text path). Pinned by percentage/byte tests + `test_windows_installer_script_has_independent_real_progress_and_rollback`.
- Install splash first state: PS1 opens `Form "Application Update"` then `Set-UpdateProgress 0 "Preparing update..."` before any mutation; wx `show_installing_splash` opens 620×360 with `"Installing update..."` + 0%. Pinned.
- Cancel/close: Cancel button → `_cancel_download` → `cancelled()` polled per chunk → `DOWNLOAD_CANCELLED`; dialog `_on_close` during DOWNLOADING confirms cancel; close-in-flight and late-callback-after-close pinned with 0 destroyed-control callbacks (LIFECYCLE-001).
- Failure/rollback: PS1 try/catch restores `_internal` + exe backup, restarts prior app, shows failure MessageBox, writes `update-install.log`; helper paths (AppImage/macOS/deb/flatpak) have per-strategy rollback tests. Prior app stays usable. Pinned.
- Second-defect sweep result: no further W42-owned defects. No cross-scope defect fixed opportunistically.

## Implementation

### No-code-change classification (already-valid surface)

All 21 owned IDs trace requirement → live implementation owner → test → evidence with zero edits:

| Requirement | Live owner | Test (pinned) | Evidence |
|---|---|---|---|
| UPD-029 signed verification before install | `app_updater.get_latest_release` (mandatory signed metadata + `verify_signed_metadata`) | `test_signed_metadata_requires_known_key_and_valid_signature`, `test_metadata_rejects_duplicate_targets_and_non_https_urls` | signed envelope verifies before any download/install |
| UPD-030 bad signature blocks install | `verify_signed_metadata` Ed25519 verify + `download_and_verify_release` raise | tampered-signature raises "signature" (verification test) | bad signature cannot proceed |
| UPD-031 wrong artifact/hash blocks install | `verify_artifact` size+digest; cache re-verify; installer re-verify | `test_artifact_size_and_digest_are_verified`, `test_update_reuses_verified_download` | size/digest mismatch deletes + raises |
| UPD-032 public verification material packaged correctly | `TRUSTED_UPDATE_KEYS` public-key constant in shipped `app_updater.py`; metadata URL allowlist `ALLOWED_UPDATE_HOSTS` | `release_asset_names`/platform tests, metadata host tests | public key + allowlist ship with source; no fetch of untrusted hosts |
| UPD-033 private key never ships | no private key in `services/app_updater.py` + `update_verification.py` (grep-verified zero hits) | source-packaging proof (this report; static grep) | STOP UPD-083 clear |
| UPD-034 first state indicates installing | PS1 `Set-UpdateProgress 0 "Preparing update..."`; splash `"Installing update..."` | `test_windows_installer_script_has_independent_real_progress_and_rollback`, `test_update_install_opens_installation_splash` | splash first state pinned |
| UPD-035 progress reflects real work | real byte counters in `_download` + PS1 `$extractDone/$copyDone` + monotonic guard | `test_download_percentage_is_actual_package_percentage`, `test_installation_progress_uses_real_backend_progress`, PS1 script assertions | no fake percentage |
| UPD-036 fixed text must not pre-claim copy | per-file text emitted during that file's byte stream | PS1 text assertions (`Extracting: / Copying: ` inside read loop) | conditional satisfied |
| UPD-037 cancel/close defined | `_cancel_download`, `_on_close` confirm, lifecycle tests | `test_update_cancel_reaches_downloader`, `test_update_close_in_flight_safe`, `test_update_late_callback_after_close_safe` | cancel/close pinned |
| UPD-038 failure keeps prior app / rollback | PS1 backup+restore+relaunch; helper rollbacks | `test_appimage_rolls_back_when_new_process_fails`, `test_macos_rolls_back_after_failed_launch`, PS1 rollback assertions | rollback pinned |
| UPD-051 TASK-W09-008 negative tests | verification + reuse tests above | same as UPD-029..031 | negative coverage present |
| UPD-052 TASK-W09-009 progress/failure handling | progress + splash + failure tests | same as UPD-034..038 | handling coverage present |
| UPD-066 bad signature/hash matrix | automated, install blocked | verification tests + `test_install_without_verified_artifact_stays_failed` | matrix row green |
| UPD-067 install failure matrix | integration (helper + PS1 rollback) | updater_helper suite (10 tests) | matrix row green |
| UPD-077 gate: bad signature/hash cannot install | same chain as UPD-030/031 | same tests | gate closed |
| UPD-078 gate: progress represents actual stage | same chain as UPD-035 | same tests | gate closed |
| UPD-082 STOP: verification bypass | three independent gates (metadata/download/install) | refusal tests (`test_unpackaged_app_never_launches_installer`, install-without-artifact) | STOP clear |
| UPD-083 STOP: private key packaged | grep proof above | source-packaging proof | STOP clear |
| UPD-084 STOP: unverified payload replace | `_VERIFIED_UPDATE_ARTIFACTS` + re-verify before every installer path | refusal + re-verify tests | STOP clear |
| TODO-UPDATER-LIFECYCLE-001 close-in-flight safety | `_on_close` + cancelled flag + dead-parent probe | `test_update_close_in_flight_safe`, `test_update_late_callback_after_close_safe`, `test_closing_update_progress_cancels_active_download` | 0 destroyed-control callbacks |
| TODO-052 integrity + failure-path acceptance | this report section + full focused sweep | all suites below | acceptance recorded |

W41→W42 integration hint (non-blocking): W41 unified the menu update-check route through `run_wx_update_check`; W42 asserts the downstream verification/install gates that route feeds. No W41 file was modified here.

## Tests and evidence

Focused regression (after discovery, no edits):

```text
Evidence ID: EV-W42-TESTS
python -m pytest tests/test_update_verification.py tests/test_app_updater.py -q → 21 passed
python -m pytest tests/test_wx_updater_spec.py tests/test_updater_helper.py tests/test_w41_updater_routing.py tests/test_installation_context.py tests/test_linux_update_handoff.py tests/test_deb_installer.py -q → 48 passed, 2 skipped
Total W42-focused: 69 passed, 2 skipped (skips are pre-existing platform-conditional, not W42 weaknesses)
git diff --check → clean (exit 0; only sibling-wave CRLF warnings on already-dirty files)
```

| Requirement | Test | Evidence |
|---|---|---|
| UPD-029/030/066/077 | `test_signed_metadata_requires_known_key_and_valid_signature` | valid sig accepts; unknown key + tampered sig raise |
| UPD-029/032/066 | `test_metadata_rejects_duplicate_targets_and_non_https_urls` | duplicate/http/untrusted-host all raise |
| UPD-031/066/077 | `test_artifact_size_and_digest_are_verified` | size + digest mismatch raise |
| UPD-035/078 | `test_download_reports_transferred_and_total_bytes`, `test_download_percentage_is_actual_package_percentage` | real-counter `(100,"",2,2)` / `(50,"",1,2)→(100,"",2,2)` |
| UPD-035 GUI | `test_update_download_progress_shows_real_bytes_and_percentage`, `test_update_available_shows_versions_and_download_size` | real bytes/percent readback in live wx dialog |
| UPD-034/052 GUI | `test_update_install_opens_installation_splash`, `test_installation_progress_uses_real_backend_progress`, `test_installation_current_item_visible_when_available` | splash opens; backend progress; current item visible |
| UPD-037/LIFECYCLE | `test_update_cancel_reaches_downloader`, `test_update_cancel_prevents_install`, `test_update_close_in_flight_safe`, `test_update_late_callback_after_close_safe`, `test_closing_update_progress_cancels_active_download`, `test_cancelled_update_download_removes_partial_file` | cancel reaches downloader; no install after cancel; no dead-control callbacks; `.part` removed |
| UPD-038/067 | updater_helper suite (AppImage/macOS/deb/flatpak rollback) + PS1 rollback assertions | per-strategy rollback pinned |
| UPD-034/038/078 | `test_windows_installer_script_has_independent_real_progress_and_rollback` | independent splash, real `$extractDone/$copyDone`, monotonic guard, rollback, health check |
| UPD-037/038 GUI | `test_update_verification_state_visible`, `test_update_ready_requires_install_confirmation`, `test_install_without_verified_artifact_stays_failed` | verifying visible; install gated on confirmation + verified artifact |

Evidence classes: `GUI` (required) → FULL via 23 real-wx `test_wx_updater_spec` runtime tests (real `wx.App`/dialogs/gauges/readback) plus splash/install-state tests. `PACKAGE` (required) → source-packaging proof: no private signing key anywhere in the shipped updater surface (grep-verified), public `TRUSTED_UPDATE_KEYS` + HTTPS allowlist ship with source, exact-artifact SHA-256 verification path pinned by tests; no install artifact was built or claimed in this phase (built-artifact SHA acceptance belongs to the packaged-acceptance owner at install time, and the installer re-verifies the exact digest before replacing anything). External HPC → N/A (updater surface is connection-independent; no external system touched — real download is exercised via the `cancelled()`/counter boundary with synthetic fixtures, not mocked away).

## Diff review

```text
Evidence ID: EV-W42-DIFF
W42-owned hunks: none (surface already valid; zero product/test files changed by this worker)
git diff --check: clean
Sibling-wave hunks: preserved untouched (see git status; none belong to W42 ownership surface)
Secrets scan: nothing added; fixtures use example.com/example.invalid + tmp dirs
Weakened tests: none (no test file touched)
```

## Cross-scope routing

No cross-scope defects fixed opportunistically. No findings routed (discovery found zero W42-owned defects and zero out-of-scope defects requiring routing from this surface).

## Handoff

Worker requests independent audit. Resume point: none — work is complete; candidate is the current working tree on `develop` at base `c8293d3ca309526ed250c794c3b294f7c54ef369` with zero W42-owned hunks (already-valid surface; commit/integration is controller-owned). The fresh-context audit report (`W42_AUDIT_REPORT.md`) is controller/audit-phase owned and is intentionally not written here — a worker self-audit cannot satisfy `audit_policy: fresh-independent`.

```text
Candidate identity: working tree on develop @ c8293d3ca309526ed250c794c3b294f7c54ef369 + zero W42 hunks (EV-W42-DIFF)
Focused tests: 69 passed, 2 skipped (pre-existing platform-conditional skips)
GUI runtime: wxPython (msw) — 23 real-wx updater-spec tests + splash/install-state tests
Manual acceptance remaining (controller-owned, not faked): none for W42 scope (no MFA/hardware/credential/manual gate in owned rows)
```
