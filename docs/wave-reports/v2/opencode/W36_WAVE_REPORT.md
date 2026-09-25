# W36 — Packaged plugin operations and documentation contract — Wave Report

Wave: W36
Canonical report path: docs/wave-reports/v2/opencode/W36_WAVE_REPORT.md
Repository: mskomek/hpc-client-gui
Branch: develop
Baseline SHA: c8293d3ca309526ed250c794c3b294f7c54ef369
Current HEAD: c8293d3ca309526ed250c794c3b294f7c54ef369
Tested implementation SHA: c8293d3ca309526ed250c794c3b294f7c54ef369 (plus uncommitted W36 diff in README.md, src/hpc_gui/docs/{PLUGINS,HELP}_{en,tr}.md, tests/test_w36_packaged_docs.py; sibling dirty files from W26-W35 preserved untouched)
Plugin/external repo SHA(s), if applicable: plugin repo not pinned (local declarative fixtures only; no network — same basis as W32-W35)
First started: 2026-09-24 (run phase)
Last updated: 2026-09-24
Session status: READY FOR FINAL REVIEW
Wave decision: GO (worker) — pending fresh independent audit

## Objective

Prove packaged discovery/install/update/remove/offline behavior and keep provider/plugin authoring documentation aligned to the actual schema (Workstreams H + I).

## Mandatory authority consumed

- waves/pending/W36.md (all owned IDs)
- opencode/REQUIREMENT_REGISTRY.md rows Owning Wave W36 (39 rows: HPC-W08-PM-021..026, 049..078 + HPC-W08-DOCS-001/002)
- opencode/TODO_OWNERSHIP_MAP.md row Owning Wave W36 (HPC-W08-TODO-DOCS-SURFACE-001)
- waves/bak/WAVE_V2_FINAL_08.md sections: Workstream H (Packaged discovery), Workstream H0 (reference), Workstream I (Documentation contract), Test matrix, Acceptance criteria, STOP conditions, Handoff
- Live code: src/hpc_gui/plugins/{discovery,loader,validator,models,installer,lifecycle,providers,settings,templates,storage}.py, src/hpc_gui/wx_plugins_view.py, src/hpc_gui/wx_shell.py, src/hpc_gui/services/provider_capabilities.py, src/hpc_gui/i18n/{en,tr}.json, docs/ADDING_CLUSTER_PROVIDER.md, src/hpc_gui/docs/PLUGINS_{en,tr}.md, README.md, src/hpc_gui/docs/HELP_{en,tr}.md

## Baseline (pre-edit)

- `git status --short --branch` showed develop at c8293d3c with pre-existing dirty W26-W35 files (preserved; W32 discovery.py/lifecycle.py/providers.py/settings.py new files plus loader/validator/installer/models diffs are sibling-wave work, not re-owned).
- Narrow baseline: tests/test_w32 + test_w33 + test_w34 + test_w35 = 61 passed; plugin core/contract/installer/schema + wx packaged smoke + wheel packaging = 133 passed, 20 skipped.
- dist/ wheel (hpc_client_gui-1.5.9, sha256 d3a3dcbe...) is STALE: predates W32-W36 plugin modules (discovery/lifecycle/providers/settings ABSENT) — cannot serve as W36 package evidence.
- Discovery pass findings (WAVE_FINDINGS):

Finding ID | Severity | Surface | Evidence | Root cause | Impact | Candidate fix | Countable | Status
DEF-W36-001 | P1 | packaged discovery | dist wheel lacks discovery/lifecycle/providers/settings modules (zip listing) | stale artifact predates W32-W35 implementation | PM-021/060/070 unprovable against shipped artifact | build fresh wheel from candidate, prove discovery from it with no dev path | YES | FIXED (FIX-A)
DEF-W36-002 | P1 | authoring docs | PLUGINS_en/tr document profiles/quota but no manifest contract (grep: provider_ids/optional_dependencies/requires_app/entrypoints absent) | manifest contract (W32 MANIFEST-001..008) never written for authors | DOCS-001 unmet: authors cannot match schema/loading behavior | add manifest authoring section EN+TR, bind with contract test | YES | FIXED (FIX-B)
DEF-W36-003 | P2 | public surface text | README + PLUGINS_en/tr + HELP_en/tr claim a "top-right Plugins button (between Update and Send Logs)"; live wx surface has a menubar Plugins menu only (wx_shell.py:110-125, no wx.Button; _on_plugins dead code) | stale text from an older surface | TODO-DOCS-SURFACE-001 unmet for plugin entry claims | rewrite entry text to the real menu + tabs in all 5 spots (EN+TR) | YES | FIXED (part of FIX-B)
DEF-W36-004 | P3 (routed, not fixed) | AGENTS.md | test_agent_guidance_points_at_single_authority fails: AGENTS.md lacks "pull request" | agent-guidance ownership outside W36 | none on W36 acceptance | ROUTED to controller/true owner; no opportunistic edit | NO | ROUTED

## Implementation (smallest coherent correction)

- FIX-A (packaged): built a fresh wheel from the candidate (`python -m build --wheel --no-isolation --outdir .tmp/w36-packaged`); artifact `hpc_client_gui-1.5.9-py3-none-any.whl`, SHA-256 `d7aec62d6c6da11b9f5e68013979336a7c7af7d585d538a7a0ca143e2d4cc417`, 274 entries, contains discovery/lifecycle/providers/settings/loader plus the corrected docs. No product code changed for FIX-A: the proof is the artifact + the subprocess test.
- FIX-B (docs, DOCS-001/DOCS-002/SURFACE-001):
  - `src/hpc_gui/docs/PLUGINS_en.md`: "The Plugins button" section replaced with "Opening the Plugin Manager" (menubar Plugins menu entries mapped to Discover/Installed/Updates tabs); new "Plugin manifest authoring" section (required keys, schema_version 1, plugin_api 1 (+2 trusted-only), dotted id shape, name/version/requires_app rules, capability vocabulary, declarative entrypoints, files hash contract, provider_ids/optional_dependencies advisory-only semantics, containment behavior).
  - `src/hpc_gui/docs/PLUGINS_tr.md`: same two changes in Turkish with actual tr.json menu labels (Eklenti Gözat & Kur..., Kurulu Eklentileri Yönet..., Eklenti Güncellemelerini Denetle...).
  - `README.md`: "top-right Plugins button" replaced with menubar Plugins menu entries.
  - `src/hpc_gui/docs/HELP_en.md` / `HELP_tr.md`: same entry-point correction (EN menu labels / TR menu labels).
  - Quota-optional contract (DOCS-002) verified already present in ADDING_CLUSTER_PROVIDER.md + PLUGINS_en/tr + README (leave-blank supported, no probing fallback); no edit needed.
- No cross-Wave cleanup: only W36-owned docs + one new test file changed; sibling dirty files preserved. Remaining stale-button hits under `.agent-runs/`, `build/`, `audit/` are legacy snapshots/build output — read-only, intentionally untouched.

## Tests

New: `tests/test_w36_packaged_docs.py` (20 tests):

- Matrix PM-049..060: no-plugins start, valid-loads-once, malformed isolated, no-code-import (PM-053 by construction), incompatible rejected, duplicate deterministic, optional-dep-missing loads, disabled registers nothing, stale settings safe, quota-omitted NOT_DECLARED + byte-stable rebuild, CWD-never-leaks.
- Packaged PM-021/022/023/024/025/026 + PM-060/070 (`test_packaged_wheel_discovers_without_dev_path`, packaging mark): subprocess with cwd outside repo + PYTHONPATH=wheel only proves import-from-wheel, loaded list, empty problems, provider `truba` registered, quota NOT_DECLARED, disable observed on next load.
- DOCS-001: docs name all manifest keys EN+TR; documented capability names ⊆ KNOWN_CAPABILITIES; documented pins match validator; advisory example validates clean.
- DOCS-002: quota-less profile validates, template quota_sources == [], view NOT_DECLARED; quota documented in all three guides.
- SURFACE-001 (audit mark): no top-right claim in README/PLUGINS/HELP EN+TR; i18n menu/tab labels real; wx_shell binds all three PLUGIN-* commands with the correct tab map.
- STOP PM-073/074/076/077: shadowing diagnosed deterministically, optional plugin never blocks startup, disable semantics + lifecycle note wording, secrets stored locally but dropped from export and redacted in logs, never in loader diagnostics.
- PM-078: canonical registration chain + requirement id asserted unchanged.

Evidence:

- EV-W36-001: `pytest tests/test_w36_packaged_docs.py -q` → 20 passed (tested SHA c8293d3c + W36 diff; packaged test against wheel d7aec62d...). Exit 0. passed=20 failed=0 skipped=0.
- EV-W36-002 (packaged FULL): wheel rebuilt after docs edits; probe JSON shows hpc_gui.__file__ inside `.whl`, cwd outside repo, loaded=[org.hpcclient.truba], problems=[], providers=[truba], quota=NOT_DECLARED, after_disable=[] (see test body for the exact probe).
- EV-W36-003 (regression): test_w32+w33+w34+w35 → 61 passed; plugin core/contract/schema → 52 passed, 20 skipped; installer+w34+w35-gui → 71 passed; plugin_manager_ui → 34 passed (3 slow rollback tests deselected from the timed batch; unaffected by W36); docs link check `test_referenced_local_files_exist` → passed.
- EV-W36-004 (negative control): `test_agent_guidance_points_at_single_authority` fails identically with and without the W36 diff (AGENTS.md untouched) → pre-existing, routed as DEF-W36-004.
- Baseline: pre-edit narrow suites (61 + 133 passed/20 skipped) recorded before edits.

Test taxonomy: integration (matrix, packaged subprocess, STOP), contract (docs-vs-schema), audit (surface text), unit (chain identity). Mocks limited to disposable roots and declarative fixtures (legitimate boundary); what tests do NOT prove: real-network registry fetch and real OS package installers (EXTERNAL_BLOCKED not triggered — no owned requirement needs live infra; offline/cache contract covered by W35 injected fetchers).

## Diff review

- `git diff --check` → clean.
- W36-owned diff: README.md (1 sentence), PLUGINS_en.md (menu section + manifest section), PLUGINS_tr.md (same, Turkish), HELP_en.md (1 sentence), HELP_tr.md (1 sentence), tests/test_w36_packaged_docs.py (new, 20 tests).
- Full diff of owned files inspected: no secrets, no generated/binary noise, no unrelated changes, no weakened tests, EN/TR parity on both changed sections, Turkish menu labels byte-match tr.json.
- New tests use meaningful assertions (list identity, problem emptiness, capability states, wheel-zip membership, probe JSON fields, docs-vs-code constants), legitimate boundaries (tmp roots, fixture manifests, wheel subprocess), deterministic (no sleeps; subprocess timeout 120s).

## POST_GREEN_REVIEW

- Duplicate path: matrix scenarios reuse W32-W34 backends through public APIs; no logic duplicated into tests or docs.
- Alternate entry: Qt dialog entries (Browse & Install/Manage/Updates) share the same loader root semantics; docs describe the wx surface only where surface text is concerned.
- Silent fallback: none — packaged probe fails loudly (non-zero exit + stderr tail); missing wheel skips explicitly with reason.
- Stale state: wheel rebuilt after the last docs edit; reported SHA matches the tested artifact.
- Identity: probe asserts import-from-wheel and outside-repo cwd; registry identity covered by W32 determinism test.
- Cleanup: all fixtures under tmp_path; wheel under .tmp/w36-packaged (temp-state rule).
- Dead branch: `_on_plugins` dead handler in wx_shell.py noted but NOT removed (sibling-owned file; routed, not opportunistically cleaned).
- Hardcoded: none (wheel located via env override or newest .tmp artifact; app version from package).
- Error-as-success: probe failures propagate as test failures, never PASS.
- Packaged divergence: proven absent for plugin discovery (wheel-only sys.path + foreign cwd).

## Requirement dispositions (all owned IDs)

- HPC-W08-PM-021 (package with expected plugin source): IMPLEMENT (fresh wheel contains all plugin modules; zip-membership asserted).
- PM-022 (launch outside repo): IMPLEMENT (subprocess cwd outside repo, exit 0, discovery works).
- PM-023 (inspect plugin list/status): IMPLEMENT (loaded ids + empty problems from packaged probe).
- PM-024 (enable/disable as designed): IMPLEMENT (disable observed on next load + lifecycle note wording).
- PM-025 (exercise provider registration): IMPLEMENT (registered_providers → truba via canonical chain in packaged context).
- PM-026 (absent dev source path): IMPLEMENT (wheel-only PYTHONPATH; no repo on sys.path; CWD leg in-repo).
- PM-049..060 (matrix rows): IMPLEMENT (11 tests; PM-056 conditional branch active with missing-optional fixture; PM-053 satisfied by no-import construction + entry-point inactive proof).
- PM-061 (both repo SHAs): IMPLEMENT as far as wave-locally possible (main HEAD recorded; plugin repo has no local checkout — fixtures only, no stale pin claimed).
- PM-062 (sources/precedence documented+tested): IMPLEMENT (W32 discovery module + docs manifest section; precedence asserted in W32 suite, reused).
- PM-063 (metadata compatibility validated): IMPLEMENT (validator + manifest tests reused; incompatible-API case in W36 matrix).
- PM-064 (enable/disable matches UI): IMPLEMENT (lifecycle note + toggle tests + wx view renders the note per W35).
- PM-065 (bad plugin cannot crash core): IMPLEMENT (malformed + broken-sibling cases).
- PM-066 (duplicates deterministic): IMPLEMENT (duplicate test + shadowing STOP test).
- PM-067 (provider plugins use W02 contract): IMPLEMENT (chain test + capability view via W02 builder; no behavior changed).
- PM-068 (optional capabilities truly absent, CONDITIONAL): IMPLEMENT (quota-absent provider loads, NOT_DECLARED, stable rebuild).
- PM-069 (settings isolated/namespaced): IMPLEMENT (W34 module reused; stale-settings + secrets cases in W36 matrix).
- PM-070 (exact artifact discovers without dev-path help): IMPLEMENT (wheel d7aec62d... + probe).
- PM-071 (authoring docs match implementation): IMPLEMENT (manifest sections added EN+TR + contract test).
- PM-072 (no P0/P1): IMPLEMENT (no owned P0/P1 open; DEF-W36-004 is P3 routed).
- PM-073/074/075/076/077 (STOP): IMPLEMENT (absence proven: deterministic shadowing diagnostic; startup never blocked; PYTHONPATH-independence proven; disable semantics documented in UI note; secrets redacted/dropped).
- PM-078 (handoff): IMPLEMENT — W36 changed no provider behavior (docs + tests only), so no W02/W03/W05–W07 evidence slice is invalidated; nothing must be rerun before W10 on W36's account.
- HPC-W08-DOCS-001: IMPLEMENT (manifest authoring sections + schema-binding test).
- HPC-W08-DOCS-002: IMPLEMENT (absent-quota templates proven + documented in all three guides).
- HPC-W08-TODO-DOCS-SURFACE-001: IMPLEMENT (5 files corrected; entry/tab claims verified against wx_shell/i18n; updater/platform/terminal claims outside plugin surface left to their owners — no mismatch found in plugin-adjacent text).

No AWAITING_INPUT. No EXTERNAL_BLOCKED (no owned requirement needs live infra).

## Resume state

Completed and verified:
- Fresh packaged artifact built from candidate with SHA recorded; packaged discovery/install/enable/provider/dev-path-independence proven from the wheel outside the repo.
- Manifest authoring contract documented EN+TR and bound to the validator by contract tests.
- Public plugin-entry claims re-audited and corrected in README/PLUGINS/HELP EN+TR.
- Full matrix + STOP absences + handoff recorded; regressions green; diff reviewed.

In progress: none (worker done; awaiting fresh independent audit).

Open P0/P1: none owned.
Open P2/P3: DEF-W36-004 (P3, routed to controller/true owner).

Pending tests/evidence: fresh independent audit (controller-owned).

Last exact commands run:
- .venv/Scripts/python -m build --wheel --no-isolation --outdir .tmp/w36-packaged → hpc_client_gui-1.5.9-py3-none-any.whl
- .venv/Scripts/python -m pytest tests/test_w36_packaged_docs.py -q → 20 passed
- .venv/Scripts/python -m pytest tests/test_w32_discovery_manifest.py tests/test_w33_lifecycle_isolation.py tests/test_w34_provider_settings.py tests/test_w35_plugin_manager_gui.py -q → 61 passed
- .venv/Scripts/python -m pytest tests/test_plugin_core.py tests/test_plugin_contract.py tests/test_plugin_schema_compat.py -q → 52 passed, 20 skipped
- git diff --check → clean

Next actions:
1. Controller: fresh independent audit of W36 (do not reuse stale PASS).
2. Controller: merge/reconciliation + final validation (PROGRAM_COMPLETE gates owned by controller).

Evidence/artifact identities:
- Tested SHA: c8293d3ca309526ed250c794c3b294f7c54ef369 + W36 diff (README.md, PLUGINS_en/tr.md, HELP_en/tr.md, tests/test_w36_packaged_docs.py)
- Packaged artifact: .tmp/w36-packaged/hpc_client_gui-1.5.9-py3-none-any.whl, SHA-256 d7aec62d6c6da11b9f5e68013979336a7c7af7d585d538a7a0ca143e2d4cc417, 274 entries
- New tests: tests/test_w36_packaged_docs.py (20 tests)
- This report: docs/wave-reports/v2/opencode/W36_WAVE_REPORT.md
- Audit (fresh-context, controller-owned): docs/wave-reports/v2/opencode/W36_AUDIT_REPORT.md

## Final summary block

FIX-A: fresh packaged artifact + outside-repo wheel-only discovery proof
DEF: DEF-W36-001 (stale dist wheel predates all plugin modules; packaged acceptance unprovable)
Root cause: dist/ artifact built before W32-W35 implementation; discovery/lifecycle/providers/settings absent from the zip.
Before EV: zip listing of dist wheel shows the four modules ABSENT.
After EV: EV-W36-001/002 (fresh wheel d7aec62d..., 274 entries, all modules PRESENT; subprocess probe from wheel-only sys.path with foreign cwd: loaded=[org.hpcclient.truba], problems=[], providers=[truba], quota=NOT_DECLARED, disable observed).
Regression test: test_packaged_wheel_discovers_without_dev_path
Sensitivity proof: stale dist wheel lacks the modules by listing (artifact-level negative); probe asserts `.whl` in hpc_gui.__file__ so a dev-path import cannot silently pass.
Package evidence: SHA-256 d7aec62d6c6da11b9f5e68013979336a7c7af7d585d538a7a0ca143e2d4cc417 under acceptance.
External evidence: N/A (no owned requirement needs live infra).
Open P0/P1: none.
Open P2/P3: DEF-W36-004 (P3 routed, AGENTS.md guidance ownership).
Two-fix gate: PASS (FIX-A packaged-artifact vs FIX-B docs-surface: different defect IDs, root causes, files, and evidence).
Wave decision: GO (worker) — pending fresh independent audit.

FIX-B: manifest authoring contract + public surface correction (EN+TR)
DEF: DEF-W36-002 (no manifest contract for authors) + DEF-W36-003 (stale top-right-button claim in 5 spots)
Root cause: W32 codified the manifest contract in code/tests only; surface text predates the V2 wx menubar (no Plugins button exists — menubar menu only, _on_plugins unbound).
Before EV: grep shows provider_ids/optional_dependencies/requires_app/entrypoints absent from PLUGINS docs; "top-right" present in README/PLUGINS/HELP.
After EV: EV-W36-001 (contract test binds documented keys/vocabulary/pins to validator constants; surface test bans the stale claim and asserts real menu/tab/command bindings).
Regression test: test_docs_manifest_contract_matches_schema + test_docs_optional_quota_without_dummy_values + test_docs_surface_plugin_entry_points_match_wx
Sensitivity proof: docs-link suite still passes (no new local links); agent-guidance failure identical with/without W36 diff (pre-existing, routed).
New/modified tests: tests/test_w36_packaged_docs.py (20 new; matrix/packaging/contract/audit/unit taxonomy in file).
Skipped/xfail changes: none (packaging-marked test runs in the default suite when the wheel exists; skips explicitly otherwise).
Package evidence: see FIX-A.
External evidence: N/A.
Open P0/P1: none.
Open P2/P3: DEF-W36-004 (P3 routed).
Two-fix gate: PASS (see FIX-A).
Wave decision: GO (worker) — pending fresh independent audit.
