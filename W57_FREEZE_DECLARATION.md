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
