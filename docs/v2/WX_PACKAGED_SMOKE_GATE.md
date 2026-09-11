# Packaged wx Smoke Gate

Run from the unpacked wheel or packaged application environment:

```text
python scripts/wx_packaged_smoke.py
```

The JSON report must contain `wx-packaged-smoke/1` and `PASS` for process
start, wx runtime, main-frame creation, real terminal readback, packaged
files/editor/jobs/plugin/ANSYS/diagnostics-updater surface imports, and clean
shutdown. It also verifies the real packaged files/transfer, editor, and jobs
control dictionaries created by the main wx frame, an offline Unicode editor
round-trip, and transfer-queue rendering. It records Python/platform
information but never dumps environment or connection data.

The gate is deliberately headless. Display-dependent launch, real-cluster
authentication/MFA, X11, clipboard/DnD, transfer conflict/resume, and live
output remain manual release checks in `V2_MANUAL_GUI_TEST.md`; source pytest
alone is not packaged evidence.
