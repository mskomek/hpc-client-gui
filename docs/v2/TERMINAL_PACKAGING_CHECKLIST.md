# Terminal Packaging Verification Checklist — Wave 77

## Required packaged assets

Inside the artifact, verify presence of:

```text
wx_index.html
wx_bridge.js
xterm.js
xterm.css
addon-fit.js
NOTICE.md
```

Plus any additional locally vendored terminal addon introduced by these waves.

**Rule:** Prove the packaged runtime does NOT load assets from the source checkout.

## Offline test

Disable network access during terminal page initialization. The terminal renderer must still start. No CDN or network dependency is allowed.

## Security/privacy

Verify:

- No CDN
- No external script
- No external navigation
- No network fetch from terminal page
- Terminal keystrokes are not logged
- Pasted contents are not logged
- Terminal screen contents are not exported into diagnostics unless the existing privacy contract explicitly allows that

## Per-platform status

### Windows

| Item | Status |
|---|---|
| WebView2/Edge backend | VERIFIED (wx.html2.WebViewBackendEdge available) |
| Local file:// page load | VERIFIED (wx_index.html loads via file:/// URL) |
| xterm.js init | VERIFIED (xterm initializes, terminal.open succeeds) |
| hpcWrite → terminal.write | VERIFIED (tests prove JSON bridge works) |
| Packaged WebView2 runtime | BLOCKED (no packaged artifact built in this session) |
| `wx.html2` import works | VERIFIED (wx 4.3.1 msw, wxWidgets 3.3.3) |
| `IsBackendAvailable` | VERIFIED (Edge backend available) |

### macOS

| Item | Status |
|---|---|
| WebKit-based wx WebView path | BLOCKED (no macOS environment) |
| Signed .app bundle | BLOCKED |

### Linux

| Item | Status |
|---|---|
| GTK/WebKit runtime requirements | BLOCKED (no Linux environment) |
| `libwebkit2gtk` availability | BLOCKED |

## Packaged flow required

```text
launch packaged app
↓
wx runtime
↓
open terminal
↓
local xterm assets load
↓
ready handshake
↓
input/output
↓
resize
↓
close cleanly
```

## Evidence

- `docs/v2/GUI_TERM_001_EXECUTION_EVIDENCE.json` — Wave 76 behavioral evidence
- `docs/v2/TERMINAL_PARITY_CONTRACT_72.md` — 35-gap contract (Wave 72)
- `docs/v2/TERMINAL_PARITY_GAPS_72.json` — machine-readable gaps
- `docs/v2/TERMINAL_PACKAGING_CHECKLIST.md` — this file

## Commit history (Waves 72-77)

| Commit | Wave | Description |
|---|---|---|
| `c5120150` | 72 | `docs: rebaseline wx terminal parity` |
| `20ee7bb7` | 73 | `feat(wx): add xterm webview terminal renderer` |
| `7696ef99` | 74 | `fix(wx): restore terminal input and PTY semantics` |
| `9f522ac3` | 75 | `feat(wx): complete terminal chrome and lifecycle parity` |
| `f1ca2d1d` | 76 | `test(wx): prove terminal behavioral parity` |
| (pending) | 77 | `test(packaging): validate wx terminal webview backends` |
