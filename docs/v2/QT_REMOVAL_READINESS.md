# Qt Removal Readiness

The gate is **NO-GO** while any production Python file imports PySide6. Every
P0 baseline row must first be `COVERED` in `V2_PARITY_STATUS.md`, and the
remaining Qt-only production files must be migrated or removed.

Run:

```text
python scripts/qt_removal_gate.py
```

Exit code `0` means GO; exit code `2` means NO-GO. A NO-GO report must list the
uncovered P0 IDs, the Qt dependency inventory, and the Qt-only file inventory.
Wave 67 may act only after this gate is GO and packaged/manual evidence is
complete.
