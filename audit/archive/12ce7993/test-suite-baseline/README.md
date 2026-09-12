# Frozen Test-Suite Baseline

Baseline SHA: 12ce79935bf076e1062c57dc7dbd148bad2bfae1

Collected: 2673

Collection errors: 0

Full suite completed: NO

Full-suite totals for passed, failed, skipped, xfailed, xpassed, and duration are unknown. Partial execution is not an authoritative full-suite result.

The full suite was not completed for these recorded reasons:

1. scripts/ci.py full could not enter its normal pytest coverage run because pytest-cov was missing in the audit environment. Pytest rejected the --cov options.
2. The release runner encountered a deterministic test-setup hang at tests/test_connection_advanced_settings.py::ParallelismSourceOfTruthTests::test_settings_dialog_has_no_global_parallelism_editor. The test patches Path.home with a default MagicMock; .exists() remains truthy in src/hpc_gui/config/storage.py::_next_config_backup, producing an infinite loop.
3. Seven isolated failures were reproduced on the frozen baseline, listed below. They are known isolated baseline failures, not the complete suite failure count.

## Known isolated baseline failures

- tests/test_macos_ci.py::test_macos_ci_matrix_covers_both_native_architectures — workflow file missing at the frozen SHA.
- tests/test_macos_ci.py::test_macos_ci_has_no_release_upload_or_signing_step — workflow file missing at the frozen SHA.
- tests/test_macos_release_workflow.py::test_release_preflight_shares_the_ci_test_suite — workflow file missing at the frozen SHA.
- tests/test_wave9_ci_unicode_matrix.py::TestResultsVerification::test_wx_unicode_smoke_cannot_fail_open — workflow file missing at the frozen SHA.
- tests/test_workflow_action_pins.py::test_every_workflow_exists — expects ci.yml and release.yml; only release.yml exists.
- tests/test_wx_packaged_smoke.py::test_packaged_wx_smoke_gate_reports_critical_stages — expects PASS although the smoke script reports the missing artifact and FAIL.
- tests/test_gui_audit_screenshots.py::test_manifest_exists_and_commit_current — stored manifest SHA 3a7294079b992d3ddcabc349bbeadf6988312b64 differs from baseline SHA.

These references preserve the seven isolated outcomes only; they do not claim that the full suite has exactly seven failures.

## Archive contents

- baseline.json — versioned collection and full-suite state.
- nodeids.txt — the collected baseline nodes, one per line.
- inventory-enriched.json — collected markers, fixtures, and partial observed inventory.
- proposed-taxonomy-heuristic.json — heuristic proposal only, not actual classifications.
- lane-inventory.json — Phase 1 current and archived lane mapping.
- duration-partial.json — partial execution observations only, not suite duration.
- static-findings.json — duplicate and source-shape audit findings.

The Phase 1 taxonomy proposal assigned every item heuristically and included a unit fallback. At the frozen baseline, current primary marker state was zero primary markers across the 2,673 collected tests. Proposal counts must not be read as actual marker counts.

inventory-enriched.json preserves both collected marker state and proposal fields. Its proposed_primary and proposed_qualifiers fields are heuristic suggestions, not pytest marker classifications.
