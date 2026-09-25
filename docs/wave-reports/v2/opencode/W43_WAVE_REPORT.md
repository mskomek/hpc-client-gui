# W43 Wave Report — Updater restart, package validation and signing policy

```text
Wave: W43
Canonical report path: docs/wave-reports/v2/opencode/W43_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui
Branch: develop
Baseline SHA: c8293d3ca309526ed250c794c3b294f7c54ef369
Current HEAD: c8293d3ca309526ed250c794c3b294f7c54ef369 (working-tree changes uncommitted; controller owns commit/integration)
Plugin/external repo SHA(s), if applicable: N/A (no plugin repo touched)
First started: 2026-09-24 (W43 run phase)
Last updated: 2026-09-24
Session status: READY FOR INDEPENDENT AUDIT
Wave decision: GO (worker-level; pending controller independent audit)
```

## Authority reads

1. `waves/pending/W43.md` (wave_id W43, execution kind, canonical_source W43, 18 source rows + 1 TODO row, start gate NONE, cohort P8-updater-join, required evidence `GUI,PACKAGE`, integration refs W40/W42 non-blocking, downstream hint W44).
2. `opencode/REQUIREMENT_REGISTRY.md` rows owning Wave W43: `HPC-W09-UPD-039`..`043`, `053`, `054`, `055`, `068`, `069`, `079`, `080`, `081`, `086`, `087`, `088`, `HPC-W09-PKGUPD-001`, `HPC-W09-PKGUPD-002` (lines 966-970, 980-982, 995-996, 1006-1008, 1013-1015, 1290-1291).
3. `opencode/TODO_OWNERSHIP_MAP.md` row owning Wave W43: `HPC-W09-TODO-058` (line 206: Authenticode policy / unsigned wording).
4. `opencode/sources/WAVE_V2_FINAL_09.md` → Workstream J — Restart semantics (lines 243-252), Workstream K — Package validation (254-256), Targeted tasks TASK-W09-010/011 (269-270), Test matrix rows 288-289, Acceptance criteria 302-304, STOP conditions 312, Rollback 320, Handoff 324.
5. Live code before edits: `src/hpc_gui/services/app_updater.py` (signed-metadata gate, `download_and_verify_release`, `_VERIFIED_UPDATE_ARTIFACTS`, `launch_update_installer` re-verify, `build_update_script` backup/rollback PS1), `src/hpc_gui/services/update_verification.py` (`verify_signed_metadata`, `validate_update_url`, `verify_artifact` size+SHA-256), `src/hpc_gui/wx_updater_view.py` (`WxUpdateDialog` READY requires explicit Install; `_start_install` had NO unsaved guard — the W43 defect), `src/hpc_gui/services/editor_controller.py` (`DocumentModel.dirty`), `docs/VERIFYING_RELEASES.md` §5 (unsigned Windows wording already present).
6. Live tests before edits: `tests/test_app_updater.py`, `tests/test_update_verification.py`, `tests/test_wx_updater_spec.py`, `tests/test_updater_helper.py`, `tests/test_w41_updater_routing.py`, `tests/test_installation_context.py`, `tests/test_linux_update_handoff.py`, `tests/test_deb_installer.py`.

## Baseline capture

```text
Evidence ID: EV-W43-BASELINE
Commit: c8293d3ca309526ed250c794c3b294f7c54ef369
Branch: develop
git status: dirty (pre-existing sibling-wave M files preserved untouched; W43 adds 2 new files + 1 scoped hunk, see diff review)
```

Content-identity note: the controller handoff cites `content_identity=965183e8...`. `waves/` is gitignored, so the pending spec lives outside Git history by program design. The worker proceeded on current repository truth without editing the spec; identity reconciliation is controller-owned.

Narrow baseline before edits is not separable from the shared dirty tree (parallel cohort shares one working tree on `develop`). The W43 worker baselined by focused suite: all updater/verification clusters below were green before edits and re-run after edits as the acceptance regression. No sibling file was reverted, merged, or cleaned by this worker.

Pre-existing dirty files NOT owned by W43 (preserved untouched): all `M` entries from sibling waves (settings/i18n/plugins/jobs/editor/logs/services — see `git status`). W43 touched only the hunks in EV-W43-DIFF.

## Discovery pass / WAVE_FINDINGS

```text
Finding ID | Severity | Surface | Evidence | Root cause | User/system impact | Candidate fix | Countable fix? | Status
DEF-W43-001 | P0 | _start_install installs + quits app with zero unsaved check | wx_updater_view.py _start_install (pre-edit): verified-artifact gate only; no dirty/unsaved probe, no confirm, no defer; ExitMainLoop on success | restart-safety never implemented on the install path | update with dirty editor silently restarts and can lose unsaved user data (STOP UPD-086 violated; UPD-039..043/079 open) | enforce user-confirmed defer-or-confirm guard before any installer launch | YES (FIX-A) | FIXED+VERIFIED
OBS-W43-002 | N/A | no dedicated restart-policy unit | no update_restart_policy module pre-edit | policy lived only as dialog text | UPD-039..042 semantics (mode/defer/version-confirm) untestable in isolation | new policy module with pure functions + provider registry | NO (part of FIX-A) | FIXED+VERIFIED
OBS-W43-003 | N/A | package/signing/rollback/handoff surfaces already valid | verify_artifact size+digest, _VERIFIED_UPDATE_ARTIFACTS + re-verify, PS1 backup/rollback + log, VERIFYING_RELEASES §5 unsigned wording | prior waves + release docs | no defect; pin with W43-owned tests | new pinning tests, zero product edits outside FIX-A | NO | PINNED (no-code-change classification)
```

Second-defect sweep (W43 surface only): negative paths checked (verify отказано without artifact; corrupt cache deleted; cancel removes `.part`; close-in-flight safe — inherited W42 pins re-run green); stale callback checked (late callback after close safe — re-run green); probe/confirm injection failures checked (confirm exception → defer, fail-closed; never silent install); byte-change checked (any package byte flip invalidates SHA-256 — new pin); signing-claim sweep checked (`rg` over `src/hpc_gui/*.py`: no file claims signed Windows without mentioning unsigned — new pin). Result: no further W43-owned defects beyond DEF-W43-001.

## Implementation

### FIX-A — user-confirmed unsaved-safe restart (DEF-W43-001, UPD-039..043/053/079/086)

- NEW `src/hpc_gui/services/update_restart_policy.py` (W43 policy authority): `RESTART_MODE="user-confirmed"`; `count_unsaved`/`has_unsaved_changes`/`should_defer_install` over `dirty`-attribute documents; `deferral_message(count)` (names count, offers Later, states never-silent); `verify_post_update_version` (exact trimmed equality); provider registry (`register/unregister/clear/get_unsaved_count`) for editor integration without cross-wave edits; `windows_signing_policy()` (unsigned + doc pointer); `handoff_payload()` (UPD-088 carrier).
- `src/hpc_gui/wx_updater_view.py` (+57, only W43 hunk in tracked files): `WxUpdateDialog` gains `unsaved_probe`/`confirm_fn` seams (default: registry count + real `wx.MessageBox YES_NO` with `deferral_message`); `_start_install` now computes unsaved BEFORE closing the dialog — if >0 and unconfirmed, it stays in `STATE_READY_TO_INSTALL` with `_install_deferred_due_to_unsaved=True`, verified artifact retained, nothing installed/closed/discarded; if confirmed, records `_install_confirmed_with_unsaved` and proceeds; if clean, no prompt and proceeds exactly as before. Confirm exceptions fail closed to defer.
- Restart answers pinned: automatic vs user-confirmed → user-confirmed (`Later` + `Install Update`); unsaved fate → never silently destroyed (defer-or-explicit-confirm); defer-until-safe → yes (dirty>0 defers); version confirm → exact equality helper.

### No-code-change classifications (requirement → live owner → evidence)

- UPD-054/055/068-runtime-part/080/081-PKGUPD-001/002 (exact package + same production path): `download_and_verify_release` writes the exact `updates/v{version}/{zip_name}` artifact and `verify_artifact`s it (size+SHA-256); `launch_update_installer` refuses without the `_VERIFIED_UPDATE_ARTIFACTS` record AND re-runs `verify_artifact` immediately before every installer path; test-channel fixtures exercise this same production path (new W43 pins). Zero product edits.
- UPD-069 (packaged updater resources): installer PS1 carries real per-byte progress + required backup/restore resources; splash is 620×360 with integrity text (W42-pinned, re-run green). Pinned by W43 byte/progress + script-resource assertions.
- UPD-087 (rollback): `build_update_script` preserves `_internal.backup` + `hpc-client-gui.exe.backup`, writes `update-install.log`, try/catch restores known-good + relaunches prior app (new W43 pin, zero product edits).
- UPD-088 (handoff): `handoff_payload(settings_schema_version, migration_coverage, verification_evidence, packaging_requirements)` + this report section is the carrier: schema v7 (storage.py lineage; exact registry version string is settings-wave-owned, referenced not redefined here); migration coverage = updater verification fixtures + v6→v7 theme-key lineage (settings-wave-owned list referenced); verification evidence = EV-W43-TESTS below; packaging requirements = exact ZIP + SHA-256 + signed `UPDATE_METADATA.json`, Windows unsigned per `VERIFYING_RELEASES.md` §5.
- TODO-058 (Authenticode): `docs/VERIFYING_RELEASES.md` §5 already states "Authenticode signing is **not enabled yet**" with SmartScreen guidance — public wording explicitly matches unsigned status. `windows_signing_policy()` returns `{status: unsigned, authenticode_enabled: false}` and the W43 test pins both the doc wording and the no-false-signed-claim sweep. Zero doc edits needed (wording already truthful).

W42→W43 integration hint (non-blocking): W42 owns verification/install gates; W43 consumes them unchanged (no W42 file modified). W40 localization hint: the READY restart label resolves via `t("updates.restart_required")` in both en/tr (W43 GUI test is locale-agnostic). Downstream W44 hint: handoff payload above.

## Tests and evidence

New: `tests/test_w43_restart_package_policy.py` — **16 passed** (deterministic; real `verify_artifact`/policy path; real wx dialogs for GUI claims; `wx.CallAfter` inline + inline thread where the worker is bypassed; dialog seams only).

| Requirement | Test | Evidence |
|---|---|---|
| UPD-039/053 mode | test_restart_is_user_confirmed_not_automatic | `user-confirmed`, Later+Install retained |
| UPD-040/043/079/086 dirty | test_clean_state_does_not_defer, test_dirty_state_defers_install, test_deferral_message_names_count_and_later | 0→allow, 2→defer, message names count + Later + never-silent |
| UPD-042 version | test_post_update_version_confirmed_by_exact_equality | equality pins, mismatch/empty rejected |
| UPD-041 defer wiring | test_provider_registry_aggregates_counts | registry 2+0→2 |
| UPD-055/068 GUI FULL | test_ready_install_defers_when_dirty_and_user_declines | dirty=2 + decline → stays READY, artifact retained, nothing installed |
| UPD-055/068 GUI FULL | test_ready_install_proceeds_when_dirty_but_user_confirms | dirty=1 + confirm → splash shown, `_install_confirmed_with_unsaved=1` |
| UPD-055/068 GUI FULL | test_ready_install_with_clean_state_needs_no_confirm | clean → no prompt, splash shown |
| UPD-039 GUI FULL | test_ready_dialog_states_restart_requirement | READY dialog carries restart wording (en/tr agnostic) |
| PKGUPD-001 | test_exact_artifact_sha256_bound | exact bytes pass; +1 byte → digest mismatch |
| PKGUPD-002 | test_safe_test_channel_uses_production_verification_path | stubbed channel → real `download_and_verify_release` + SHA-256 match |
| PKGUPD-001 gate | test_installer_refuses_unverified_exact_artifact | unpackaged/unverified → "authenticated verification" refusal |
| UPD-087 | test_windows_script_preserves_known_good_and_rolls_back | `_internal.backup` + exe backup + rollback + install log |
| TODO-058 | test_windows_signing_policy_is_unsigned_with_documented_wording | unsigned + doc wording + no false-signed-claim sweep |
| UPD-088 | test_handoff_payload_carries_required_fields | schema/coverage/evidence/packaging carried |

Focused regression (after edits):

```text
Evidence ID: EV-W43-TESTS
python -m pytest tests/test_update_verification.py tests/test_app_updater.py tests/test_wx_updater_spec.py tests/test_updater_helper.py tests/test_w41_updater_routing.py tests/test_installation_context.py tests/test_linux_update_handoff.py tests/test_deb_installer.py tests/test_w43_restart_package_policy.py -q → 85 passed, 2 skipped (skips are pre-existing platform-conditional, not W43 weaknesses)
git diff --check → clean (exit 0; only sibling-wave CRLF warnings on already-dirty files)
```

Evidence classes: `GUI` (required) → FULL via 4 real-wx `test_w43_*` runtime tests (real `wx.App`/dialogs/panel readback/splash/decline-stays-READY) plus the 23 inherited real-wx `test_wx_updater_spec` tests re-run green. `PACKAGE` (required) → FULL via exact-artifact SHA-256 binding on the real `verify_artifact` path (`test_exact_artifact_sha256_bound`, `test_safe_test_channel_uses_production_verification_path`, `test_installer_refuses_unverified_exact_artifact`, `test_windows_script_preserves_known_good_and_rolls_back`) — no artifact was built or published; claims bind to the exact tmp fixture bytes + SHA-256, and any byte change invalidates. External HPC → N/A (updater surface is connection-independent; no external system touched).

## Diff review

```text
Evidence ID: EV-W43-DIFF
Tracked hunk (only): src/hpc_gui/wx_updater_view.py +57 (restart-safety seams + _start_install defer-or-confirm guard; see `git diff -- src/hpc_gui/wx_updater_view.py`)
New files (untracked, W43-owned): src/hpc_gui/services/update_restart_policy.py, tests/test_w43_restart_package_policy.py
git diff --check: clean (exit 0)
Scope check: no sibling M file modified by this worker; no test weakened (no skip/xfail/assertion edits outside the new file); no secrets (no private-key material; only the shipped Ed25519 public-key constant path untouched); no generated/binary noise (only .py sources + this report)
Secrets sweep: `verify_artifact`/`TRUSTED_UPDATE_KEYS` public-only posture unchanged from W42 (private-key grep still zero hits per W42; not re-modified here)
```

## Handoff / DAG unlocks (UPD-088 payload)

```text
settings_schema_version: v7 lineage (canonical version string owned by settings waves; referenced, not redefined)
migration_coverage: [updater verification fixtures (this wave), v6->v7 theme-key lineage (settings-wave-owned, referenced)]
verification_evidence: EV-W43-TESTS (85 passed, 2 skipped) + EV-W43-DIFF (git diff --check clean)
packaging_requirements: exact ZIP artifact + sibling .sha256 + signed UPDATE_METADATA.json (Ed25519, TRUSTED_UPDATE_KEYS); Windows release UNSIGNED per docs/VERIFYING_RELEASES.md §5
```

Historical unlock targets are integration hints only; no downstream Wave was started by this worker.

## Findings and resume state

- No owned blocking defect remains. DEF-W43-001 fixed + verified. No P0/P1 open on W43 surface.
- No `AWAITING_INPUT` (no concrete missing artifact/API: editor dirty state is consumed via the injectable probe/registry seam, not a missing input).
- No `EXTERNAL_BLOCKED` (no external system required; package claims bind to exact local fixture bytes).
- Resume point: controller independent audit of this READY_FOR_AUDIT candidate; auditor re-runs EV-W43-TESTS verbatim and inspects EV-W43-DIFF.
- Cross-scope routes: none (second-defect sweep found nothing outside W43 ownership; W41 OBS items remain with their owners).
```

---

## Contradiction scan

- Restart mode is stated once (`user-confirmed`) in policy, implementation, tests, and this report — no automatic-restart claim anywhere.
- Defer semantics agree: dirty>0 → decline stays READY with artifact retained (test) == report == code.
- Package claims bind to exact bytes+SHA-256 in code, tests, and report — no version-string substitution.
- Signing agrees: `unsigned` in policy, doc §5, test, and report — no signed-Windows claim.
- No test weakened; new tests add assertions only. No sibling file edited.

## Review passes

- Claim-to-source: every owned ID above traces to a named live owner + pinned test.
- Diff review: tracked +57 hunk + 2 new files inspected; sibling changes untouched.
- Adversarial: confirm-exception → defer (fail-closed); byte-flip → mismatch; unverified → refusal; clean → no prompt (no nag).
