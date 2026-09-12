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

This is a real windowed wx run, not a headless test: the packaged terminal input
probe uses guarded Windows `SendInput` and requires the application window to be
foreground. A runner that cannot foreground the app must report the missing
terminal echo as a failure and must not send keys to another window; it must not
count a skipped or injected bridge callback as keyboard parity. Real-cluster authentication/MFA, X11,
clipboard/DnD, transfer conflict/resume, and production live output remain
manual release checks in `V2_MANUAL_GUI_TEST.md`.

Latest Windows attempt (2026-09-12, Python 3.12.4, dirty worktree based on HEAD
`12ce79935bf076e1062c57dc7dbd148bad2bfae1`, artifact SHA-256
`c83c1b05c157a97b040c705efe722855cd1511ee3b59de19c87341e18a38394f`): **FAIL**.
The process, wx runtime, frame, UI surfaces, editor round-trip, and PTY resize
passed; the xterm DOM focus query returned the helper textarea. This dirty-tree
run is not a dedicated clean-HEAD WebView2 readiness PASS. Foreground activation
was denied (`foreground_matches_frame=false`), so
the guarded probe sent no keys; DOM keydown/beforeinput/input, bridge input, and
SSH input counts were all zero. Terminal output/readback and downstream
round-trips consequently failed. The exact report is
`build/audit/wx-packaged-smoke-windows.json`.

A preceding build (`21141a8b3bb272269234bb18136afefe49927fa5530f85ca8aa5cec64c6c8394`)
did have the application foreground and accepted 36/36 `SendInput` events, but
still produced no terminal output. Together these attempts leave the native
keyboard → xterm → PTY boundary unresolved; neither run is a clean-HEAD release
artifact. Earlier packaged PASS evidence belongs to a different artifact and is
historical only. `GUI-TERM-001` remains **PARTIAL**.
