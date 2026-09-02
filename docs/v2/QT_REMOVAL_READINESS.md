# Qt Removal Readiness

The current evidence is **NO-GO**. The gate requires every P0 baseline row to
be `COVERED` in `V2_PARITY_STATUS.md` and rejects the release while the Qt
runtime remains declared in `pyproject.toml`.

Run:

```text
python scripts/qt_removal_gate.py
```

Exit code `0` means GO; exit code `2` means NO-GO. A NO-GO report must list the
uncovered P0 IDs and remaining Qt dependency. This wave intentionally removes
nothing; Wave 67 may act only after this gate is GO and packaged/manual evidence
is complete.
