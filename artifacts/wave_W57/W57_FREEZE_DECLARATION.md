# W57 — Candidate Verification and Freeze Declaration Record

Wave: `W57` (execution kind, canonical_source `W57`).
Run phase worker: opencode executor, project-authorized model route.
Lease identity (LOCAL_REAL, serial fallback): run `ses_f28c68d44ffeNNM52nDfznGacI`, phase `W57/run`.
Content identity (controller handoff): `d12d2330f79be8242d068748f5788553f3e07a27178f2661c6b14a1f36a6b455`.

## Frozen candidate (built by W56, verified — not rebuilt — by W57)

```text
Candidate ID:      W56-frozen / W57-verified
Main SHA:          `36d6151fd9634cf50e14a639ec0407bef1d296f4`
Plugin SHA:        in-tree at the same HEAD (no separate registry repo)
Artifact:          `dist/hpc-client-gui/hpc-client-gui.exe`
SHA256:            `6cca43a5a98a2c7049aae182b58473db4c491dabc06b13cf599bd429e45e530e`
Built:             Windows 11 AMD64, Python 3.14.0, PyInstaller 6.22.2, wxPython 4.3.1
Bundle:            172 files, zero Qt tokens (no `PySide*`, no `shiboken*`, no `Qt6*.dll`)
Version:           1.5.9 (`version` from outside the repo: `1.5.9` / `python: 3.14.0`, exit 0)
Support matrix revision: `docs/wiki/Compatibility-and-Support-Matrix.md` at `7f3e92b3`
  (W57 wx-only realignment) + `artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md` (frozen matrix)
Open P2:           none
Open P3:           DEF-W57-001 (missing `jobs.refresh*` i18n keys; routed to W28; record below)
P0/P1:             0
Frozen for W58:    NO — W57 run returns REOPEN (DEF-W57-001 routed to owner; rebuild + rerun required)
```

W57 did not rebuild, patch, or re-sign the candidate. Behavior diff
`36d6151f..7f3e92b3` over `src/ build/ requirements.txt
requirements-release.lock pyproject.toml` is empty; all W57 source changes are
`docs/wiki/` (support-matrix/install realignment) plus
`tests/test_w57_freeze_consistency.py`. Packaged evidence below binds to the
exact artifact SHA-256 above and carries over truthfully.

## Explicitly NOT the candidate (rollback/disambiguation, FREEZE-036/047)

Same-version pre-cutover archives and older candidate directories remain on
disk and must not be confused with the frozen artifact:

- `dist/hpc_client_gui-1.5.9-py3-none-any.whl` + `dist/hpc_client_gui-1.5.9.tar.gz`
  (2026-09-22, pre-cutover Qt-era build inputs; superseded, not the candidate)
- `dist/w14-candidate/`, `dist/w14-candidate-r1/` (Wave 14 artifacts, not V2-final)
- `dist/releases/`, `dist/hpc-updater-demo/` (adjacent release tooling, not the candidate)
- `dist/hpc-client-gui/` (the frozen bundle directory above; the ONLY
  `1.5.9` artifact bound by this declaration's SHA-256)

The previous known-good release remains identifiable by its own directory and
filename; no ambiguous overwrite was performed during W57 stabilization.

## W57 verification summary (this run, fresh)

- Packaged probes against the frozen artifact (from outside the repo):
  `version` → `1.5.9`, `doctor environment` → `status: PASS, frozen: True`,
  `--help`/`commands` inventory OK, clean-profile isolated first run
  (`HPC_GUI_CONFIG_ROOT` fresh root) → `PASS, profiles: 0`, exit 0.
- Bundle: 172 files, zero Qt tokens; exe size 7672473, SHA-256 as above.
- Source-independence: probes executed with cwd outside the repo.
- LOCAL_REAL replay (held lease): connection + reconnect PASS, SFTP 65536-byte
  round trip with matching SHA-256 PASS, remote editor save with server-side
  hash PASS, disposable Slurm job submit → RUNNING on `compute02` → cancel →
  `CANCELLED` PASS, PTY (`/dev/pts/0`) PASS, lab cleanup done.
- `LOCAL_PASSWORD_REAL` fixture (real containerized OpenSSH): password success
  PASS and invalid-password rejection PASS via the product's transport
  library; fixture torn down afterwards. No passwords persisted.
- Focused suites at `7f3e92b3`: `test_qt_removal_gate` +
  `test_wave0_unicode_baseline` + `test_wheel_packaging` 61 passed;
  `test_version_consistency` + `test_remote_entry_helpers` 13 passed;
  `test_wx_w55_shell_soak` 2 passed; `test_w04_support_freeze` 28 passed;
  `test_w57_freeze_consistency` 5 passed (sensitivity proven by fault
  injection); `compileall` exit 0; scoped `ruff` clean; `git diff --check`
  clean; `ci.py docs` PASS; `ci.py packaging` PASS; `ci.py audit` PASS.
- Maintained gate `ci.py full` → FAIL at the release-preflight i18n check
  (4 missing keys, see DEF-W57-001). Whole-repo `ruff` has 281 pre-existing
  errors (static-debt record, not introduced by W57).

## DEF-W57-001 (routed, not fixed here)

- Severity: P3. Surface: Jobs tab refresh status label (`wx_jobs.py`).
- Reproduction: refresh the Jobs tab; the status label renders the raw key
  `jobs.refreshing` because `src/hpc_gui/i18n/en.json` and `tr.json` define
  none of `jobs.refreshing`, `jobs.refresh_updated`,
  `jobs.refresh_failed_stale`, `jobs.refresh_failed`.
- Expected: localized status text. Observed: raw i18n key for the
  `refreshing` path (the other three paths have English fallbacks).
- Owner Wave: `W28` (feature evidenced in `W28_WAVE_REPORT.md` /
  `WAVE_W28_AUDIT_REPORT.md`; `W28` is CLOSED) → controller-owned
  closed-owner repair transaction. W57 does not patch product code: any
  product/i18n-bundle correction invalidates the W56 freeze and requires a
  rebuild plus rerun of affected W56/W57 evidence.
- Release decision: no P0/P1 open; P3 recorded with owner and resume point.
  W57 packaged/external/GUI evidence above remains valid for the current
  candidate except the red `FREEZE-029` gate; after the owner repair +
  rebuild, rerun packaged regression against the NEW candidate SHA and
  re-verify this declaration's successor.

## Handoff note

W58 consumes the SUCCESSOR of this declaration (rebound to the post-repair
candidate) unchanged — not this blocked record. This file is the truthful
W57-run artifact for controller scheduling.
