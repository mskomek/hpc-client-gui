# Final develop reconciliation — 2026-09-14

## 1. Repository state

| Item | Value |
| --- | --- |
| `origin/develop` starting SHA | `37eebc17f6ca5db947cb51c50c6c17b67f089475` |
| Closeout branch | `test-suite-governance-integration-closeout-20260913` |
| Closeout SHA | `d82e6ba1e43303e68b05cebb98eab645174fc362` |
| Reconciliation branch | `test-suite-final-develop-reconcile-20260914` |
| Reconciliation worktree | `D:/Projeler/hpc-client-gui-final-develop-reconcile` |

The reconciliation branch was created directly from `origin/develop`, not from
the closeout branch. Every pre-existing worktree, including the dirty primary
`develop` checkout at `D:/Projeler/hpc-client-gui`, was left untouched: no
reset, no clean, no stash.

## 2. Closeout commit review

| Commit | Purpose | Status on current develop | Action |
| --- | --- | --- | --- |
| `c1f3642e` | `fix: preserve wx app ownership across test lifecycle` | Missing. `tests/conftest.py` had no app-replacement guard; `tests/test_wx_files_sync_compare.py` still created an ad-hoc unowned `wx.App` in `_get_files_page` and had no module fixture or forced-GC regression. | KEEP / reimplemented |
| `a2c0f6e1` | `docs: finalize integration closeout` | Partially present. `docs/testing/PHASE_2_EXECUTION_REPORT.md`, `docs/testing/TEST_SUITE_INTEGRATION_CLOSEOUT_2026-09-13.md` and `docs/testing/TEST_TAXONOMY_FINAL_REPORT.md` all exist on develop with newer, different content; the two `audit/test-governance/integration-closeout-20260914/*.json` evidence files are absent. | SKIP — restoring them would overwrite newer develop documentation with stale closeout text. This report supersedes them. |
| `d82e6ba1` | `docs: add integration closeout continuation report` | Missing (`rapor_closeout_2026-09-14.md`). Documentation only; it describes the historical closeout run, not the current develop tree. | SKIP — superseded by this report. |

No product, service, or `src/` change was carried from the closeout branch;
`c1f3642e` touched test infrastructure only.

## 3. wx.App ownership

### Missing semantics on develop

* No guard around `wx.App.__init__`: creating a second `wx.App` replaced the
  process-global C++ application without destroying the first wrapper, so a
  later garbage-collection pass could deallocate the abandoned wrapper, tear
  down the live application, and make the next control raise `PyNoAppError`.
* `tests/test_wx_files_sync_compare.py::_get_files_page` created an unowned
  `wx.App(False)` on demand and kept no strong reference to it.

### Final implementation (current develop architecture)

* `tests/conftest.py` — the existing `_wx_app_init_without_modal_logging`
  wrapper now destroys the previous application while it is still the current
  application and before the replacement exists. At most one live native
  `wx.App` survives a replacement, and the abandonment time bomb is removed.
  The pre-existing `wx.Log.SetActiveTarget(wx.LogStderr())` behaviour is
  preserved unchanged.
* `tests/test_wx_files_sync_compare.py` — a module-scoped autouse `wx_app`
  fixture owns the application for the whole module, holds a strong reference
  for its lifetime, destroys only windows it did not inherit, yields before
  teardown, and destroys the application only when the fixture created it
  (`owns_app`). A shared, pre-existing app is left to its owner.
* `_get_files_page` no longer creates an application. It raises if no
  application exists, so ad-hoc unowned creation cannot reappear silently.

Invariants satisfied: at most one live native App at replacement time; a
replaced wrapper cannot GC-destroy the current native App; shared Apps are
destroyed only by their owner; the module suite keeps a strong reference;
windows are destroyed before owned App teardown; no ad-hoc unowned App creation
remains in the sync/compare suite.

### Forced-GC regression

Node: `tests/test_wx_files_sync_compare.py::test_wx_files_sync_app_survives_forced_collection`

Behaviour: builds a shell through the fixture-owned App, closes it, drops every
strong reference, forces `gc.collect()`, asserts `wx.App.Get() is wx_app`, then
builds and closes a second shell and asserts ownership again.

Taxonomy: primary `gui`; qualifiers `regression`, `resource`, `semantic`, `wx`.

Mutation evidence (observed, not assumed):

| Mutation | Result |
| --- | --- |
| Restore unconditional ad-hoc `wx.App(False)` in `_get_files_page` | Node FAILS (`AssertionError` at `tests/test_wx_files_sync_compare.py:102`). |
| Remove only the conftest replacement guard, fixture ownership intact | Node still passes in isolation. The guard protects a process-wide invariant across modules that create their own applications; this node owns the ownership invariant, not the guard. Recorded truthfully rather than claimed as covered. |

## 4. Remote empty-name filter — confirmed, not rewritten

`src/hpc_gui/services/file_filter_registry.py:134` `_entry_name` already returns
a meaningful non-empty name and otherwise derives the basename from the entry
path. Confirmed in place; no change made.

## 5. Newer develop semantics preserved

`scripts/release_test_suite.py` isolated groups, the updater `_zip_path`
behaviour, plugin schema compatibility gating and the deterministic
threading/event behaviour on develop were all left untouched. No stale
governance assertion was restored. Verification:

    python -m pytest tests/test_release_test_suite.py tests/test_wx_updater_spec.py \
      tests/test_wx_remote_file_actions_behavior.py::test_wx_remote_navigation_sort_and_provider_filter_are_visible \
      tests/test_file_filter_registry.py -q
    -> 50 passed in 4.27s

## 6. Confirmed-defect regressions (reconciliation branch)

| Defect | Canonical owner | Result |
| --- | --- | --- |
| Local directory permission handling | `tests/test_wave2_directories_local_files.py::TestErrorHandling::test_list_entries_permission_error` | PASS |
| Rename selection preservation | `tests/test_wave2_wx_ui_parity.py::TestSelectionPreservation::test_rename_preserves_selection` | PASS |
| Destroyed Notebook callback | `tests/test_wx_file_actions_lifecycle.py::test_wx_embedded_remote_callback_after_notebook_destroy_is_ignored` | PASS |
| Jobs output remote-read overlap | `tests/test_wx_jobs_behavior.py::test_wx_job_output_does_not_overlap_remote_reads` | PASS |
| Plugin-menu lifecycle | `tests/test_ui_contributions.py::test_lifecycle_install_without_restart` | PASS |
| Remote empty-name filter | `tests/test_wx_remote_file_actions_behavior.py::test_wx_remote_navigation_sort_and_provider_filter_are_visible` | PASS |
| wx.App forced-GC ownership | `tests/test_wx_files_sync_compare.py::test_wx_files_sync_app_survives_forced_collection` | PASS |

`7 passed in 5.07s`.

## 7. Taxonomy

| Metric | Value |
| --- | --- |
| Collected nodes | 2710 |
| Collection errors | 0 |
| Zero-primary | 0 |
| Multi-primary | 0 |
| Semantic-review gaps | 0 |
| `direct_test_calls` warnings | 0 |
| `catch_all_filenames` warnings | 0 |

Ratchet baseline:
`audit/test-governance/integration-closeout-20260913/taxonomy-ratchet-strict.json`
(zero-debt). Result: `RATCHET: PASS`, exit 0. No allowlist debt introduced.

## 8. Collection delta

Baseline `37eebc17` (clean worktree) 2709 nodes -> reconciliation 2710 nodes.

| Change | Node | Explanation |
| --- | --- | --- |
| Added (1) | `tests/test_wx_files_sync_compare.py::test_wx_files_sync_app_survives_forced_collection` | The reimplemented forced-GC ownership regression. |
| Removed (0) | — | — |
| Renamed (0) | — | — |

## 9. Reconciliation branch validation

| Command | Exit | Result |
| --- | --- | --- |
| `python -m pytest tests --collect-only -q` | 0 | 2710 collected, 0 errors |
| `python scripts/check_test_taxonomy.py --mode report` | 0 | zero-primary 0, multi-primary 0 |
| `python scripts/check_test_taxonomy.py --mode ratchet --baseline .../taxonomy-ratchet-strict.json` | 0 | RATCHET: PASS |
| `python -m compileall -q src/hpc_gui` | 0 | PASS |
| `python -m ruff check src tests scripts` | 0 | All checks passed |
| `python scripts/check_i18n.py` | 0 | key / reference / hardcoded-text checks OK |
| `python scripts/smoke_test.py` | 0 | smoke test: OK |
| `git diff --check` | 0 | clean |
| `python -X faulthandler scripts/release_test_suite.py` | 0 | all release preflight gates passed, 1336s |
| `python scripts/release_test_suite.py --coverage` | 0 | 66.77% >= 65%, 1630s |

Authoritative release suite totals: 2680 passed, 0 failed, 26 skipped,
6 deselected, 0 xfail, 0 xpass, 29 subtests passed, 13 isolated groups.
No native termination and no faulthandler traceback were observed.

## 10. Local merge and remote push

See the appendix at the end of this file.

## 11. Release readiness

Develop integration readiness is not release readiness. The following external
evidence is unchanged by this reconciliation and is still owned outside the
repository test suite:

* Windows packaged smoke — separate evidence.
* GUI-TERM-001 — separate evidence.
* Linux packaged runtime — separate evidence.
* macOS packaged runtime — separate evidence.
* Live cluster verification — separate evidence.
* Manual GUI sign-off — separate evidence.
