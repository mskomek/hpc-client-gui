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

Five tests previously skipped as “flaky” or “polluted” are now exercised:

| Previous skip | Current evidence | Result |
| --- | --- | --- |
| `tests/test_wx_jobs_behavior.py::test_wx_job_output_pause_keeps_refreshing_but_stops_live_follow` | Renamed to `test_wx_job_output_pause_freezes_and_resume_updates_output`; checks visible output stays unchanged while Pause All is active and updates after resume. It carries `gui`. | Pass |
| `tests/test_wx_jobs_behavior.py::test_wx_job_output_minimize_suspends_follow_and_restore_resumes_it` | Exercises minimize/restore events and visible output/polling state. | Pass |
| `tests/test_wx_jobs_behavior.py::test_wx_job_output_does_not_overlap_remote_reads` | Removed the global-window-count skip. Calls the normal coalesced refresh path while a read is blocked and asserts peak reads is one and the worker is off the GUI thread. | Pass |
| `tests/test_wx_jobs_behavior.py::test_wx_job_output_discards_stale_result_after_job_selection_changes` | Uses separate gates for jobs A and B; after A is released, asserts its stale output is not displayed while B is blocked, then verifies B is displayed. | Pass |
| `tests/test_hardening_additional.py::test_wx_separator_lifecycle_offscreen` | Removed the unconditional skip and fail-open conversion of shell creation failures, duplicate-handler output, and Windows heap/access violations into skips or success. The subprocess now requires all five visible menu states and a zero exit code. It still skips only when wx cannot be imported. | Pass |

The failed stress assertion encountered while unskipping these cases was also
reviewed. `tests/test_wx_jobs_stress.py::test_wx_jobs_stress_pause_resume_state_never_desynchronizes`
expected “Pause All” to keep replacing visible output and expected the stale
label “Pause Live Follow”. The runtime contract is that paused output is frozen
and refreshed again on resume; the test now checks that behavior through 100
pause/resume transitions.

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
