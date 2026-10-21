# WAVE 07 — Plugin system

Status: **WAVE_COMPLETE** on the isolated integration branch. Local `develop` and remotes were not changed.

## Source identity and selection

- Wave start: `3efd890b5deb1ccf36e423d3000fa1b75f1481d0`.
- Source commit: `ce598c2859b31d0abdfaaf6c071a6898eec60782`; tree `418427c15e5c10de085df3b47f7137e4fc057310`.
- V2 source: `c0c6d0e956c9283f0c05f25b799e1b1f57ecb240`. Jobs source `713949fb752b90601e007812ebf2bd765da5ad52` has no plugin source changes for this wave.
- Changed files: 19 Python files, including 6 new application modules and 3 test support modules. Source fingerprint over sorted `path + NUL + SHA256(committed blob bytes) + newline` records: `9be467bfb2e843e32bfd9fa04f9ede5cbe7111e024a5a81c2dea798ce5d7347f`.

The validator was split into manifest, profile, registry, and contract modules. Plugin menu contributions were split into shared model/validation helpers and a parser. The two public facades keep their prior symbols. V2's validator facade did not re-export several existing names, so the legacy constants, type helpers, compatibility functions, and trusted-tool helper were restored. Static facade comparison found no missing prior symbols; runtime `__all__` checks found no missing exports.

V2 also split installer, plugin-manager UI, and plugin contract tests. AST comparison found all 39 installer, 37 manager UI, and 20 contract test function bodies unchanged and present exactly once across the selected split files. Assertions were not altered. The 852-line installer, 1192-line manager UI, and 512-line contract test modules are now below 500 lines.

Dirty V2 snapshot review found separate `plugin_manager_dialog.py`, `plugin_manager_cards.py`, and `plugin_manager_state.py` UI work. Those files were not selected here; they remain preserved for the later dialog/UI wave. The V2 snapshot aggregate fingerprint remains `889fb7432500705ff44281ad2c76407d5ec334de17f2ab777128e33ad0d4980b` and the snapshot was not modified.

## Physical line counts

| Python file | Start | End |
|---|---:|---:|
| `src/hpc_gui/plugins/validator.py` | 702 | 103 |
| `src/hpc_gui/plugins/ui_contributions.py` | 698 | 234 |
| `tests/test_plugin_contract.py` | 512 | 322 |
| `tests/test_plugin_installer.py` | 852 | 169 |
| `tests/test_plugin_manager_ui.py` | 1192 | 329 |

New modules: `_manifest_validation.py` 254, `_profile_validation.py` 215, `_registry_validation.py` 80, `_validator_contracts.py` 150, `_ui_contribution_parser.py` 295, `_ui_contribution_shared.py` 210 lines. All 19 changed Python files are at or below 500 lines. No exception was added.

## Verification on source commit `ce598c28`

| Check | Result | Exit | Evidence |
|---|---|---:|---|
| Plugin, installer, menu, schema, and security batch without external checkout setting | 450 passed, 0 failed, 40 skipped | 0 | `.tmp/wave07-plugin-tests-final.log` |
| Same broad batch with local plugin contract checkout | 479 passed, 1 timeout, 10 skipped | 1 | `.tmp/wave07-plugin-tests-with-contract-checkout.log` |
| Cross-repository plugin contract tests with `HPC_GUI_CONTRACT_REPO` set to the local checkout | 30 passed, 0 failed, 0 skipped | 0 | `.tmp/wave07-plugin-cross-repo-contracts.log` |
| Fluent integration tests against the local checkout | 9 passed, 0 failed, 0 skipped | 0 | `.tmp/wave07-fluent-integration-final.log` |
| wx menu lifecycle timeout diagnosis | `test_wx_separator_lifecycle_offscreen` passed in the first broad batch and on isolated rerun (13.32 seconds); assertions and its 15-second timeout were unchanged | 0 on rerun | `.tmp/wave07-wx-menu-timeout-rerun.log` |
| Ruff and compileall over all changed Python files | passed | 0 | committed-source command output |
| Facade public API comparison | no missing legacy symbols; no `__all__` runtime names missing | 0 | committed-source command output |
| Changed-source architecture gate, base `3efd890b` | PASS; 853 Python files scanned; 42 inherited over-limit files remain; no new dependency/cycle/API errors | 0 | `.tmp/wave07-architecture-final.json` and `.md` |

The single failure in the contract-enabled broad run was a native wx subprocess exceeding its existing 15-second ceiling during the Unicode/hide-disable lifecycle loop. The same test passed in the earlier broad run and isolated rerun; this was classified as a load-sensitive GUI timeout, not a product assertion failure. The external checkout at `D:\Projeler\hpc-client-gui-plugins` was read-only for these tests; its pre-existing untracked `.github/social-preview.jpg` remains untouched. Nine Fluent tests were run by a temporary pytest hook that pointed their existing local fixture to this checkout and removed only the already-evaluated missing-sibling skip marker; no test source or assertions changed. One POSIX permission test remains skipped on Windows.

The architecture gate reduced the global over-limit count from 47 to 42. One inherited unresolved internal import and eight inherited dependency cycles remain from the baseline. No remote installation or plugin registry network access was used.

## Integration state

WAVE 07 is committed on `codex/integration/v2-jobs-staged-20261021` only. The branch includes current `develop` through sync merge `1995d7f5cb28de5cdf34737f95202e9d4fb7af9b`. Local `develop` and `origin/develop` remain at `d91c84f1d784fd3391bf132a54134faef44e63c9`. The V2 snapshot and original Jobs/V2 branches remain unchanged. Full release acceptance, Windows11 guest acceptance, Ubuntu/Linux package acceptance, and GitHub Actions were not run.
