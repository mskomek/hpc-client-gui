# WAVE 11 — Remaining Large Modules

Status: **WAVE_COMPLETE** for the architecture and focused regression scope. The source snapshot was tested on the Ubuntu-Test and Windows11 VMs. The full Windows portable release run is still in progress and belongs to WAVE 12 acceptance.

## Source identity

- Wave start SHA: `4e5b698653538ceeadb7a2cd16ae593e942b18a4`.
- Integration Git HEAD for the VM snapshot: `b38d3633665ac1823a172d5b59017ce2c9203870`; WAVE 11 changes were present in the tested working-tree snapshot.
- VM snapshot fingerprint: `80a17499530c55331e684d984c9fe4971a9b534cb3ad5c2379195ef91329ad57` (canonical manifest file list and SHA-256 values).
- VM manifest SHA-256: `49c83e66f42317492d3d8705a2f84e0f971b1046e6a92545ee887f243c5da12e`.
- Architecture process used a VM-only synthetic Git commit `cfb7f9a4e299c23df12b4a3cf1a918605febdeff`; source identity is bound to the manifest fingerprint above, not that synthetic commit.
- Jobs source SHA: `713949fb752b90601e007812ebf2bd765da5ad52`; V2 source SHA: `c0c6d0e956c9283f0c05f25b799e1b1f57ecb240`.

## Changes

- Split remaining large application modules, including the main window, login widget, plugin manager, wx connection/editor/transfer workspace, FTP and directory facades, and related terminal/output modules.
- Split large regression tests and support code by feature while keeping assertions and release-runner discovery in place.
- Added 36 first-party application modules. Across WAVE 11, 163 Python paths were modified, added, moved, or removed.
- Reduced selected facades: `ui/main_window.py` 1,182→331 lines; `ui/widgets/login_widget.py` 1,573→392; `ui/dialogs/plugin_manager_dialog.py` 914→425; `wx_connection.py` 1,331→411; `wx_editor_view.py` 945→312; `wx_transfer_workspace.py` 910→205.
- Removed the completed LOC baseline and changed `.github/workflows/ci.yml` to run the shared architecture validator in `--mode full`, enforcing global size, dependency, public API, and cycle gates.
- No first-party Python file is over 500 physical lines. The inherited inventory decreased from 52 over-limit files at WAVE 00 to zero.

## VM verification

| Check | Result | Exit | Evidence |
|---|---|---:|---|
| Shared source architecture + project imports/API/cycles, full scan | PASS; 1,014 Python files; 0 over 500; 0 dependency errors; 0 cycles; 0 public API errors | 0 | `ARCHITECTURE_FINAL.json`, source identity above |
| Architecture gate regression tests | 7 passed | 0 | Ubuntu-Test r28 quality run |
| Ruff `check src scripts tests` | PASS | 0 | Ubuntu-Test r28 quality run |
| `compileall -q src/hpc_gui scripts tests` | PASS | 0 | Ubuntu-Test r28 quality run |
| i18n key/reference/hardcoded UI text checks | PASS | 0 | Ubuntu-Test r28 quality run |
| Windows wx/Qt/Jobs/Files focused batch | 114 passed | 0 | Windows11 r27 evidence; host/guest source hashes matched |
| Windows plugin manager UI regression | 12 passed | 0 | Windows11 r28 evidence; manifest SHA matched |
| Ubuntu portable release suite, offscreen | Main suite: 1,919 passed, 44 skipped, 58 deselected, 22 subtests passed. Combined with isolated partitions: 2,639 passed, 206 skipped, 61 deselected, 29 subtests passed; no assertion failures. Overall runner exit **5** because 101 wx-only isolated partitions skipped with `No module named 'wx'`. | 5 | `.tmp/ubuntu-r28-portable-offscreen.log`; classify `BLOCKED_ENVIRONMENT`, not PASS |
| Windows full portable release suite | In progress at report creation; outcome to be recorded in WAVE 12 | — | Windows11 interactive runner session |

The Ubuntu release runner's nonzero exit is an environment limitation, not a test pass: wxPython is unavailable on that VM. The full Windows run is being used for native wx coverage. Linux package/build acceptance and a source-matched Windows release artifact are not yet established.

## Merge checkpoint

WAVE 11 source commit: `0ece0ad8fb52f028e9acf23bdc792dc6fd266fc0`. Local `develop` was clean at `d91c84f1d784fd3391bf132a54134faef44e63c9`, verified as an ancestor, and fast-forwarded to `0ece0ad8fb52f028e9acf23bdc792dc6fd266fc0`. The user worktree `D:\Projeler\hpc-client-gui` remains unchanged; no remote branch was changed.
