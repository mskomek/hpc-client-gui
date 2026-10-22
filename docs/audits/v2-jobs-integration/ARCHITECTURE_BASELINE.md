# Architecture Baseline

Baseline source commit: `f61919bad12be5f328cb9db3fee3c8de8563fa5b` (the clean local `develop` head at task start). The full source report, hashes, and counts are preserved in [ARCHITECTURE_BASELINE.json](ARCHITECTURE_BASELINE.json). The transitional LOC baseline was removed after WAVE 11 reached the zero-violation architecture gate.

The shared Agent Core validator at `mskomek/.agents-core` commit `2dfa726973194305f63b62477a286037f5c0642d` was run in `project` scope. It reported **803 source files, 60 files in the 400–500 warning range, and 52 files over 500 physical lines**. Its exit code was 1 because the 52 existing violations are the staged baseline. The independent project dependency scan found **2 unresolved internal symbol imports** and **8 existing import-cycle groups**.

The transition gate runs the shared validator in `changed` scope against the previous successful commit. Every added or modified source file must be at or below 500 lines; untouched baseline debt is inventoried and cannot increase through a changed file. The project checks also reject new unresolved internal imports, new cycles, and missing facade exports. Final mode uses the shared validator in `project` scope and requires zero over-limit files, zero dependency errors, zero API errors, and zero cycles. The LOC baseline will be removed when final mode passes.

## Existing files over 500 lines

| LOC | File |
|---:|---|
| 6251 | `tests/test_ftp_widget.py` |
| 4601 | `src/hpc_gui/ui/widgets/remote_dir_panel.py` |
| 3216 | `src/hpc_gui/wx_jobs.py` |
| 1892 | `src/hpc_gui/ui/widgets/jobs_outputs_widget.py` |
| 1781 | `src/hpc_gui/ui/widgets/ftp_widget.py` |
| 1710 | `src/hpc_gui/ui/widgets/login_widget.py` |
| 1489 | `tests/test_wx_file003_final_stress.py` |
| 1437 | `src/hpc_gui/wx_connection.py` |
| 1277 | `src/hpc_gui/ui/main_window.py` |
| 1213 | `src/hpc_gui/wx_updater_view.py` |
| 1192 | `tests/test_plugin_manager_ui.py` |
| 1175 | `tests/test_wx_connection_profiles.py` |
| 1165 | `src/hpc_gui/ui/widgets/local_dir_panel.py` |
| 1031 | `src/hpc_gui/ui/dialogs/connection_dialog.py` |
| 1028 | `src/hpc_gui/ui/dialogs/plugin_manager_dialog.py` |
| 1025 | `tests/test_wave2_directories_local_files.py` |
| 1023 | `src/hpc_gui/cli/main.py` |
| 1005 | `src/hpc_gui/wx_editor_view.py` |
| 992 | `tests/test_wx_connection_hardening.py` |
| 987 | `src/hpc_gui/wx_transfer_workspace.py` |
| 852 | `tests/test_plugin_installer.py` |
| 832 | `src/hpc_gui/config/storage.py` |
| 805 | `src/hpc_gui/ui/dialogs/transfer_dialog.py` |
| 702 | `src/hpc_gui/plugins/validator.py` |
| 698 | `src/hpc_gui/plugins/ui_contributions.py` |
| 684 | `tests/test_wx_updater_spec.py` |
| 673 | `tests/test_wx_jobs_files_outputs.py` |
| 673 | `tests/test_ssh_credential_flow.py` |
| 664 | `src/hpc_gui/services/app_updater.py` |
| 662 | `tests/test_wx_connection_71_3.py` |
| 661 | `tests/test_wx_file_browser_tabs.py` |
| 660 | `tests/test_wx_connection_71_4.py` |
| 649 | `tests/test_wx_connection_71_5.py` |
| 609 | `tests/test_wave80_files_outputs.py` |
| 606 | `tests/test_jobs_outputs_scroll.py` |
| 592 | `tests/test_wave79_provider_contract.py` |
| 580 | `tests/test_wx_terminal_parity_evidence.py` |
| 580 | `src/hpc_gui/wx_plugins_view.py` |
| 555 | `tests/test_wx_remote_file_actions_behavior.py` |
| 550 | `tests/test_w33_lifecycle_isolation.py` |
| 542 | `tests/test_wave0_unicode_baseline.py` |
| 541 | `tests/test_luna_fm_integration.py` |
| 540 | `tests/test_wx_65a_stress.py` |
| 538 | `tests/test_ssh_jump_host.py` |
| 536 | `tests/test_synchronized_browsing.py` |
| 529 | `src/hpc_gui/ui/dialogs/settings_dialog.py` |
| 528 | `tests/test_wave79_audit.py` |
| 523 | `tests/test_wx_file_transfer_integration.py` |
| 519 | `tests/test_wx_connection_71_2.py` |
| 512 | `tests/test_plugin_contract.py` |
| 512 | `tests/test_corrective_jobs_details.py` |
| 508 | `scripts/ftp_transfer_stress.py` |

The two starting dependency findings are `tests/test_ssh_jump_host.py` importing `_KnownHostsPolicy` from `hpc_gui.ssh.client` (the symbol is currently defined in `hpc_gui.ssh.host_keys`) and the stale `scripts/capture_current_gui_qt.py` import of `AnsysLintResultsDialog` (the module exposes builder functions). The first will be checked in the SSH wave; the screenshot script will be aligned with the dialog API in the dialog wave.

The existing `docs/architecture/source-loc-exceptions.json` contains a stale `wx_jobs.py` count (3,122 versus the measured 3,216). It does not authorize retaining that file above the limit and will be reconciled during Jobs modularization.
