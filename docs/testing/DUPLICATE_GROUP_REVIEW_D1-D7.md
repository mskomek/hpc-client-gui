# Duplicate-group review D1–D7

Reviewed on `test-suite-governance-20260912-v2` after Packet C. Frozen comparison: `12ce79935bf076e1062c57dc7dbd148bad2bfae1`; remediation base: `54f7376f3e3e1fccd672f121e33b68d2e8df2652`.

## Decisions

| Group | Original owners and unique assertion review | Current owner and outcome |
|---|---|---|
| D1 — SSH decode policy | `tests/test_wave0_unicode_baseline.py::TestEncodingBoundaryInventory::test_errors_replace_in_ssh` and `tests/test_wave1_unicode_core_policy.py::TestEncodingBoundaryJustification::test_ssh_client_decode_justified` both asserted the source uses replacement decoding for lossy SSH output. The former remains the canonical static encoding-boundary audit; the second duplicate node was removed. | Retained `test_errors_replace_in_ssh`. This is source-policy evidence, not runtime decode evidence. |
| D2 — SFTP encoding claims | `tests/test_wave0_unicode_baseline.py::TestRiskClassification::test_p0_sftp_roundtrip_risks_documented` and `tests/test_wave1_unicode_core_policy.py::TestEncodingBoundaryJustification::test_files_ssh_utf8_justified` only asserted that `files_ssh.py` contains “utf-8”; neither proved byte preservation. Both nodes were removed. | Added `tests/test_ssh_files_byte_preservation.py::test_sftp_download_upload_roundtrip_preserves_arbitrary_bytes`. It drives `SSHFilesBackend.download` and `upload` through a fake SFTP seam, checks exact arbitrary-byte equality, and verifies every SFTP channel closes. |
| D3 — Wave78 cluster status | `test_cluster_servers_visible_without_selected_job_when_provider_supports` selected job 0 despite its name. The distinct `test_raw_server_status_opens` selected a job and observed only loaded status before using a mocked viewer seam. | The first node now asserts no job is selected, triggers refresh, and checks the visible loaded-status label. The second node triggers the real wx button action without selecting a job and asserts the `lssrv` result reaches the viewer seam. It is now named `test_raw_server_status_action_dispatches_raw_result`; its former nodeid was retired because the assertion and setup changed. The seam assertion does not claim that a raw-viewer window was visually rendered. |
| D4 — Optional schema sections | `TestSchemaV4Audit::test_v4_optional_sections_ok` previously supplied only the minimal required profile and duplicated the minimal-schema case. | The same node now supplies `job_details`, `accounting`, and `cluster_status` sections. `test_v4_valid` remains the minimal-profile owner. |
| D5 — Files translation keys | `TestFilesBehavior::test_context_menu_labels_localized` and `TestWave80Audit::test_files_context_menu_localized` asserted the same English/Turkish catalog values; neither interacted with a visible menu. | Kept the single `TestFilesBehavior` catalog-contract owner and removed the duplicate Wave80 node. These checks are not GUI localization evidence. |
| D6 — Outputs translation keys | `TestOutputsBehavior::test_standard_output_localized` and `TestWave80Audit::test_outputs_standard_output_error_localized` asserted the same output/error catalog values; neither inspected a visible control. | Kept the single `TestOutputsBehavior` catalog-contract owner and removed the duplicate Wave80 node. These checks are not GUI localization evidence. |
| D7 — Typed-password precedence | `tests/test_wx_connection_71_2.py::test_typed_password_precedence` and `tests/test_wx_connection_71_3.py::test_typed_password_precedence` repeated the service precedence assertion. | Added `tests/test_connection_profile_service.py::ConnectionProfileServiceTests::test_typed_password_precedes_saved_secret`, which asserts the typed value wins without prompting for the saved secret. Kept `tests/test_wx_connection_hardening.py::test_typed_password_precedence` because it additionally covers SSH info, GUI connection, and storage invariants. |

## Exact node delta and validation

Relative to the Packet C inventory, three nodeids were added and eight removed. Two new owner nodes replace D2 and D7 assertions; the third is the rewritten D3 raw-status action node. D1, D5, and D6 each remove one duplicate. D3 retires its old raw-status nodeid; D4 changes assertions without changing its nodeid. No other nodeids changed.

Added:

```text
tests/test_connection_profile_service.py::ConnectionProfileServiceTests::test_typed_password_precedes_saved_secret
tests/test_ssh_files_byte_preservation.py::test_sftp_download_upload_roundtrip_preserves_arbitrary_bytes
tests/test_wave78_jobs_details.py::test_raw_server_status_action_dispatches_raw_result
```

Removed:

```text
tests/test_wave0_unicode_baseline.py::TestRiskClassification::test_p0_sftp_roundtrip_risks_documented
tests/test_wave1_unicode_core_policy.py::TestEncodingBoundaryJustification::test_files_ssh_utf8_justified
tests/test_wave1_unicode_core_policy.py::TestEncodingBoundaryJustification::test_ssh_client_decode_justified
tests/test_wave78_jobs_details.py::test_raw_server_status_opens
tests/test_wave80_files_outputs.py::TestWave80Audit::test_files_context_menu_localized
tests/test_wave80_files_outputs.py::TestWave80Audit::test_outputs_standard_output_error_localized
tests/test_wx_connection_71_2.py::test_typed_password_precedence
tests/test_wx_connection_71_3.py::test_typed_password_precedence
```

Every new owner passed alone. Each affected owner file passed: Wave0 42, Wave1 19, byte-preservation 1, Wave78 16, Wave79 73, Wave80 45, profile service 9, wx connection 71.2 6, wx connection 71.3 7, and connection hardening 20. No replacement test was deleted or weakened to obtain these results.

The taxonomy report collected 2,686 nodes with 2,670 zero-primary and zero multi-primary. The exact Packet C ratchet passed: zero-primary debt decreased by eight, no classified node lost its primary, every added node has exactly one primary, and no generic catch-all file was introduced. The eight retired nodeids had no references in `scripts/` or `.github/`; this document is the explicit behavior mapping. A source search also found the retained broader D7 owner, which has distinct assertions.

Translation catalog owners remain key-level contract evidence. Packet F must provide real visible Files/Outputs localization evidence before any GUI-localization claim is made.
