# Packet J — resource and concurrency review

The reviewed tests now assert bounded progress, ownership, ordering, and cleanup
at the real service/UI boundary. External network and SSH seams remain local
test servers or fakes; no live cluster or user resource is used.

## Channel and transfer ownership

- `tests/test_connection_advanced_settings.py::TransferChannelSafetyTests::test_workers_receive_distinct_channels`
  now calls the production `SFTPChannelManager.open_transfer_sftp()` from two
  barrier-synchronized workers. Only Paramiko's channel constructor is faked.
  It verifies distinct channel owners, the 60-second timeout, worker completion,
  and close of both handles.
- `tests/test_selected_job_context.py::TestSelectedJobStoreThreadSafety::test_concurrent_subscribe_and_select`
  synchronizes three subscribe/unsubscribe workers with 20 selections. Each
  listener receives the complete ordered generation/job snapshot for its
  subscription interval, all threads join within a bound, and no listener sees
  a later selection after unsubscribe.
- `tests/test_transfer_concurrency.py::test_two_ftp_transfers_overlap_with_distinct_connections`
  uses the disposable local FTP server, proves peak overlap is two, records two
  distinct live FTP connection identities, and compares uploaded content by
  SHA-256.
- `tests/test_transfer_concurrency.py::test_cancelled_transfer_releases_isolated_backend`
  now starts the real TransferDialog/TransferController worker, waits for its
  backend upload to enter, dispatches `cancel_all()`, and releases the blocked
  progress operation. It verifies the current item is retained as cancelled,
  no second item starts, and the allocated backend closes.
- `tests/test_ftp_widget.py::FtpWidgetTests::test_transfer_dialog_runs_up_to_parallel_limit`
  records active and peak workers behind a release event; it verifies exactly
  two of three queued items start before release, peak concurrency stays two,
  all items finish, and cleanup releases/joins the worker on every exit path.
- `tests/test_download_cancel_wire.py::_run_until_cancelled` now cancels from
  the observed progress callback once the threshold is crossed. This removes
  the polling watcher thread and timing sleep while retaining the real local
  SSH/SFTP wire assertions for partial-file retention, retry, and session
  usability.

## wx ownership and skip review

Updater progress coverage now drives the real wx callback from a patched
download seam and checks the resulting byte label, gauge, and percentage. The
unknown-length case checks the visible indeterminate state. The download-button
test waits for the actual worker entry, and cancellation/close/late-callback
tests assert worker ownership and cleanup rather than only internal state.

Five tests previously skipped as “flaky” or “polluted” are now exercised:

| Previous skip | Current evidence | Result |
| --- | --- | --- |
| `tests/test_wx_jobs_behavior.py::test_wx_job_output_pause_keeps_refreshing_but_stops_live_follow` | Current related node `test_wx_job_output_manual_refresh_updates_while_follow_is_paused` checks that an explicit refresh updates output while live follow is paused. It does not prove automatic polling is stopped. Companion `test_pause_suppresses_regular_output_refresh_until_resume` verifies the normal non-forced refresh path is suppressed while paused and works after resume. | Pass |
| `tests/test_wx_jobs_behavior.py::test_wx_job_output_minimize_suspends_follow_and_restore_resumes_it` | Exercises minimize/restore events and visible output/polling state. | Pass |
| `tests/test_wx_jobs_behavior.py::test_wx_job_output_does_not_overlap_remote_reads` | Removed the global-window-count skip. Calls the normal coalesced refresh path while a read is blocked and asserts peak reads is one and the worker is off the GUI thread. | Pass |
| `tests/test_wx_jobs_behavior.py::test_wx_job_output_discards_stale_result_after_job_selection_changes` | Uses separate gates for jobs A and B; after A is released, asserts its stale output is not displayed while B is blocked, then verifies B is displayed. | Pass |
| `tests/test_hardening_additional.py::test_wx_separator_lifecycle_offscreen` | Removed the unconditional skip and fail-open conversion of shell creation failures, duplicate-handler output, and Windows heap/access violations into skips or success. The subprocess now requires all five visible menu states and a zero exit code. It still skips only when wx cannot be imported. | Pass |

The failed stress assertion encountered while unskipping these cases was also
reviewed. `tests/test_wx_jobs_stress.py::test_wx_jobs_stress_pause_resume_state_never_desynchronizes`
expected “Pause All” to keep replacing visible output and expected the stale
label “Pause Live Follow”. The current contract distinguishes automatic live
follow from an explicit refresh: the former is suppressed while paused, while
the latter remains available. The behavior module now checks the regular
refresh guard and explicit refresh path separately; the stress test exercises
100 pause/resume transitions through explicit refreshes.

`tests/test_wx_jobs_stress.py::test_wx_jobs_stress_blocked_reads_never_overlap`
uses the normal coalesced refresh callback rather than a forced refresh helper.
It measures peak in-flight reads and confirms every read runs off the GUI
thread. The direct `MockHPCJobs` worker exercise
`test_wx_jobs_stress_backend_workers_and_reads_are_bounded` was removed: its
test-double-only worker assertions are now covered through the production
Jobs refresh path, and an exact repository search found no direct selector or
workflow reference to that node.

`tests/test_wx_terminal_webview.py::test_wx_terminal_100_reconnects_no_leak`
now retains each prior SSH fake and checks its subscriber is removed after each
reconnect, then checks close removes the last subscriber. The WebView
availability check remains an environment skip when that optional backend is
absent.

`tests/test_editor_flow.py` had no resource/concurrency claim or flaky skip to
repair; its 14-node module passed, and its fixture owns and closes the editor.
No production code changed and no newly exercised Packet J test exposed a
product defect.

## Validation

- Five formerly skipped tests: **5 passed** (four wx Jobs nodes plus the wx
  separator subprocess; the renamed pause owner is counted in the four).
- Transfer/channel focus group: **7 passed**.
- `tests/test_connection_advanced_settings.py`: **20 passed**.
- `tests/test_selected_job_context.py`: **21 passed**.
- `tests/test_transfer_concurrency.py`: **10 passed**.
- `tests/test_download_cancel_wire.py`: **4 passed**.
- `tests/test_ftp_widget.py::FtpWidgetTests::test_transfer_dialog_runs_up_to_parallel_limit`:
  **1 passed**.
- `tests/test_editor_flow.py`: **14 passed**.
- `tests/test_wx_jobs_behavior.py`: **5 passed**.
- `tests/test_wx_jobs_stress.py`: **11 passed**.
- Taxonomy RATCHET and collection passed: **2,684 collected, 0 collection
  errors**, with no unexplained node changes. Ruff and `git diff --check` passed.

### Windows release-suite follow-up

The later Windows release-suite continuation reported both non-strict WebView
xfails as XPASS. Their subprocess tests passed when run without the xfail
markers, and the entire module then passed **29 tests** with no xfail or xpass.
The obsolete non-strict xfail annotations were removed; these two cases now
fail normally if their ordering assertions regress. This changes no nodeids and
does not establish packaged keyboard-to-PTY parity.

### Current governance-base re-evaluation (2026-09-13)

The historical Packet J result for
`tests/test_hardening_additional.py::test_wx_separator_lifecycle_offscreen`
is superseded for current-state reporting. Its later isolated subprocess run on
the reconciled governance worktree exceeded the 30-second bound. This is an
unresolved native wx lifecycle timeout; the earlier pass remains historical
evidence only. No product defect has been confirmed from this timeout, and it
must not be counted as a current pass.

### Re-evaluation on the v3 reconciled worktree (2026-09-13)

- `tests/test_wx_65a_stress.py::test_wx_65a_integrated_stress`: an earlier run
  passed in **214.57s**; the later isolated run passed in **133.20s**. The
  measured test invariants were zero. WebView2 logged
  `WebViewCreated` operation-aborted diagnostics during rapid detached-shell
  cycles, but neither run reported heap corruption.
- `tests/test_wx_shell_p0_stress.py::test_wx_shell_p0_stress_real_wx_paths`:
  the test assertions passed in **176.31s**, but an asynchronous remote-files
  completion callback raised `RuntimeError: wrapped C/C++ object of type
  Notebook has been deleted` in `wx_remote_files_view.py` while reading
  `notebook.GetSelection()`. This is a confirmed product lifecycle defect;
  no production change was made.
- `tests/test_hardening_additional.py::test_wx_separator_lifecycle_offscreen`:
  **failed** because its child process exceeded the explicit 30-second timeout
  (`subprocess.TimeoutExpired`). This remains an unresolved native lifecycle
  timeout and is not reclassified as flaky or passing.
- `tests/test_wx_embedded_terminal.py`: **10 passed**; the formerly reported
  find-button node passed alone, and the entire isolated-panel module passed.
- `tests/test_wx_terminal_behavioral.py`: **19 passed**, including the former
  find-next/previous WebView close node.
- `tests/test_wx_terminal_parity_evidence.py`: **10 passed** in child-process
  isolation; no native crash reproduced in this run. These adapter/bridge
  results do not establish packaged terminal parity.
- `tests/test_wx_remote_file_actions_behavior.py`: **28 passed** after its
  fixture began restoring both global language and shared clipboard state and
  yielding through deferred wx destruction. The module no longer emitted the
  prior `UnregisterClass` shutdown warning.

### Additional reconciled wx evidence (2026-09-13)

- `tests/test_wx_files_sync_compare.py`: **8 passed in 18.11s** after removing
  direct-handler shortcuts from the normal navigation cases and replacing two
  vacuous `or True` assertions with exact recovery and queued-callback checks.
- `tests/test_wx_file_context_matrix.py`: **10 passed in 2.32s**;
  `tests/test_wx_file_actions_stress.py`: **5 passed in 14.43s**. Their wx
  fixtures now restore the prior language and drain deferred window teardown;
  neither module emitted the prior `UnregisterClass` warning.
- `tests/test_wx_ansys_view.py`: **8 passed in 2.72s**, including a queued
  linter completion invoked after frame destruction and exact visible
  English/Turkish/English button-label refresh checks.
- `tests/test_wx_a11y.py`: **2 passed in 2.90s** after asserting real Files
  and Terminal page visibility rather than accepting an unconditional true.
- `tests/test_wx_embedded_terminal.py`: **10 passed in 4.00s** with primary
  categories split by behavior: visible panel actions are GUI tests, direct
  key-input rules are unit tests, and shell/PTY composition is integration.
- `tests/test_lssrv_auto_refresh.py`: **13 passed**; the two raw-output tests
  assert the actual visible controls are shown before checking their contents.
- `tests/test_wx_jobs_stress.py`: **10 passed in 35.74s** after removal of the
  fake-only recovery node; its visible Jobs owner is separately exercised by
  `test_wx_jobs_final_fix.py::test_outputs_no_job_zero_channels_waiting_and_pause_reset`.
- `tests/test_wx_file003_final_stress.py`: **11 passed in 183.43s**. The run
  completed all recorded local/remote mutation, navigation/completion race,
  transfer, reconnect, and close-in-flight counts; wrong targets, stale UI
  overwrites, destroyed-control callbacks, leaked workers/windows, and lost or
  duplicate transfers were all zero. Peak local/remote mutation concurrency
  remained one.
- `tests/test_wx_layout_resize.py::test_wx_layout_resize`: **1 passed in
  139.35s**. It completed 400 English/Turkish resize cases and 2,800 tab
  selections with all measured geometry, clipping, overflow, layout-exception,
  and detached-window invariants at zero. Its locale persistence is redirected
  to temporary storage, and locale/wx resources are restored by fixture even
  if the long sweep fails.
- `tests/test_wx_separator_lifecycle_offscreen` has a current module run with
  **11 passes and 1 subprocess failure**: the child exited with Windows status
  `0xC0000374` (heap corruption). This supersedes its earlier isolated pass and
  timeout as unresolved native-runtime evidence; it is not a test pass.

### v4 governance revalidation (2026-09-13)

The v4 branch is based on remediation SHA `1de2dce3aa8af037033882b26029fb33f39f9f57` and its source tree matches the fully reviewed v3 tree. The exact updater module passed **22/22** in an isolated child; terminal WebView passed **29/29** in a separate bounded child, including both ordering tests and visible fallback checks. About's real dialog/no-network node passed alone (1/1), while a combined Qt/WebView process raised a Windows native access violation at that node after the two preceding modules; this is order-dependent/native instability evidence, not a pass for the combined run. The separator lifecycle node remains unresolved: the timing sweep recorded a 30-second child timeout and a later module run recorded `0xC0000374` heap corruption. Do not label it flaky or passing.

The authoritative v4 release runner's current product failure is `tests/test_wave2_directories_local_files.py::TestErrorHandling::test_list_entries_permission_error`; its repeated `stat` through `Path.is_dir()` escapes the intended permission-error handling. The coverage runner reaches the same failure and reports 46% partial coverage before stopping. Full current outcomes are in `audit/archive/794226e/test-suite-final/release-suite-outcomes.json`.
