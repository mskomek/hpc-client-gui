# Zero-Primary Dispositions

Frozen baseline: 12ce79935bf076e1062c57dc7dbd148bad2bfae1
Taxonomy snapshot SHA: 6cad198dca6c0f69bc8196f5030a7aebcba9d696
Current collected nodes: 2656
Current zero-primary nodes: 6

These six nodes remain unclassified because Packet A reproduced their failures on the frozen baseline. The first five are among the seven archived isolated failures. The wx shell stress case is a separately confirmed supplemental baseline-signature failure. They are explicit exceptions, not successful coverage, and are preserved in the ratchet allowlist.

| Node | Baseline class | Evidence |
| --- | --- | --- |
| tests/test_macos_ci.py::test_macos_ci_matrix_covers_both_native_architectures | ARCHIVED_BASELINE_FAILURE | workflow file missing at frozen baseline |
| tests/test_macos_ci.py::test_macos_ci_has_no_release_upload_or_signing_step | ARCHIVED_BASELINE_FAILURE | workflow file missing at frozen baseline |
| tests/test_macos_release_workflow.py::test_release_preflight_shares_the_ci_test_suite | ARCHIVED_BASELINE_FAILURE | workflow file missing at frozen baseline |
| tests/test_workflow_action_pins.py::test_every_workflow_exists | ARCHIVED_BASELINE_FAILURE | test expects ci.yml and release.yml; only release.yml exists |
| tests/test_wx_packaged_smoke.py::test_packaged_wx_smoke_gate_reports_critical_stages | ARCHIVED_BASELINE_FAILURE | test expects PASS while smoke reports missing artifact and FAIL |
| tests/test_wx_shell_p0_stress.py::test_wx_shell_p0_stress_real_wx_paths | SUPPLEMENTAL_BASELINE_FAILURE | The frozen baseline reproduces KeyError: 'update' before the stress assertions; it is supplemental to Packet A's seven archived failures. |

The complete machine-readable fields (owner packet, rewrite/deletion policy, comparison requirement, and final status) are in audit/test-taxonomy/zero-primary-disposition.json. The taxonomy snapshot SHA identifies the code/test state whose actual pytest markers were reported; the final governance HEAD is recorded separately in the execution report. The original seven-failure inventory and incomplete-full-suite caveat remain in the frozen baseline archive. The two latent product defects found by stronger Packet M tests are recorded separately and are not zero-primary exceptions.
