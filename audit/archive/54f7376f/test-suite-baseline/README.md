# Test-suite remediation baseline

- Original frozen audit SHA: `12ce79935bf076e1062c57dc7dbd148bad2bfae1` (2673 collected nodes).
- Remediation baseline SHA: `54f7376f3e3e1fccd672f121e33b68d2e8df2652` (2678 collected nodes).
- Collection errors: 0.
- Collection delta: 2673 → 2678; 5 added, 0 removed.
- Exact current node IDs: `nodeids.txt`; machine-readable record: `baseline.json`.

Added node IDs:

- `tests/test_wx_updater_spec.py::test_install_without_verified_artifact_stays_failed`
- `tests/test_wx_updater_spec.py::test_show_update_available_wrapper_returns_false_for_cancel`
- `tests/test_wx_updater_spec.py::test_show_update_available_wrapper_returns_false_for_close`
- `tests/test_wx_updater_spec.py::test_show_update_available_wrapper_returns_true_when_download_starts`
- `tests/test_wx_updater_spec.py::test_update_release_notes_preserve_unicode`

The frozen node list and metadata are preserved in `../../12ce7993/test-suite-baseline/`. The embedded-terminal node change noted in the dirty develop worktree is not included in this committed baseline and is not treated as an established rename. Collection verifies discovery only; it is not a test-result or release-readiness claim.
