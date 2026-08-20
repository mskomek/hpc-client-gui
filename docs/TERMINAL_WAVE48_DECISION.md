# Wave 48 — Embedded Terminal Architecture Decision

Status: audit complete; implementation deferred to Wave 49
Date: 2026-08-20

## Decision

Keep the existing Paramiko connection and interactive PTY channel. Replace
only the text-view/parser rendering seam with a local xterm.js frontend hosted
by `QWebEngineView` and connected through `QWebChannel`.

The browser surface is local-only: xterm.js, its CSS, fonts, and addons are
bundled application assets. No CDN, remote navigation, analytics, or external
web content is allowed. The WebEngine page must use a restrictive CSP and
reject navigation away from the bundled local document.

Wave 49 may proceed only after a clean supported Windows/Linux package build
proves that the existing pinned `PySide6_Addons` wheel carries
`QtWebEngineWidgets` and `QtWebChannel` correctly in the onedir/AppImage/deb/
Flatpak layouts. The verified Linux `PySide6_Addons==6.11.2` wheel is about
167 MiB and exposes both modules; no separate WebEngine dependency is needed.
The current repository still contains no xterm.js assets, so no runtime asset
is added in Wave 48.

## Current ownership map

| Stage | Current owner | Contract for migration |
| --- | --- | --- |
| SSH connect/auth/profile lifecycle | `src/hpc_gui/ssh/client.py:SSHClient.connect`; `ui/widgets/login_widget.py:_ConnectionWorker` | Reuse unchanged. |
| PTY allocation | `SSHClient._start_shell_session` → `client.invoke_shell(term="xterm", width, height)` | Reuse; keep one channel and existing geometry. |
| Receive loop | `SSHClient._shell_reader_loop` → `_handle_shell_output` | Reuse byte arrival/thread boundary; Wave 50 owns decoding/backpressure hardening. |
| Current fallback sanitization | `ssh/client.py:_sanitize_terminal_text` | Keep only for logs/fallback; never feed sanitized text to xterm. |
| Parser/state | `services/terminal_emulator.py:TerminalEmulator` | Adapter-era code only; remove after Wave 49–52 call-site gates. |
| Paint | `login_widget._append_shell_output_to_widget` → `TerminalEmulator.feed/render` → `_TerminalConsole.setPlainText` | Replace with bridge output to xterm; status/log lines remain separate. |
| Keyboard mapping | `_TerminalConsole` event filter → `login_widget._terminal_key_sequence` → `SSHClient.send_shell_input` | Replace key translation with xterm-generated input bytes. |
| Clipboard/paste | `_TerminalConsole` paste handler → `_paste_console_clipboard` → `send_shell_input` | Preserve through xterm selection/clipboard bridge; bracketed paste is a Wave 50/51 gate. |
| Resize | `login_widget.eventFilter` → `_sync_shell_geometry` → `SSHClient.resize_shell_pty`; emulator resize | Keep PTY resize; bridge forwards xterm dimensions. |
| Command history/command bar | `TerminalInput`, `command_history_store`, `run_command_text` | Wave 51 owns removal/relocation; do not delete in Wave 48. |
| Connect/disconnect | `_begin_connect_async`, `_on_connect_finished`, `_handle_ssh_disconnected` | Preserve signals and status UI; terminal receives no app diagnostics. |

Public methods/signals to preserve until the new widget is integrated:
`SSHClient.send_shell_input`, `send_shell_text`, `resize_shell_pty`, the shell
output/disconnect callbacks, and `LoginWidget.shell_output_message` /
`ssh_disconnected`.

## Bridge contract

- Python → JavaScript: raw PTY bytes/text delivered in order over a bounded
  queued Qt signal; application status uses a separate UI label/log channel.
- JavaScript → Python: xterm `onData` input and `onResize` dimensions through
  `QWebChannel`; Python validates dimensions before calling
  `resize_shell_pty`.
- The bridge owns no SSH connection and contains no Slurm logic.
- WebEngine initialization failure is visible in the status surface with an
  actionable message; it is a package/release gate failure, not a permanent
  second terminal engine.

## Dependency and licensing gate

| Dependency | Planned role | Evidence/gate |
| --- | --- | --- |
| PySide6_Addons | `QWebEngineView`, `QtWebChannel` | Existing `6.11.2` lock entry; verified in the Linux wheel, still require Windows/package smoke gates. |
| QtWebEngine/QtWebChannel runtime | Local Python↔JS bridge | Keep under the existing Qt LGPL handling; preserve the wheel’s LGPL/GPL/commercial notice provenance. |
| xterm.js | VT/xterm rendering | Vendor a versioned upstream asset and preserve its MIT license/NOTICE in `third_party_licenses/`. |
| xterm addons | Only explicitly selected features | No addon is approved yet; each requires a source/version/license record before vendoring. |

Wave 49 must update the existing lock, version manifest, SBOM, Qt source
metadata, and package license placement together with the actual dependency.
No copied/minified asset may enter the tree without provenance.

## Behavior contract for Waves 49–52

Required: local offline rendering; `xterm-256color` (or a tested compatible
value); 256-color/true-color, bold/dim/italic/underline/inverse, cursor
movement, alternate screen, erase/clear, scroll regions, bracketed paste,
application cursor/keypad modes, Unicode/combining/wide characters, bounded
scrollback, direct terminal focus/input, PTY resize, control keys, function
keys, selection, and Windows/Linux clipboard behavior.

Optional polish: theme controls, font controls, search UI, and broader TUI
compatibility beyond the later contract tests.

Application diagnostics, connection banners, reconnect prompts, and status
messages must never be injected into the remote PTY byte stream.

## Migration and rollback

1. Wave 49 adds the bridge/frontend behind an internal seam and proves local
   asset loading with fake PTY input.
2. Wave 50 hardens byte decoding, complete sends, PTY resize, cancellation,
   and bounded buffering.
3. Wave 51 makes the new terminal the default and removes the permanent
   command-entry surface after keyboard/UX checks.
4. Wave 52 runs TUI/package/CI gates and removes `TerminalEmulator` and
   `TerminalInput` only after all call sites are gone.

Rollback is source-level: keep the old parser only until the replacement gates
pass, then remove it. Do not ship two user-selectable terminal engines.

## Wave 49 implementation allowlist

- Add the local xterm.js asset bundle and its preserved license notice.
- Add the minimal terminal bridge service and WebEngine widget.
- Add only the required WebEngine/WebChannel dependency and packaging entries.
- Add fake-PTY/bridge tests for local asset loading, input, output, resize, and
  navigation/CSP rejection.
- Keep `ssh/client.py`, authentication, transfers, Slurm, X11, and CLI terminal
  behavior unchanged.

## Evidence and blockers

- `ssh/client.py`, `login_widget.py`, `terminal_input.py`, and
  `terminal_emulator.py` are the current terminal owners.
- No WebEngine, WebChannel, xterm.js, npm, or CDN dependency exists in the
  current tree.
- No live cluster or credential access was used.
- Final Wave 48 PASS still requires the clean Windows/Linux package gate for
  the WebEngine dependency; that gate belongs before Wave 49 implementation.
