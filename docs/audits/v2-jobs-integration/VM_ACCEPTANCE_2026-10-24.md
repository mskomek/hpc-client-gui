# VM Acceptance and Packaging Rerun — 2026-10-24

## Final audit-reference check — integration checkpoint 3935aa02

- The report checkpoint archive was verified on Kole Ubuntu-Test: SHA-256 `232fd6ae72dfb94749433890baec210366f8a9fad7e100dbdccca542c5a15dc8`.
- Python 3.14.9 / pytest 9.1.1 ran `tests/test_docs_references.py`: **2 passed**, exit **0**.
- Log: `.tmp/vm-verification/r17-docs/docs-references.log`, SHA-256 `471c77f65875e4c272e08d0f1104f654c2ee63bed8cefdd055594fbb60385d29`.

## Source identity

- Base commit: `48ac62334b398bbc95b4d14ca9ef23dc83c356f3`.
- Working-source overlay fingerprint: `bed040f2fc44fd4a8b00633e959218aff7f19550d76a50d86b31142fc2d21593`.
- The overlay manifest contains 15 file hashes. It was staged and verified on both VMs; the ignored scratch files and unrelated `uname` user files were not part of the source overlay.
- This is the exact source identity used for the Linux acceptance and package run, and for the active Windows acceptance run.

## Ubuntu-Test full acceptance

- Environment: Ubuntu 24.04.5 VM, Python 3.14.8, Xvfb, D-Bus session.
- Command: `timeout 7200s xvfb-run -a -s '-screen 0 2560x1600x24' dbus-run-session -- <venv314>/bin/python scripts/release_test_suite.py --scope acceptance`.
- Exit code: **1**. This is a failed acceptance run, not a pass.
- The captured per-command pytest summaries add up to 3,444 passed, 26 failed, 33 skipped, and 62 deselected. Native process crashes can truncate their final pytest summaries, so this is the count present in completed summaries, not a release-runner aggregate.
- Fourteen isolated child commands returned nonzero: `test_w21_terminal_lifecycle.py`; `test_wx_file003_final_stress_navigation_races.py`; `test_wx_file003_final_stress_transfer_races.py`; `test_wx_file_actions_behavior.py`; `test_wx_file_browser_tabs.py`; `test_wx_file_browser_tabs_remote_tabs.py`; `test_wx_packaged_smoke.py` (exit 5, all 17 tests deselected by the selected markers); `test_wx_plugin_menu_contracts.py`; `test_wx_remote_file_actions_behavior_navigation_clipboard.py`; `test_wx_shell_p0.py` (native exit -11); `test_wx_shell_p0_stress.py` (native exit -11); `test_wx_terminal_parity_evidence.py`; `test_wx_terminal_parity_evidence_input_resize.py`; and `test_wx_terminal_parity_evidence_lifecycle_evidence.py`.
- The `wx_plugin_menu_contracts` child did not inherit `DISPLAY`; the two shell children segfaulted in the wx/WebView/GTK path; several terminal parity children timed out waiting for WebView subprocess readiness. Other listed failures remain failures and are not counted as environment passes.
- Captured log: `.tmp/vm-verification/linux-acceptance-48ac623-overlay.log` (SHA-256 `9678cd64ad5d2070f3f4beb67f6cb90f84ce34f4d6bf2a457de8db9fea06eebb`).

### Ubuntu-Test focused wx/Xvfb reruns

- Corrected the child environment in `test_wx_plugin_menu_contracts.py` and replaced the WebView readiness helper's blocking `MainLoop()` with bounded event pumping. On the verified source files (`test_wx_plugin_menu_contracts.py` SHA-256 `f62589f97f786317f8c7e6729ef7e68b7fb915472cdfb802e50d8f2d24ea2e91`; `wx_webview_probe.py` SHA-256 `02b8a8864a48f6da93f954064d105e5313f8b9381d39178ccb2c636d091cfe07`), the focused reruns passed:
  - Plugin menu contracts: 3 passed.
  - Terminal parity: 4 passed.
  - Terminal input/resize: 3 passed.
  - Terminal lifecycle parity: 4 passed.
- Logs are retained in `.tmp/vm-verification/ubuntu-focused-wx/`; their SHA-256 values are respectively `a4622d1c0569bf9eca43a71d5c98c3c0c741cedb8a36540144cbe800c2d10d03`, `d92728b169d1c6c56cc7b9d30a7ec4449bf37512685cd3c2b6685c4e3fbfd0ec`, `6a9558a6a66ecd31f8749183ccab061cfb7d254dcb57a55684b60e584c3ca735`, and `a2d8306745bfadfb69b58ff337eccb5bc3539bec193b5b8a14d160708c984933`.
- The W21 reconnect test was changed to wait for native WebView readiness before running the same disconnect/reconnect assertions. On the verified file SHA-256 `4a3ea60050a5db1c51621e095b822903de003e3e9df72b8b6855812bfc885c12`, it still failed: 7 passed, 1 failed; the reconnect child exited `-11` during wx/WebKit teardown. Log SHA-256: `6d73fd289327101c2996f241179fb239bddfb49001954bd419d3a40483908fbb`.
- Re-ran both shell P0 files with `PYTHONFAULTHANDLER=1`. Each exited `139` (SIGSEGV), so neither is a pass. The traces locate one crash in wx `SafeYield` while a `wxTimer` event is delivered; the stress crash occurs in `_close()` while yielding after frame close, with a WebKit/JavaScriptCore stack. Logs: `.tmp/vm-verification/ubuntu-focused-wx/test_wx_shell_p0-faulthandler.log` (SHA-256 `53234f059435aa8611a2634bfb9d0fd258da98151d722b535a89c095e37eb643`) and `test_wx_shell_p0_stress-faulthandler.log` (SHA-256 `5eea33f1e3d77099d2dbfc11bd1b2ab3c96789e787be5c71b32662ecd41dde77`).
- Fixed the delayed terminal-mount lifecycle so shutdown cancels a pending wx timer and the callback checks its owning frame before creating WebView controls. The P0 test fixture now shuts down through the production `Close`/lifecycle path; the tray-only shell also defers its unrelated WebView. On these exact source hashes (`wx_shell_frame.py` `d66f5c881f62438b6716c1528c730ef61f016a7e7c29276e594f2221fbd1c7bc`, `wx_shell_terminal.py` `fc7d2d7d2062d4f06f78d611e4554f55040c52b4e96e7f775fe06f365ffaa81a`, `test_wx_shell_p0.py` `29fc7b16687bac03eb331b771143008bddff742d1d6a0780967df8772d5b9498`), Ubuntu-Test reruns passed: P0 **13 passed** in 21.08s; production close stress **1 passed** in 197.57s (includes repeated shell close cycles). Evidence logs are `.tmp/vm-verification/ubuntu-focused-wx/test_wx_shell_p0-close-fixture2.log` (SHA-256 `edee045ff01bf8065f816e596e9a80c850548803eae942807785a34f173cf6c4`) and `test_wx_shell_p0_stress-lifecycle-fix.log` (SHA-256 `050b8177df3b258bbbcaeef55640a09e5f897da73aeb97c0d29fbf47abd06e27`). Two earlier intermediate retries still segfaulted before reaching the production close path; they are retained on the VM and were not counted as passes.
- W21's remaining reconnect native crash was traced to headless wx's default GUI log target: WebKit shutdown attempted `wxLogGui::Flush`/`wxMessageBox` from cleanup. The subprocess fixture now uses `wx.LogStderr()` while retaining all reconnect, close, and identity assertions. On `test_w21_terminal_lifecycle.py` SHA-256 `3258f7aa8bac37978580aa22c0eb9fbb80abfa59c12b9a10522cef703b451a70`, the focused reconnect case passed, then the full file passed **8/8** in 8.68s. Full-file log: `.tmp/vm-verification/ubuntu-focused-wx/w21-full-stderr-log-target.log` (SHA-256 `d385313433933baf8ba90f5523564e2edab7ebac30b70f3d287d3647a388e54e`). The earlier faulthandler crash trace is retained at `w21-reconnect-faulthandler.log` (SHA-256 `87fe7bed49496dd210da3e396a3f31230230d0303fb6753acb5e922ce5862f1`).
- The repository's canonical `scripts/check_source_architecture.py --mode full` ran in Ubuntu-Test with the shared Agent Core validator at `/home/test/.tmp/hpc-client-gui-acceptance-c264/ac-core`: **PASS**, 1,020 Python files, 0 over 500 lines. JSON report SHA-256 `6efa94426b454c55116cc3e3d3d420e07a86c8577293ca9f0715b91fe42f94b5`; Markdown report SHA-256 `9d218e992e0bd0b3d95a4628b101e242887ee3afb7667a3beadf89c83ec389e7`.
- A refreshed full Ubuntu acceptance run is active on base `48ac62334b398bbc95b4d14ca9ef23dc83c356f3` plus the 23-file overlay manifest SHA-256 `9a7959f930269d75ab1e7749d3e87563862caa67160ea96fe8d156e0db2d974b`. The staged ZIP SHA-256 is `6121bcef0fe833e282a23e59d39a3e2617112fe8a2ab1cd6c20caa92a947c6b1`; the VM verified every manifest entry before starting `scripts/release_test_suite.py --scope acceptance`. Log and exit file are `.tmp/linux-full-acceptance-r3.log` and `.tmp/linux-full-acceptance-r3.exit` in the VM scratch checkout; no final result is recorded yet.
- Fixed the release runner's isolated packaged-smoke selector. The file has a `packaging` marker, so the previous shared `-m "not packaging and not artifact_dependent"` command collected zero tests and exited 5. The runner now executes this contract file without that filter while keeping it process-isolated. On `release_test_suite.py` SHA-256 `62e87dfc5c66a2e3dfe5906c5433f7721eddefa46cbfb47e3d6f3d96a45efa70` and `test_release_test_suite.py` SHA-256 `ecc0e2bdb088dec8831366b3d7f3e9c1b51b688208419c839f5d19dd131299ff`, Ubuntu-Test passed the command-builder suite **15 passed** and the packaged-smoke test file **17 passed**. Logs: `.tmp/vm-verification/ubuntu-release-runner/test_release_test_suite.log` (SHA-256 `7cd222654887f74669bdd642e9cfead62de78b88945ba88f02308e2c56ec8d86`) and `test_wx_packaged_smoke.log` (SHA-256 `0e6f932f9d0c0cb6623fde965f59e17942a40c97324b37562c3b8549f0419142`); both recorded exit code `0`.
- The host's system Python 3.12 has wxPython 4.2.1, but this repository requires Python 3.14 and wxPython 4.3.1; a probe under that unsupported system interpreter failed during setup because its Paramiko is too old. It is not accepted as validation or used to replace the supported VM run.

## Ubuntu-Test release packages

- Command: `python scripts/release_linux.py --version 1.5.9 --execute`, with the pinned AppImage tool and required AppImage extraction mode.
- Build exit code: **0**.
- Release output directory on the VM: `/home/test/.tmp/hpc-client-gui-acceptance-c264/linux-package-retry2-48ac623-overlay/dist/releases/v1.5.9`.
- All three SHA-256 sidecars verified with `sha256sum -c`.

| Artifact | Size | SHA-256 |
|---|---:|---|
| `hpc-client-gui-1.5.9-x86_64.AppImage` | 207,522,296 bytes | `5288f647b920cf0af021a1febd5e1fde55022627592befc5b8e40d3accdf6c81` |
| `hpc-client-gui_1.5.9_amd64.deb` | 152,906,066 bytes | `76c3c07e7590185846e8efbb8bfe65d9fa3a1b28cc2fe09b7f6a41d1038b600c` |
| `hpc-client-gui-1.5.9.flatpak` | 129,862,336 bytes | `055ab3dc8871c8d70b40c4c0553aa36f6fbc0c209eafe0c55d86f0e7ff313f53` |

- The extracted Debian launcher binary had no unresolved `ldd` dependencies. Its packaged application entrypoint returned exit 0 for `--help` under Xvfb/D-Bus.
- The AppImage runtime identified itself successfully; the bundled application returned exit 0 for `--help` under Xvfb/D-Bus with `APPIMAGE_EXTRACT_AND_RUN=1`.
- The Flatpak bundle was produced by `flatpak build-bundle` and its checksum sidecar passed. Installing it into a Flatpak runtime was not part of this rerun.
- Captured build log: `.tmp/vm-verification/linux-package-build-retry2-48ac623-overlay.log` (SHA-256 `04914d5f88a6a7156615c01e20fdf7ab437a11f72cd8bbf32ede6ca83ff2cdb0`).

## Windows11 acceptance and packaging

### Full acceptance

- The canonical `Invoke-Windows11Interactive.ps1` run completed on `test\home` with exact 15-file source overlay fingerprint `bed040f2fc44fd4a8b00633e959218aff7f19550d76a50d86b31142fc2d21593`.
- Run ID: `21f2a11f621849fe8fbdc9fb52a24396`; exit code **1**; `Timeout=false`; guest cleanup completed. Host and guest hashes matched for every additional source file (`SOURCE_HASH_MISMATCHES=0`).
- Completed child pytest summaries total 3,463 passed, 19 failed, 35 skipped, and 62 deselected. The full suite is **not a pass**.
- Eight child commands returned nonzero. The aggregate partition failed these five cases: `test_docs_references.py::test_referenced_local_files_exist`; `test_test_taxonomy_checker.py::test_report_mode_succeeds_with_taxonomy_debt`; and three `test_w14_provenance_manifest.py` cases (`test_manifest_contains_all_provenance_fields`, `test_provenance_captures_git_identity_and_toolchain`, `test_smoke_evidence_carries_identity_header`). In that VM run, `git ls-files` and `git rev-parse HEAD` returned exit 128 and the generated provenance identity was `unknown`.
- `test_wx_file003_final_stress_navigation_races.py` failed two cases; `test_wx_file003_final_stress_transfer_races.py` failed one (`AttributeError: 'int' object has no attribute 'SetSize'`). `test_wx_remote_file_actions_behavior_navigation_clipboard.py::test_wx_remote_ctrl_a_selects_all_rows` failed its selection assertion.
- The terminal groups failed four `test_wx_terminal_interaction.py` cases, one `test_wx_terminal_lifecycle_behavior.py` case, and five `test_wx_terminal_vt_behavior.py` cases. Their WebView child processes hit 60-second `subprocess.TimeoutExpired` exceptions. `test_wx_packaged_smoke.py` returned exit 5 with 17 tests deselected by the supplied marker expression.
- Captured stdout SHA-256: `d969f1c161f060e838ddf7e83df6e9eb112f30ef5c1a25d88588e2eac10dc239`; stderr SHA-256: `5afbdf7211f254fe421f8346ff99cb06ac1208e7af93bb4ddc9f16d586fb3721`.

### Windows package build

- The first release attempt, run ID `1691b0a61ff048519daac49cd84d1aa1`, exited 1 before producing an artifact. `scripts/check_release_consistency.ps1` searched `src/hpc_gui/cli/main.py`, while the current `CLI_VERSION` declaration is in `src/hpc_gui/cli/_contracts.py`.
- Fixed that source path in `scripts/check_release_consistency.ps1`; the local PowerShell consistency gate then passed for version `1.5.9`.
- The successful canonical retry is run `e4c07716b02c4503bd172c4db25091f4`, on `test\home`, with base `48ac62334b398bbc95b4d14ca9ef23dc83c356f3` plus 17 hashed overlay files, fingerprint `2b0a854455ef2b1ca9bcf703e6da15c5b666cc717fee1a1c83d6867ee8a371c7`. It exited 0, did not time out, completed cleanup, and had zero host/guest source-file hash mismatches. Packaged executable SHA-256 matched on host and guest: `15cd209c995b7d3009c91ca40892d5b8f1fb162f3e5f10716642ea278e8e0d7b`.
- Windows release gates passed: release consistency for `1.5.9`, GUI/CLI executable smoke, CLI guide coverage, and local mocked transfer smoke. The ZIP contains 159 entries; required GUI/CLI/help entries were verified. Artifact `hpc-client-gui_windows_onedir.zip`: 36,739,587 bytes, SHA-256 `14ce13806001f89c3ce225b8168fafadf2dc875bfe2bcfaf82fafd2779ef8228`; `WINDOWS_RELEASE_SMOKE=PASS`. Captured stdout SHA-256 `8e6122bd3164881fe3348e9251ee58fe3db0eb46232921d3a1957643d4392282`; stderr SHA-256 `0d81773abb608da6f58930423e3ff3dee69d9a7ae0da13fe9e7b6015b23da431`.
## Historical checkpoint verdict — before r17 final reruns

At this checkpoint the verdict was `INTEGRATION_CODE_COMPLETE_ACCEPTANCE_BLOCKED`: the Ubuntu and Windows full acceptance runs still had failures. That status describes the earlier source/test state only and is superseded by the later r17 full acceptance results below. Hosted CI has not run. No push, PR, release publication, or commit was created.

## Latest continuation — 2026-10-24

### Updated focused validation

- The refreshed Ubuntu full acceptance run linux-full-acceptance-r3 remains in progress on the 23-file overlay fingerprint 9a7959f930269d75ab1e7749d3e87563862caa67160ea96fe8d156e0db2d974b. During that run, a separate focused Xvfb process ran briefly on the same Ubuntu VM; treat the full run as diagnostic only, not a clean acceptance result.
- The diagnostic R3 run exposed positional _settle(wx_app, rounds) calls after _settle gained its window parameter. Updated the navigation-race and transfer-race test calls to use the named rounds= argument; all loop counts and assertions remain intact. On the updated two-file copy, Ubuntu-Test passed 3 tests in 304.86s, exit 0. Log SHA-256 d14afad654d9b432e1474e52e965d39e772bd03151a0e7ab5e9910622b13c9ab; exit-file SHA-256 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa.
- R3 also failed one local right-click selection test because its wx frame was not sized before it synthesized screen coordinates. Resized and laid out the local and remote file-action test frames before event dispatch; these changes only stabilize the tested GUI geometry. Focused reruns for these two action modules are pending.
- Re-ran the repository architecture validator on the updated R4 source copy: PASS, 1,020 Python files, 0 over 500 lines, exit 0. Log SHA-256 23f1d2a4c9e6abdb9699d306211c472a677c60763ebc3304c9da7c8b9b10c705.
- The Qt LGPL source URL verifier failed intermittently during two Windows package starts although the same URLs returned HTTP 200 from the guest PowerShell probe. Added bounded retries for transient URL errors and regression coverage; permanent HTTP errors still fail immediately and a URL must still be verified. Ubuntu-Test passed tests/test_qt_lgpl_sources.py: 3 passed, Ruff and compileall passed. The compact focused test copy emitted two unregistered-marker warnings because it did not include the repository pytest configuration. Test log SHA-256 1234811f6b574282d2e0761a8fcc4baa815518c729589574ee32d18e3756f65e; Ruff log SHA-256 82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18.

### Windows11 focused GUI and package reruns

- Focused W21 plus shell P0 run ID 95fa8265a0144e708d812d8625165832 used base 48ac62334b398bbc95b4d14ca9ef23dc83c356f3 and overlay fingerprint 9d13de1710dbac47839f56f80eb6da47f3fe59811968370f99e4840597b443c3; host/guest stage hashes matched and cleanup completed. Result: 20 passed, 1 failed, exit 1. The W21 reconnect test still reports WebView2 did not become ready before reconnect (0x80004004, Operation aborted). Stdout SHA-256 e39c5f4f7b1f7122743fa5e0b1b5d7e79ef776f47804bb42a95954165209d65e; result SHA-256 b3b20d5a53dbd1b2146cfd10c38f4965ebf33e7ceb743d8d53fd8492b3d5fd98.
- The final Windows package run ID fbf53c304a9e4553a813608320a13375 used test\home, active Explorer session 2, base 48ac62334b398bbc95b4d14ca9ef23dc83c356f3, and source overlay fingerprint 32d23d01a03de15f66426df74f938dabbbc4524d0c8b2152155e1fcf1188a2e0. It exited 0, did not time out, and cleanup completed. The guest ran the Qt source verifier tests (3 passed), built the GUI and CLI with PyInstaller, passed packaged EXE/CLI smoke, documented all 36 CLI command paths, passed the local mocked transfer gate, and verified the ZIP checksum and all required members.
- Verified Windows package: hpc-client-gui_windows_onedir.zip, 36,740,109 bytes, SHA-256 6ef6708ea3d3adea28621670ab73a0ef8ff41b7aaa470b807d7b31bbd4558979, 159 members. Source identity JSON SHA-256 1fceee6caae5c66d9c28181b53f71bd7a10b7d54d0140693d728042ea1eac1dc. The canonical runner cleaned its guest staging directory after returning the verified hashes, so the ZIP is not retained in the guest.
- Windows package stdout SHA-256 3f68b9ff46347d5a196659f909292639445867b7e8a865ec89c51f5bc3b2fd1f; stderr SHA-256 02b5e02dcaeb8a51a6cde0ec5967bc1aff8a22de96c05cf743a5def66b08c233; runner result SHA-256 ad3a3e5587184f1a1290ca858a351dc6c3f69ccfe710ea99c49fd6e7464041d5.

### Pending

- The earlier Windows full acceptance remains failed (3,455 passed, 27 failed, 35 skipped, 62 deselected); the latest W21 focused failure confirms at least one Windows GUI blocker remains.
- The Linux R3 full acceptance is diagnostic and still running in its isolated snapshot. A clean full Ubuntu acceptance run on the updated source, the focused local/remote file-action reruns, a current-source Linux package build, and any necessary preserved-artifact step remain outstanding.
- No hosted CI run, push, PR, or release publication occurred.

### 2026-10-24 r16/r17 continuation checkpoint

- r16 source: base `48ac62334b398bbc95b4d14ca9ef23dc83c356f3`, 37-file overlay fingerprint `ef541f0872c0fad708d0a6345e25b92df8d7c61e14c535dd1d07639a82c68e58`, ZIP SHA-256 `a3d197b59c41946a627f0d5c298bbd61d77d68358d5a8f29a760d3b2d3ac9899`.
- Kole Ubuntu, Python 3.14.9: `scripts/ci.py release` exit 0; 3,506 passed, 0 failed, 33 skipped, 46 deselected across 244 pytest subprocess commands. The full acceptance log SHA-256 is `fefb70e9817b803c657ac441d26e643b2b5928dd11198486899dbc325536f82b`. The focused notebook and layout tests passed 3/3. Architecture full check passed: 1,020 Python files, 0 over 500 lines, 0 new dependency errors, 0 API errors, and 0 cycles. Evidence is retained in `.tmp/vm-verification/r16-linux/`.
- r16 Ruff initially could not start because `ruff` was absent from the Python 3.14.9 environment. After installing the declared dev dependency (`ruff 0.17.2`), Ruff identified one duplicate local function (`F811`) in `wx_remote_files_interactions.py`; this was removed in r17 without changing behavior.
- Kole Windows11-New, Python 3.14.7: r16 architecture passed at 1,020 Python files and 0 over 500 lines; focused notebook/layout tests passed 3/3 in 178.80s. The full acceptance process is still running at this checkpoint. Its isolated `test_w19_connection_gui.py` child has failed with Windows native exception exit `3221226525` (`0xC000041D`) during wx teardown; this is recorded as a failure, not a pass.
- r17 is a new 39-file source overlay fingerprint `325593c807cab38278a93b45986f38ac3152c426421084780bc06ef99c201765`, archive SHA-256 `aafce9d620856696318fd7f7438449f6c2b0cd552d35aa147c7662038fbfb986`. It removes the duplicate local function and avoids pumping wx events while W19 WebView controls are tearing down. Kole Ubuntu r17 Ruff passed with exit 0; full architecture passed with 1,020 Python files, 0 over 500 lines, 0 dependency/API errors, and 0 cycles. `scripts/ci.py release` passed on Python 3.14.9 with 3,506 passed, 0 failed, 33 skipped, and 46 deselected across 244 pytest subprocess commands; log SHA-256 `932cbc9920c5fb6463813fc9ae6b706fa8b4a6e75c808c40d30eb34b19535ae4`. Portable coverage validation is running. Windows r17 is staged separately; its focused and full tests have not started yet.

## r17 Windows acceptance and package checkpoint — 2026-10-24

- Source overlay: 39 files; fingerprint `325593c807cab38278a93b45986f38ac3152c426421084780bc06ef99c201765`; base commit `48ac62334b398bbc95b4d14ca9ef23dc83c356f3`.
- Windows11-New, Python `3.14.7`: source architecture full check and Ruff 0.17.2 passed. Architecture report: 1,020 Python files, 0 files over 500 lines, 0 dependency/API errors, 0 cycles.
- Focused W19 connection GUI: 8 passed, exit 0. wx notebook/layout resize: 3 passed in 181.48 seconds, exit 0.
- Full Windows release acceptance: exit 0; 3,504 passed plus 29 subtests passed, 0 failed, 35 skipped, 46 deselected across 239 pytest summary lines. W19 native exit `0xC000041D` did not recur. wx emitted non-fatal `UnregisterClass` / “No application object” shutdown messages; preserved in stderr for follow-up. Captured stdout SHA-256 `76b5b976a75d6bfd21aad9ff2c3a160503989a7a604b86107b4605e304f05772`; stderr SHA-256 `d5ca8654aeec66ff86b1568d6f81f60f452bccf6cd336960edd4a572f7740fd4`; exit file SHA-256 `a635af4604117d679ee577631c35cd5290b83ee2b673ec44077b86685ed00035`.
- Windows package build used the same source fingerprint and Python `3.14.7` in a separate clean build clone. Release workflow, consistency, PyInstaller GUI/CLI builds, packaged EXE/CLI smoke, 36-command CLI guide coverage, and local mocked transfer gate passed; build exit 0.
- Windows ZIP: `hpc-client-gui_windows_onedir.zip`, 36,453,374 bytes, SHA-256 `cd1de871ca0d2c53220e39329f3b65e7008d342a06817e5b4bbf85d50218503a`, 158 members. The guest manifest and sidecar matched the locally copied ZIP; required GUI/CLI/help/sftp-smoke members were verified. Package stdout SHA-256 `4a21dca34c5b9334b79680f6e7d3797276b75e257e6e0dee305c520a833ad4e7`; stderr SHA-256 `ddb001222804efc64084bae257ea64f10a64c28c61850fba0924da954756c42e`; manifest SHA-256 `0a5500747942e93375c17b0a0c6c581089559320a73ac778284eeafc7b6f9cd5`.
- Windows evidence is retained under `.tmp/vm-verification/r17-windows/` and `.tmp/vm-verification/r17-windows-package/`.
- Ubuntu r17 portable Xvfb/D-Bus coverage and current-source Linux package build completed successfully; detailed exit codes, counts, hashes, and warnings are recorded in the r17 coverage and Linux package sections. Earlier “active/pending” notes in this checkpoint were superseded by those results.
- No commit, push, PR, or release publication was performed.

## r17 Ubuntu Linux package build and installed-launcher smoke — final update

- Test VM: Kole Ubuntu-Test. Package build and launcher smoke used the existing Python **3.14.9** interpreter from the VM's uv-managed Python installation; the generated release manifest records `python: 3.14.9`. The VM's system `/usr/bin/python3` is 3.12.3 and was not used for this acceptance run.
- Source commit: `48ac62334b398bbc95b4d14ca9ef23dc83c356f3`; source fingerprint: `325593c807cab38278a93b45986f38ac3152c426421084780bc06ef99c201765`.
- `python scripts/release_linux.py --version 1.5.9 --execute`: exit **0**. The build log is `.tmp/vm-verification/r17-linux-package/linux-package-build-r17.log`, SHA-256 `72a91df733a664379f59a891738eb57a84aa1d290d523920b42aef47ac5d6c8e`. Artifact manifest SHA-256: `281a7c12ecf65a8291fbf690c72aec8905ceaa1cbe1a3ccfafde2c7b5c061e25`.

| Artifact | Size | SHA-256 |
|---|---:|---|
| `hpc-client-gui-1.5.9-x86_64.AppImage` | 198,928,888 bytes | `dd4ac4d7c460744d085593717cd09d5cd532a8e5b09b1780c44922be9827e75f` |
| `hpc-client-gui_1.5.9_amd64.deb` | 144,702,340 bytes | `d9df05ce86b49246b2aecf54dc13d927c35db7ff96632c6ee904ce31dc1bce1b` |
| `hpc-client-gui-1.5.9.flatpak` | 122,532,624 bytes | `2f51e5812acab18ee3df5205b3da539a468d71f95b7e3121d02d827c1b1bd1d3` |

- All three artifact SHA-256 sidecars matched. Debian payload `ldd` check had no unresolved libraries. The installed Debian launcher, AppImage launcher, and installed Flatpak launcher each returned exit **0** for `--help` under Xvfb/D-Bus. Flatpak install/run/uninstall completed; afterward both the Debian package and Flatpak application were absent from the VM.
- Flatpak emitted non-fatal document-portal/FUSE permission messages (`/run/user/1000/doc`); the application printed its full CLI help and returned 0. The warning remains visible in `.tmp/vm-verification/r17-linux-package/flatpak-launch-r17.log` (SHA-256 `e2005ed9219dd35b18b68a53c3ed0b285dbe200d04f63be853ee13ac3ee96cde`). The standalone Flatpak help output SHA-256 is `57e3aad96121613ac749b5bd82d07bb16c4295bd710ab60e3f6e9771257fb0a0`.
- Debian dependency log SHA-256: `874814db316bc693b614e3be012417ff2b44df8bd6b8c6071b4864f968c3b848`. Debian launcher output SHA-256: `2ecb086228b0a4a7dac33ee1c05a5decab92401d0e68b9558d05f3bdb4fc2cb6`. AppImage launcher output has the same SHA-256 because both printed the identical CLI help.
- Two early helper attempts stopped before a valid Flatpak launch: one ran sidecar verification from the wrong current directory; another overrode `XDG_DATA_HOME` and thereby changed Flatpak's user installation lookup path. Both harness issues were corrected, their outputs were retained, and the final launch was rerun with the correct Flatpak installation context. They are not counted as package failures or passes.
- Package build log, manifest, checksum sidecars, dependency output, launcher outputs, and final Flatpak install/run/uninstall log are retained in `.tmp/vm-verification/r17-linux-package/`. The 445 MB of package files remain on the isolated test VM; their byte sizes and hashes are recorded above and in the manifest.
- Final VM cleanup probe: Debian package absent; Flatpak app absent. No HPC connection or remote file/job operation was used. No commit, push, PR, or release publication was performed.

## r17 Ubuntu Xvfb/D-Bus coverage checkpoint — 2026-10-24

- Kole Ubuntu-Test, Python `3.14.9`; source commit `48ac62334b398bbc95b4d14ca9ef23dc83c356f3`, 39-file source fingerprint `325593c807cab38278a93b45986f38ac3152c426421084780bc06ef99c201765`.
- `xvfb-run` + `dbus-run-session` `scripts/ci.py gui` completed with exit 0 after 234 pytest subprocesses: 3,477 passed plus 29 subtests passed, 0 failed, 33 skipped, 46 deselected. Portable preflight gates passed.
- Coverage: total `69.56%` against the required 65%; all configured module coverage floors passed. Coverage outputs are retained under `.tmp/vm-verification/r17-linux-package/`.
- Captured GUI coverage log SHA-256 `087ccc05e2e0f4c4f0fde73ab01c7b2ef466c9aa73652ed5ef0cb99c2c488168`; `coverage.json` SHA-256 `49dec298a8dcc4c0bd84951741f955f0c7afc008be6a0c51356d4fa90bc3c25f`; `coverage.xml` SHA-256 `714dc690425f0b68c9e4625fd9cc8770601354cb7fa7e9c5518c61d416d5317e`.
- The coverage run emitted Python 3.14 `ResourceWarning` messages for unclosed SQLite connections (200 occurrences in the combined multi-process log; no test failures) and one trailing D-Bus connection message after all portable and coverage gates had passed. The wrapper's captured exit file is `EXIT_CODE=0`; these warnings are retained, not treated as a pass/fail substitution.
- Linux package build attempt 1 stopped before `release_linux.py` ran because the dedicated build clone lacked its ignored `.tmp/` log directory; this was harness setup, not a product build. Attempt 2 subsequently completed with exit 0 on the same source fingerprint and Python 3.14.9, and installed launcher smokes passed for Debian, AppImage, and Flatpak as documented in the final update above.

## r17 final VM validation summary

- Linux VM: Python `3.14.9`; full `scripts/ci.py release` exit 0 with 3,506 passed, 33 skipped, and 46 deselected. Xvfb/D-Bus GUI coverage exit 0 at 69.56%, above the 65% floor. Architecture full check: 1,020 Python files, 0 above 500 lines, 0 dependency/API errors, 0 cycles. AppImage, Debian, and Flatpak build and installed `--help` smoke checks passed.
- Windows11-New VM: Python `3.14.7`; full release acceptance exit 0 with 3,504 passed plus 29 subtests, 35 skipped, and 46 deselected. Windows GUI/CLI package build and smoke checks passed.
- Python 3.14 was present and used on both VMs. Ubuntu's `/usr/bin/python3` is 3.12.3, but it was not used for these validations; the Python 3.14.9 uv-managed interpreter was used and is recorded in the release manifest.
- Non-fatal warnings retained: Ubuntu coverage emitted SQLite `ResourceWarning`s and a trailing D-Bus message; the Flatpak document portal reported a FUSE permission warning while the launcher still returned 0. Windows wx teardown emitted `UnregisterClass` / “No application object” messages despite the suite exit 0.
- Hosted GitHub Actions were not run. These VM results do not claim a hosted CI result. No commit, push, PR, or release publication was performed.
