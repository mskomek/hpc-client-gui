# Qt Removal Readiness

The current evidence becomes **GO** once every P0 baseline row is `COVERED` in
`V2_PARITY_STATUS.md`. Remaining Qt dependencies are reported as inventory;
they are expected before the removal step and are not themselves a gate
failure.

Run:

```text
python scripts/qt_removal_gate.py
```

Exit code `0` means GO; exit code `2` means NO-GO. A NO-GO report must list the
uncovered P0 IDs and the Qt dependency inventory. Wave 67 may act only after
this gate is GO and packaged/manual evidence is complete.
