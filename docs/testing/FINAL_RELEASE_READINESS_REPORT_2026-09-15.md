# Final release-readiness evidence — 2026-09-15

This is an evidence record, not a release announcement. **No application
release, tag, or published artifact was created.** Everything below is the
state of the repositories and of what was actually observed on this machine
on 2026-09-15.

Verdicts use exactly: **PASS**, **FAIL**, **NOT EVIDENCED**, **PARTIAL**.

| Area | Verdict |
| --- | --- |
| Repository integrity | PASS |
| Application develop validation | PASS |
| Plugin contract validation | PASS |
| Packaged Windows evidence | PARTIAL |
| Terminal parity (GUI-TERM-001) | PARTIAL |
| Linux packaged evidence | NOT EVIDENCED |
| macOS packaged evidence | NOT EVIDENCED |
| Live cluster evidence | NOT EVIDENCED |
| Manual GUI evidence | NOT EVIDENCED |

---

## 1. Repository integrity — PASS

### Application (`mskomek/hpc-client-gui`)

| | |
| --- | --- |
| Initial local `develop` | `55bb2bfda07a4744e4438ebca58ed7c6e91cf999` |
| Initial `origin/develop` | `55bb2bfda07a4744e4438ebca58ed7c6e91cf999` |
| Final `origin/develop` | see §7 |
| `origin/main` | `063d83b523be377d4ef02dc8a61e2fdd15876ecc` — **unchanged** |

Local `develop` was already identical to `origin/develop` at the start, with a
clean tracked worktree. No stash, patch backup, or safety branch was needed.
Pre-existing untracked files (`.integration-recovery/`, `audit.zip`,
`waves.zip`, `docs/TEST_SUITE_AUDIT_REPORT_12ce7993.md`, five `scripts/*.py`
helpers, `tests/WAVE2_REMAINING_TEST_PROMPTS.md`) were left untouched and
uncommitted.

Application automatic push/PR CI remains disabled; no workflow file was
touched.

### Plugin registry (`mskomek/hpc-client-gui-plugins`)

| | |
| --- | --- |
| Initial `origin/main` | `602e904bfd4120b3bd65b3f172d14638fe817f50` |
| Initial `origin/develop` | `784cf8e2f1cf0be20eae6590d5493ae4d1e18741` |
| Merge base | `a320cde6affe9072523a49352b2d688e050168b3` |
| Divergence | main-only 3 / develop-only 18 |
| Final `origin/develop` | `9880283f9761027cdd9aa3d5a97d7a748a522da6` |
| `origin/main` | `602e904...` — **unchanged** |

---

## 2. Application develop validation — PASS

All commands run on Windows 11, Python 3.12.4, `PYTHONPATH=src`.

| Gate | Result |
| --- | --- |
| `python -m pytest tests --collect-only -q` | 2712 collected, **0 collection errors** |
| `check_test_taxonomy.py --mode report` | zero-primary 0, multi-primary 0, semantic gaps 0 |
| `check_test_taxonomy.py --mode ratchet` | RATCHET: PASS (no new zero-primary) |
| `python -m compileall -q src/hpc_gui` | PASS |
| `python -m ruff check src tests scripts` | PASS |
| `python scripts/check_i18n.py` | PASS (key, reference, hardcoded-text) |
| `python scripts/smoke_test.py` | PASS |
| `git diff --check` | PASS |
| `python -X faulthandler scripts/release_test_suite.py` | **exit 0** — 2387 passed, 26 skipped, 6 deselected, 29 subtests, 602 s main body; no native crash, no WER dialog |
| `python scripts/release_test_suite.py --coverage` | **exit 0** — coverage 66.77% ≥ 65% threshold |

The release suite ran against the tree before the two test-only commits below;
the changed files were re-verified individually afterwards (contract suite 18
passed, parity evidence suite 11 passed), and collection, ruff, taxonomy,
i18n, and smoke were re-run on the final tree.

### Regression owners — all PASS

| Defect | Owner | Result |
| --- | --- | --- |
| Local directory permission handling | `test_wave2_directories_local_files.py::TestErrorHandling::test_list_entries_permission_error` | PASS |
| Rename selection preservation | `test_wave2_wx_ui_parity.py::TestSelectionPreservation::test_rename_preserves_selection` | PASS |
| Late async callback after destroyed remote Notebook | `test_wx_file_actions_lifecycle.py::test_wx_embedded_remote_callback_after_notebook_destroy_is_ignored` | PASS |
| Jobs remote-read overlap | `test_wx_jobs_behavior.py::test_wx_job_output_does_not_overlap_remote_reads` | PASS |
| Plugin-menu connected → hidden lifecycle | `test_ui_contributions.py::test_condition_disable_hide_behavior`, `::test_capability_condition`, `::test_version_switch_rebuilds` | PASS |
| Remote empty-name filter | `test_file_filter_registry.py::TestEdgeCases::test_empty_name_entry` | PASS |
| wx.App forced-GC ownership | `test_wx_files_sync_compare.py::test_wx_files_sync_app_survives_forced_collection` | PASS |

`wx.App` ownership was also re-verified by inspection: the regression owner
carries the required taxonomy (primary `gui`; qualifiers `regression`,
`resource`, `semantic`, `wx`) and was not weakened.

The remote file filter contract in
`src/hpc_gui/services/file_filter_registry.py` still uses a meaningful
`entry.name` when present and otherwise derives the basename from `path`
(`_entry_name`, lines 134-142), so a `RemoteEntry` with `name == ""` and a
path ending in `run.log` still matches the Logs filter.

---

## 3. Plugin contract validation — PASS

### Real official plugin checkout

`HPC_GUI_CONTRACT_REPO` was pointed at a real checkout of the plugin registry
at the reconciled `develop` state:

```
python -m pytest tests/test_plugin_contract.py -q -rf
18 passed in 1.37s
```

**0 failures. 0 skipped. 0 environment-skips from a missing
`HPC_GUI_CONTRACT_REPO`.**

### Effective compatibility matrix

| Claim | Observed |
| --- | --- |
| App 1.5.8 cluster-profile capability | schemas 1-2 (`app_supports_schema("1.5.8", 3)` is `False`) |
| Pinned `APPLICATION_REF` capability | schemas 1, 2, 3, 4 |
| TRUBA 1.3.0 compatible with 1.5.8 | **YES** |
| TRUBA 1.4.0 compatible with 1.5.8 | **NO** (`>=1.5.9`) |
| TRUBA 1.5.0 compatible with 1.5.8 | **NO** (`>=1.5.9`) |
| Latest compatible TRUBA for 1.5.8 | **1.3.0** |
| Latest compatible TRUBA for the schema-capable line | 1.5.0 |

### Installer fail-closed boundary

A registry entry that claims an older floor cannot widen what installs: the
installer re-derives the floor from the immutable manifest, so a forged
`requires_app` on the TRUBA 1.4.0 entry still raises
`requires app >=1.5.9`. Independently, the capability matrix refuses schema 3
for the 1.5.8 line. Covered by
`test_registry_compatibility_claim_cannot_bypass_schema_rejection`.

### Plugin CI — real run

Workflow `Validate plugin registry`, run `34929629514`, head SHA
`9880283f9761027cdd9aa3d5a97d7a748a522da6`:

| Job | Status | Conclusion |
| --- | --- | --- |
| Validate (3.10) | completed | success |
| Validate (3.12) | completed | success |
| Validate (3.14) | completed | success |
| Consumer contract (schema-capable application pin) | completed | **success** |
| Lint (Ruff) | completed | success |

`continue-on-error` was removed from `consumer-contract`; both `validate` and
`consumer-contract` are blocking. The push to `develop` does not trigger the
workflow (its `push` trigger is `main`/tags only), so the run above was
started with `workflow_dispatch` on `develop`; pull requests trigger it
automatically.

`APPLICATION_REF` is the immutable application commit
`55eb70920f5cac27722ce76a435f0a318716c5c2`. It is a commit SHA, not a tag,
because **no schema-3/4 capable application release exists**. Policy, recorded
in `docs/CONSUMER_CONTRACT.md`: immutable tag or immutable commit SHA, never a
branch; replace with the release tag when such a release is published.

### Published plugin immutability

Machine-enforced by `published-plugin-lock.json` +
`scripts/published_lock.py`, checked inside `scripts/validate_registry.py`.
Matrix (`tests/test_published_immutability.py`, 11 passed):

| Case | Expected | Observed |
| --- | --- | --- |
| Unchanged historical package | PASS | PASS |
| Published manifest changed | FAIL | FAIL |
| Payload changed | FAIL | FAIL |
| Declared documentation changed | FAIL | FAIL |
| Entirely new plugin version | PASS | PASS |
| Registry-only compatibility override, bytes unchanged | PASS | PASS |
| Package mutated **and hashes regenerated** | FAIL | FAIL |

Historical migration: **ONE-TIME FROZEN EXCEPTION**, authority
`published-plugin-lock.json`. TRUBA 1.1.0, 1.2.0, and 1.4.0 had their
published manifests edited in place by commit `602e904` before any ledger
existed; TRUBA 1.5.0 was completed with its `README.md`/`sources.md` during
this reconciliation. The original bytes are recoverable from git history and
were deliberately **not** restored: released clients read `requires_app`
directly and know nothing of `compatibility_override`, so restoring the
original floors would re-advertise those packages to releases that cannot
validate their payload schema. Each exception is recorded with its reason in
the ledger and in `docs/PUBLISHED_PLUGIN_IMMUTABILITY.md`.

---

## 4. Packaged Windows evidence — PARTIAL

| | |
| --- | --- |
| Artifact built | **YES**, local only, **not published** |
| Build command | `pyinstaller -y --clean build/windows/hpc-client-gui.spec` |
| Application commit | `55eb70920f5cac27722ce76a435f0a318716c5c2` |
| Artifact | `dist/hpc-client-gui/hpc-client-gui.exe` |
| Artifact SHA-256 | `b8fb56d79a086482b2c9714b19be8eebb4966c674366bcf539b0d6afa2a9cf2e` |
| Embedded version | 1.5.9 |
| ONEDIR total size | 517.9 MB |
| `python.exe` in artifact tree | **absent** — no interpreter dependency leak |

`scripts/release.ps1` was audited first: it runs manifest/SBOM generation,
PyInstaller, local smokes, and a local `Compress-Archive`. It contains no
`git tag`, no `git push`, and no `gh release` — neither does any other script
in `scripts/`. The underlying PyInstaller command was invoked directly, so no
release-shaped path ran at all. Nothing was uploaded anywhere.

### Packaged smoke — NOT EVIDENCED (incomplete)

`scripts/wx_packaged_smoke.py` was run three times against this artifact. No
run completed:

- Run 1 aborted at the terminal keyboard stage, `runtime =
  keyboard_input:foreground_lost`.
- Runs 2 and 3 aborted with `timeout in packaged smoke phase 1`.

Both are environment guards, not observed product failures: the smoke drives
real keyboard input into the packaged window and needs an interactive desktop
session that keeps that window in the foreground. 49 leftover
`msedgewebview2` processes were observed on the machine, a plausible
contributor to the later phase-1 timeouts.

Run 1 reached these checks before aborting. They are recorded as observations,
**not** claimed as a current packaged PASS, because the run did not complete:

| Reached PASS in run 1 | Never ran / did not pass |
| --- | --- |
| `process_started`, `wx_runtime_started`, `main_frame_created`, `pty_resize`, `files_surface`, `editor_surface`, `jobs_surface`, `plugin_ansys_surface`, `diagnostics_updater_surface`, `files_controls`, `editor_controls`, `jobs_controls`, `editor_roundtrip` | `terminal_readback`, `pty_input_output`, `remote_file_roundtrip`, `job_roundtrip`, `transfer_queue_render`, `clean_shutdown` |

**Missing prerequisite:** an interactive Windows desktop session that holds the
packaged window in the foreground for the duration of the smoke, on a machine
without accumulated WebView2 host processes.

No evidence from any earlier artifact is reused.

---

## 5. Terminal parity — GUI-TERM-001 = PARTIAL

The full per-category record is
`docs/v2/GUI_TERM_001_EXECUTION_EVIDENCE.json`.

Source/runtime layer (real `wx.App`, real WebView, production adapter and
controller, disposable SSH/PTY backend): **PASS** across
`test_wx_terminal_parity_evidence.py` (11), `test_wx_terminal_webview.py`
(20), `test_wx_terminal_behavioral.py`, `test_terminal_bridge.py`,
`test_terminal_pty_wire.py` — covering Unicode, resize, paste, find,
alternate screen, reconnect, close/reopen, and resource cleanup.

Packaged layer against artifact `b8fb56d7...`: **NOT EVIDENCED** — no smoke
run completed.

### Exact remaining gaps

1. A completed `wx_packaged_smoke.py` run on the current artifact. This alone
   closes packaged WebView2 initialization, keyboard→backend, backend→rendered
   read-back, resize, and resource cleanup.
2. No packaged-layer Unicode terminal check exists (Turkish and Japanese input
   and rendered read-back). The packaged smoke has no such check.
3. No packaged-layer checks exist for clipboard/paste, find/search, alternate
   screen, or terminal close/reopen.
4. Linux and macOS packaged WebKit runtime: not built, not run.

### Documentation contradiction — fixed at the root

`tests/test_wx_terminal_parity_evidence.py::test_generate_parity_evidence`
**overwrote** `docs/v2/GUI_TERM_001_EXECUTION_EVIDENCE.json` on every suite
run with a hardcoded blob asserting "Windows Python 3.14 packaged wx WebView2
smoke is PASS" while the same file was marked PARTIAL. That test is why the
repository simultaneously claimed a packaged PASS and a packaged gap.

It now writes `docs/v2/GUI_TERM_001_SOURCE_RUNTIME_EVIDENCE.json`, labelled as
one evidence layer, and makes no packaged claim. The cross-layer record is
maintained by hand and states packaged evidence per artifact SHA.

---

## 6. Platform, cluster, manual, and Unicode evidence

| Area | Verdict | Missing prerequisite |
| --- | --- | --- |
| Linux packaged runtime | **NOT EVIDENCED** | A Linux build/runtime environment. None available from this Windows session; no Linux artifact was built or run. The historical Qt GPU/WebEngine workaround is not evidence for the current wx runtime and is not reused. |
| macOS packaged runtime | **NOT EVIDENCED** | macOS hardware. No app bundle was built. NFC/NFD normalization behaviour was not exercised. Nothing was simulated. |
| Live cluster / TRUBA | **NOT EVIDENCED** | An authorized test account. No SSH credential or configured test target was present; no connection, submission, or remote listing was attempted. |
| Manual packaged GUI sign-off | **NOT EVIDENCED** | An interactive desktop session with a human tester. The automated packaged smoke could not hold the foreground, and no manual checklist was walked. |

### Unicode

| Surface | Verdict |
| --- | --- |
| Windows — source/runtime | **PASS** (terminal Unicode input/output, Turkish and Japanese path and filename tests in the suite; full suite exit 0) |
| Windows — packaged | **NOT EVIDENCED** (no completed packaged run; no Unicode check exists in the packaged smoke) |
| Linux | **NOT EVIDENCED** |
| macOS | **NOT EVIDENCED** |
| Remote cluster | **NOT EVIDENCED** |

Mojibake regression: **PASS**. No `â˜…`, `Ã§`, `ÅŸ`, or `Ä°` sequence exists in
either repository's tracked text. The Turkish strings in the reconciled TRUBA
payloads are intact (`Standart Çıktı`, `Standart Hata`, `TÜBİTAK`) — note that
the *discarded* develop-only variant of TRUBA 1.4.0 had flattened those to
`Standart Cikti`, which is one reason the published payload was kept. No new
`.encode(`/`.decode(`/`latin1`/`cp125`/`errors="ignore"`/`errors="replace"`
call was introduced on any user-controlled path; the only added `.encode()`
calls are default-UTF-8 calls on synthetic registry fixtures in plugin tests.

---

## 7. Changed files

### Application — production code

None. No product code was changed.

### Application — tests

| File | Change |
| --- | --- |
| `tests/test_plugin_contract.py` | Split the oldest-line assertion: every published plugin must resolve on the current line, and the long-lived plugins (TRUBA, Fluent) must keep a version for the oldest served line. The community cluster providers were first published for `>=1.5.8`, so the old blanket assertion failed on a publication date. Added the explicit fail-closed boundary assertion. |
| `tests/test_wx_terminal_parity_evidence.py` | Stopped overwriting the curated cross-layer GUI-TERM-001 record; writes a source/runtime-scoped file instead and drops the unearned packaged-PASS claim. |

### Application — docs

| File | Change |
| --- | --- |
| `docs/v2/GUI_TERM_001_EXECUTION_EVIDENCE.json` | Rewritten as the curated cross-layer record: per-category A-L status, current artifact SHA, explicit packaged gaps, explicit list of claims *not* made. |
| `docs/v2/GUI_TERM_001_SOURCE_RUNTIME_EVIDENCE.json` | New, generated by the reporting test; source/runtime layer only. |
| `docs/testing/FINAL_RELEASE_READINESS_REPORT_2026-09-15.md` | This report. |

### Plugin — packages

| File | Change |
| --- | --- |
| `plugins/truba/1.1.0/manifest.json`, `plugins/truba/1.2.0/manifest.json` | `requires_app` `>=1.5.5` (schema 2 first shipped in 1.5.5), from main. |
| `plugins/truba/1.4.0/{manifest,cluster-profile,README,sources}` | Resolved to main's **published** bytes. develop carried a competing, never-published variant of the same version number that also dropped Turkish diacritics; under the new policy a content change requires a new version. |
| `plugins/truba/1.5.0/{manifest,cluster-profile}.json` | New schema-v4 package, from main. |
| `plugins/truba/1.5.0/{README.md,sources.md}` | Added and declared, so the package satisfies the provider quality gate. Recorded as a one-time frozen exception: it requires an application release that does not exist. |

### Plugin — registry

| File | Change |
| --- | --- |
| `registry.json` | develop's provider and ANSYS entries retained; TRUBA entries taken from main (corrected floors, regenerated manifest hashes, new 1.5.0). Re-serialised with LF endings, matching main and `.gitattributes`' byte-exactness intent — hence the large whitespace-only diff. |
| `published-plugin-lock.json` | **New.** Immutability ledger for every package published on main, with `frozen_reason` on each one-time exception. |

### Plugin — tests

| File | Change |
| --- | --- |
| `tests/test_published_immutability.py` | **New.** Runs the shipped validator over the full A-G matrix plus override-narrowing and ledger-refusal cases. |
| `tests/test_compatibility.py` | main's capability-aware suite, with develop's Plugin API v2 entry check retained; the oldest-line assertion split the same way as the application side. |
| `tests/test_registry.py`, `tests/test_truba_plugin.py` | From main. |

### Plugin — validation and workflow

| File | Change |
| --- | --- |
| `scripts/published_lock.py` | **New.** Ledger loader, digest recorder, and immutability checker. `--record` is additive and refuses to overwrite a frozen version. |
| `scripts/schema_compatibility.py` | From main, plus `effective_requires_app` / `override_error` for the registry-level compatibility override. |
| `scripts/validate_registry.py` | Override validation, schema-floor check against the *effective* range, and the repository-level immutability gate. |
| `schema/registry.schema.json` | Optional `compatibility_override` on a plugin entry. |
| `schema/cluster-profile.schema.json` | Union: main's stricter `job_outputs`/`output_stream`/`file_filter` definitions and v4, plus develop's v3 `access`/`requirements`. |
| `.github/workflows/validate.yml` | `APPLICATION_REF` pinned to `55eb7092`; `continue-on-error` removed; stale "informational" comment replaced. |

### Plugin — docs

| File | Change |
| --- | --- |
| `docs/PUBLISHED_PLUGIN_IMMUTABILITY.md` | **New.** The rule, the ledger, why rehashing cannot bypass it, the override precedence and its limits, and the recorded one-time exceptions. |
| `docs/CONSUMER_CONTRACT.md` | Pin, why the old pin made the job non-blocking, blocking status restored, immutable-tag-or-SHA policy. |
| `docs/RELEASE_NOTES.md`, `docs/WIKI_TRUBA.md`, `README.md` | Compatibility corrections from main; policy entry; immutability doc linked. |

---

## 8. Pushes

| Ref | Pushed |
| --- | --- |
| Application `develop` | **YES** — `55bb2bfd` → `55eb7092` (fast-forward) |
| Plugin `develop` | **YES** — `784cf8e` → `9880283` (fast-forward) |
| Application `main` | **NO** |
| Plugin `main` | **NO** |
| Force push | **NO** |
| Tag created | **NO** |
| Release created | **NO** |
| Published artifact | **NO** |

Both repositories were fetched immediately before pushing; neither remote had
moved.

Note: this work was carried out under an explicit instruction to push both
`develop` branches. `CLAUDE.md` in the application repository otherwise states
that only a verified `main` may be pushed to `origin`; the explicit
instruction governed here.

The application docs commit in §7 is pushed after this report is written; the
final application `develop` SHA is recorded in the accompanying status output.

---

## 9. Release-readiness summary

| | |
| --- | --- |
| Windows packaged | PARTIAL (built, smoke incomplete) |
| GUI-TERM-001 | PARTIAL (source/runtime PASS, packaged NOT EVIDENCED) |
| Linux packaged | NOT EVIDENCED |
| macOS packaged | NOT EVIDENCED |
| Live cluster | NOT EVIDENCED |
| Manual GUI | NOT EVIDENCED |

**RELEASE EVIDENCE INCOMPLETE.**

This is a statement about evidence coverage, not about defects: no failure of
the application was observed anywhere in this work. It is also not a request
for permission to publish — no release may be created from this report.

## 10. Remaining issues

1. The packaged smoke cannot run unattended: it requires an interactive
   foreground desktop session. Until that is available, or the smoke grows a
   headless input path, current-artifact packaged evidence is unobtainable
   from an automated session.
2. `scripts/wx_packaged_smoke.py` has no packaged checks for Unicode terminal
   I/O, clipboard/paste, find/search, alternate screen, or terminal
   close/reopen. Those GUI-TERM-001 categories cannot reach COVERED until such
   checks exist, regardless of the environment.
3. No Linux or macOS environment is reachable from this session, so those
   platforms have no current-artifact evidence at all.
4. No authorized cluster account is configured, so the live TRUBA path is
   unexercised.
5. The plugin repository's `validate.yml` does not run on pushes to `develop`
   (its `push` trigger is `main` and tags). The run recorded in §3 was
   dispatched manually. Pull requests are covered automatically.
