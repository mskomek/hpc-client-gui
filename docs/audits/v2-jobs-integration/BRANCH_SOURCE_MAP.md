# Branch Source Map

## Verified heads

| Ref | Commit | Advertised remote head | Worktree state |
|---|---|---|---|
| local `develop` | `f61919bad12be5f328cb9db3fee3c8de8563fa5b` | `origin/develop` = `b2de2bb8ccc533aa0b0ecb7dd2a798a4fcdf709a` | clean; checked out in `D:\Projeler\hpc-client-gui-i18n-develop` |
| Jobs | `713949fb752b90601e007812ebf2bd765da5ad52` | same | clean; `C:\Users\mskomek\.codex\worktrees\jobs-workspace-recovery-merge` |
| V2 | `c0c6d0e956c9283f0c05f25b799e1b1f57ecb240` | same | 99 modified tracked, 74 untracked, 32 ignored entries |
| integration | `codex/integration/v2-jobs-staged-20261021` at `71ef960bb486cc821e1a79f969e5b58913841715` | local only | isolated worktree; no remote branch |

Live `git ls-remote` confirmed the three advertised GitHub heads above on 2026-10-21. The supplied starting SHAs still match Jobs and V2. The supplied `develop` SHA is the remote-tracking head; local `develop` has one additional committed change.

## History and divergence

Merge bases:

- `develop` ↔ Jobs: `b2de2bb8ccc533aa0b0ecb7dd2a798a4fcdf709a`
- `develop` ↔ V2: `42c8b471cf24c047c2f7f58047a5177bfd158a20`
- Jobs ↔ V2: `42c8b471cf24c047c2f7f58047a5177bfd158a20`

Commit divergence (`left-only / right-only`): `develop...Jobs` = `1 / 23`, `develop...V2` = `11 / 5`, `Jobs...V2` = `33 / 5`. V2 is not a direct continuation of Jobs.

Jobs changes 111 files against its merge base (`+9,480/-6,582`). V2 changes 232 files against its merge base (`+38,382/-25,945`). Their comparison has 21 same-path overlaps. Key overlaps include release runner selection, CLI/config/plugin facades, connection profile service, Qt outputs, splash, FTP tests, and wx connection/terminal tests.

Jobs commits after its develop merge base, in order:

`72359f27`, `32aae234`, `7051a62c`, `2de6fc06`, `cd780e09`, `a043d8d5`, `f119e2e7`, `72c1152c`, `4f1179d3`, `8a27b784`, `596f8603`, `ed1d1613`, `f96ec99d`, `76520aa2`, `90876b1a`, `abb214c7`, `8d23613d`, `a091e14c`, `753db9f6`, `a7c2d58f`, `2964c0cd`, `5d908ebc`, `713949fb`.

V2 commits after its common base, in order:

`c4d4be9c`, `79fec477`, `e6440fbb`, `24b41444`, `c0c6d0e9`.

## WAVE 03 source selection

- Jobs release/test runner paths were selected from `f119e2e7`, `4f1179d3`, `8a27b784`, and `753db9f6`. Their dynamic GUI discovery, filesystem boundary, environment isolation, and test reporting were retained.
- V2 runner changes were selected from `c4d4be9c` and `e6440fbb`: portable/acceptance scopes, pinned evidence SHA-256, and split FTP test boundaries. The FTP boundaries now discover `test_ftp_widget_*.py` modules dynamically.
- `artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md` was restored from V2 at its exact pinned content hash and is normalized to LF with a narrow `.gitattributes` rule.
- The preserved V2 dirty snapshot contains no runner files from this wave; it was not modified.
- The wave source commit is `4ed2075c072b0cd38ca05249a9670aa96dfc3af1`; it is isolated and has not been merged into local `develop`.

## WAVE 04 source selection

- Jobs has no config-storage implementation delta for this wave. The V2 modular storage implementation was selected from `79fec477` on branch `codex/v2-master-repair-20261017` and reconciled with the integration source.
- Develop's hide-finished Jobs and SSH retry preferences were absent from the V2 facade, so both getter/setter pairs were restored and included in the public API contract.
- The V2 WIP core's dynamic facade callbacks were rejected to keep dependencies one-way. The profile WIP's use of a core module reference was retained as an explicit import; deletion cleanup is composed by the facade to avoid a new dependency cycle.
- The 27-file source set has fingerprint `c41c0f9b5873f2e0ee49c5420d1bb3fd2f4aa63aa885c7073c226f2b74c6f153`; its source commit is `71ef960bb486cc821e1a79f969e5b58913841715`. It is isolated and has not been merged into local `develop`.

## Dirty and ignored source classification

- Main user checkout `codex/log-repeat-groups` at `a742576dd9fae130cedc65070baec73b98f66df5`: four tracked modifications (`i18n/en.json`, `i18n/tr.json`, `wx_logs_view.py`, `tests/test_wx_logs_groups.py`), zero untracked files, 63 ignored entries. These changes remain untouched.
- Jobs worktree: zero modified, untracked, or ignored entries.
- V2 worktree: 99 modified tracked, 74 untracked, and 32 ignored entries. The 173 modified/untracked files are copied to a separate snapshot; `V2_WIP_SOURCE_MANIFEST.json` records paths, statuses, SHA-256 values, and the aggregate fingerprint. The original worktree remains untouched.
- Local `develop` worktree: clean.

## Integration risks

Jobs focuses on profile-scoped job persistence, provenance, workspace controllers, wx Jobs behavior, SSH settings, and focused GUI fixtures. V2's committed changes cover CLI/config/plugin facades, Qt outputs, dialogs, updater and release-runner changes. The uncommitted V2 source contains additional GUI modularizations, plus unrelated packaging/test-runner work. Only responsibility-scoped source will be selected; Muse report claims are historical and are not acceptance evidence for this integration.
