# W57 Freeze Declaration (successor, W58 consumes unchanged)

Wave: `W57.1` unit `U04` repair rebind for `W58` consumption unchanged.
Status: REBOUND-U04 (prior draft SHA `740fe48e` SUPERSEDED by live rebuild).

## Exact identities

```text
Main commit:   0eb4f0d5026f87ba1aaad0dc1ba301590d82ca7d (branch develop)
Plugin SHA:    in-tree at the same HEAD (no separate registry repo, no submodule)
Artifact:      dist/hpc-client-gui/hpc-client-gui.exe
Artifact SHA:  B3019DEA16783C8AB859FA36D2B0FEF2FB70DB075633E54EB0F36587295374FD
Size:          7672106 bytes
Bundle:        172 files, zero Qt tokens (no PySide*, no shiboken*, no Qt6*.dll)
Build:         build/windows/hpc-client-gui.spec via .venv Python 3.14.0 + PyInstaller 6.22.2
Version:       1.5.9, runtime wxV2 (DEFAULT_GUI_RUNTIME = "wx")
```

## U01-U04 proof set bound to the above SHA only

- U01: narrow W04 baseline 39/39 PASS exit 0 (smoke, content, manifest,
  freeze-consistency) + clean-profile first-run 27/27 PASS exit 0.
- U02: packaged functional replay 110/110 PASS exit 0 (SSH auth/lifecycle,
  PTY wire/IO/lifecycle, SFTP semantics, wx remote files, Slurm state,
  submit/cancel).
- U03: error/recovery + lifecycle/soak 11/11 PASS exit 0; full post-cutover
  packaged rerun (CUTOVER-003) 50/50 PASS exit 0.
- Verify: single-invocation cross-lane replay 81/81 PASS exit 0.
- U04 repair: 20-node serial closeout sweep, exit 0 (see evidence manifest).
- All batches ran with `-n auto` (parallel) except the serial U04 sweep,
  against disposable fixtures; real user config untouched.

## Support matrix (claimed only)

- Windows AMD64 packaged exe, wxV2 runtime, Python 3.14.0 embedded.
- No other platform claimed by this declaration.

## Open defects

- P0: none. P1: none. (U04 scope; frozen 6cca43a5 replay UNRECOVERABLE and
  pre-cutover 8ba80453 plus draft 740fe48e evidence SUPERSEDED are
  provenance states, not product defects. Packaged-exe fresh-user hang and
  editor-owner assertion stay routed to their owners per the wave-local
  freeze file; neither was reproduced in the U01-U04 replay batches, which
  are all green.)

## Invalidation

All pre-cutover acceptance evidence is invalid for closeout. Only the
U01-U04 proof set on SHA B3019DEA above is current. Any byte change mints
a new SHA and voids this declaration pending rerun.

## W57.4 final freeze (HPC-W10-FREEZE-044..048) - consumed unchanged by W58/W11

Status: **FROZEN** by W57.4 on 2026-10-01. This section completes the declaration above; the
identities are unchanged.

### Candidate manifest (FREEZE-044) and SHA-256 (FREEZE-045)

```text
Artifact path:   dist/hpc-client-gui/hpc-client-gui.exe
Artifact SHA256: B3019DEA16783C8AB859FA36D2B0FEF2FB70DB075633E54EB0F36587295374FD (re-hashed 2026-10-01)
Size:            7672106 bytes
Version:         1.5.9, runtime wx V2, Python 3.14.0 embedded, PyInstaller 6.22.2
Build source:    0eb4f0d5026f87ba1aaad0dc1ba301590d82ca7d; src/, build/ (except build/audit evidence)
                 and pyproject.toml are byte-identical at every later commit used for W57.4 evidence
Bundle:          172 files, zero Qt files
Manifest JSON:   artifacts/wave_W57.4/WAVE_W57.4_EVIDENCE_MANIFEST.json
```

### Previous builds stay identifiable (FREEZE-047)

| Path | SHA-256 | Role |
|---|---|---|
| `dist/hpc-client-gui/hpc-client-gui.exe` | `B3019DEA16783C8AB859FA36D2B0FEF2FB70DB075633E54EB0F36587295374FD` | **frozen candidate** |
| `dist/releases/w16-candidate/hpc-client-gui-windows-onedir.exe` | `544E186F81AA685EE80A3C07185EE0EB03AB1BC73A81151B1323253503C0A1DA` | previous W16 candidate (older, distinct directory and filename) |
| `dist/hpc-updater-demo/hpc-updater-demo.exe` | `F93740363D9D2336EAC638DA5B2A6F293B523E0C630DA028F55A60A655EB7BBA` | updater demo, not a release |
| draft `740fe48e` / original W56 `6cca43a5` | (not on disk) | SUPERSEDED / UNRECOVERABLE; never to be relabelled as the candidate |

No file in `dist/hpc-client-gui/` was rebuilt or overwritten during W57.2-W57.4.

### W11 hand-off set (FREEZE-048)

W11 receives exactly: the artifact above (verify the SHA-256 before use), this declaration,
`artifacts/wave_W57.4/WAVE_W57.4_EVIDENCE_MANIFEST.json` and the evidence named in
`docs/wave-reports/v2/opencode/W57.4_WAVE_REPORT.md`. W11 must not rebuild a "same version" binary;
any rebuild mints a new SHA-256 and requires a new freeze.

### Open defects at freeze

P0: none. P1: none. P2/P3: listed with decisions in the W57.4 defect ledger
(`docs/wave-reports/v2/opencode/W57.4_WAVE_REPORT.md`, section "Defect ledger").
