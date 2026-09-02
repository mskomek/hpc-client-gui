# Packaged wx Smoke Gate

Run from the unpacked wheel or packaged application environment:

```text
python scripts/wx_packaged_smoke.py
```

The JSON report must contain `wx-packaged-smoke/1` and `PASS` for launch,
terminal, files, editor, plugin/ANSYS, and diagnostics/updater imports. It
records Python/platform information but never dumps environment or connection
data.

The gate is deliberately headless. Display-dependent launch, real-cluster
authentication/MFA, X11, clipboard/DnD, transfer conflict/resume, and live
output remain manual release checks in `V2_MANUAL_GUI_TEST.md`; source pytest
alone is not packaged evidence.
