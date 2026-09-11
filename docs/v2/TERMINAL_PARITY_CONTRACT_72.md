# Terminal Parity Contract — Wave 72 Rebaseline

**Authority:** Wave 72 — Rebaseline terminal parity before renderer replacement.
**Branch verified:** `develop`
**HEAD verified:** `da44f6394a4c2cbd82a86f626865ea51b940cf9e` (hpc-client-gui, 2026-09-06; previous ledger head `e3408fd` superseded)
**Working tree:** clean tracked tree; untracked `.tmp/` and inherited `IMPI-core` artifacts under `.ai/`, `artifacts/`, `audit/oldgui/`, `build/`, `sourcemds/` etc. left untouched per critical rules (preserved, not committed).
**Qt runtime:** `src/hpc_gui/runtime.py:3` `DEFAULT_GUI_RUNTIME="qt"` unchanged; Qt remains production runtime. wx remains optional.
**Rule:** Do not mark `GUI-TERM-001` COVERED until the full `real wx event → WebView/xterm → production adapter → disposable PTY → xterm-visible` chain is demonstrated. This wave freezes the contract only; no renderer is implemented here.

The accompanying `TERMINAL_PARITY_GAPS_72.json` is the Wave 72 historical
TextCtrl baseline. The current renderer inventory includes
`src/hpc_gui/wx_terminal_webview.py`; current status and reproducibility are
tracked in `GUI_TERM_001_EXECUTION_EVIDENCE.json` and remain **PARTIAL**.

---

## 1. Qt Reference (authoritative)

- `src/hpc_gui/ui/widgets/terminal_widget.py:1-120` — `TerminalWidget` embeds `QWebEngineView` + `QWebChannel`. Loads `src/hpc_gui/assets/terminal/index.html` via `QUrl.fromLocalFile`. `LocalTerminalPage.acceptNavigationRequest` allows only `isLocalFile && is_main_frame`. CSP in `index.html:4` `connect-src 'none'`. Timer `READINESS_TIMEOUT_MS=5000`, `_resize_timer` 50 ms debounced `resizeEvent → _fit → runJavaScript("hpcFit")`.
- `src/hpc_gui/assets/terminal/index.html:1-20` — `xterm.css` + vendored `xterm.js` 6.0.0 + `addon-fit.js` 0.11.0 + `bridge.js`. No `qrc:///qtwebchannel/qwebchannel.js` beyond Qt; CDN absent.
- `src/hpc_gui/assets/terminal/bridge.js:1-26` — `new Terminal({convertEol:false, scrollback:2000, cursorBlink:true})`, `FitAddon.FitAddon()`, `terminal.open(...)`, `window.hpcFit` reports `terminal.cols/rows` → `hpcBridge.resize(cols,rows,pxW,pxH)`, `window.hpcClear/ Focus/ SetFontSize` (font change re-fits), `QWebChannel` binds `output → terminal.write`, `terminal.onData → send_input`, `terminal_ready`.
- `src/hpc_gui/services/terminal_bridge.py:1-55` — `TerminalBridge(QObject)` with `output/state_changed/error/ready` signals, `attach(ssh)/detach()`, `receive_output → output.emit`, `send_input(text) → ssh.send_shell_input`, `resize(cols,rows) → ssh.resize_shell_pty`, `terminal_ready → ready.emit`.
- `src/hpc_gui/ui/widgets/terminal_header.py:1-60` — presentation-only header: `status_label`, `identity_label` (bold), `•` separator, `dimensions_label` (`—` → `cols×rows`), `find/clear/font_down/font_up` `QToolButton`s, `retranslate_ui()` via `t()`, signals `find_requested/clear_requested/font_delta_requested`.
- `src/hpc_gui/ui/widgets/terminal_input.py:1-75` — **hidden in production** (see §3). `TerminalInput(QLineEdit)` with `command_submitted/reconnect_requested`, `history = get_global_history_store()`, `set_connected`, `submit_current` (Enter, `r`→reconnect when disconnected, `history.add`), `keyPressEvent` Up/Down → `history.items` navigation with empty sentinel, Return/Enter submit. `setVisible(False)` in `login_widget.py:332`; dead surface (see §3).
- `src/hpc_gui/ui/widgets/login_widget.py:293-389,573-642,660-670,1551-1556,1630-1656` — wires header+widget: `terminal_widget = TerminalWidget(self)`, header buttons → `find_text/clear/change_font_size`, `append_shell_output → bridge.receive_output`, `detach/attach` on connect/disconnect/reconnect with generation-aware `_pending_old_ssh`, `_sync_shell_geometry` via `_console_shell_geometry` (uses view size → `resize_shell_pty`), `_terminal_key_sequence` maps `Ctrl+letter → \x01-\x1f` (via `ord(ch)-64` for `@.._` range), special_map `{Return:\r, Tab:\t, Backtab:\x1b[Z, Backspace:\x7f, Escape:\x1b, Left:\x1b[D, Right:\x1b[C, Up:\x1b[A, Down:\x1b[B, Home:\x1b[H, End:\x1b[F, Delete:\x1b[3~, PageUp:\x1b[5~, PageDown:\x1b[6~, Insert:\x1b[2~}`, `_paste_console_clipboard` does `clipboard.text().replace("\r\n","\n").replace("\r","\n").replace("\n","\r") → send_shell_input`, `_find_terminal_text` via `QInputDialog.getText → terminal_widget.find_text`.
- `src/hpc_gui/ssh/shell_session.py:1-292` — `InteractiveShellSession` owns PTY: `invoke_shell(term="xterm-256color", width=cols, height=rows)` fallback `xterm`, `send_text/send_input/send_payload` (UTF-8, `closed` guard, send loop), `resize(cols,rows)` → `channel.resize_pty`, `decode_bytes` with incremental UTF-8, `drain_initial_output` 0.35s, `_handle_output` → `on_output_cb` else `_sanitize_terminal_text` (strips ESC sequences only for log fallback; real bridge bypasses sanitizer and preserves bytes), `_reader_loop` thread + stop/join.
- `src/hpc_gui/ssh/client.py` — `SSHClientFacade` exposes `send_shell_input`, `resize_shell_pty`, `info` for identity.

Reference assets are fully local: `xterm.js` 488472 B, `xterm.css` 7112 B, `addon-fit.js` 1521 B, vendored under `src/hpc_gui/assets/terminal/` with `NOTICE.md` MIT 6.0.0.

---

## 2. wx Current (pre-72)

`src/hpc_gui/wx_terminal.py:1-305` — `TerminalModel` + `build_terminal_panel(ssh,lifecycle)` + `show_terminal(...)`:

- Model: `self.text=""` Python string, `receive(data)` → `self.text += str(data)` then `splitlines()` truncate to 5000 lines, `key_input` only `C→\x03, D→\x04, Z→\x1a` else `chr` passthrough, `resize(width,height,char_width=8,char_height=18)` → `width//8 × height//18` → `resize_pty`, `find(query) → text.find`, `clear()`, `change_font_size` clamp 6..32.
- View: `wx.Panel` with toolbar `TextCtrl(find)+Button(Find/Clear/A-/A+)` + single `wx.TextCtrl(TE_MULTILINE|TE_RICH2|TE_PROCESS_TAB)` used as both output and input (`_wx_terminal_controls["input"] is output`). `apply_font` sets `GetFont().SetPointSize(model.font_size)`, `do_find` does `model.find→SetInsertionPoint+SetSelection+ShowPosition`, `do_clear` clears model+TextCtrl, `render_output` does `model.receive → ChangeValue("\n".join(text.splitlines()[-5000:])) → ShowPosition(GetLastPosition())`, `key_event` binds `EVT_CHAR`, handles `Ctrl+C/V` via `Copy/Paste` locally, maps `GetUnicodeKey` 32..126 else `GetKeyCode → chr`, special-cases 3/4/26 → C/D/Z, then `model.key_input`, `on_size → model.resize(GetClientSize())`, output subscription via `ssh._wx_output_subscribers.append(Cal lAfter(render_output))`, `close()` removes subscriber + unsubscribe_language_change, `set_ssh(new_ssh)` swaps callbacks but leaks old subscriber identity if `_wx_output_subscribers` object identity changes, lifecycle `register_cleanup(close)` + `EVT_WINDOW_DESTROY`.

`src/hpc_gui/wx_shell.py:186-193` — embedded terminal page: `_build_terminal_panel(notebook, ssh=_term_ssh, lifecycle)` adds tab `help.section_terminal` (wx-only deviation; Qt has no notebook Terminal tab — its terminal lives inside Connection right pane). `show_terminal` detached frame wraps same panel type. Both share TextCtrl architecture.

Existing tests: `tests/test_wx_terminal.py` (model-only, asserts 8x18 math, `splitlines` path, no xterm), `tests/test_wx_embedded_terminal.py` (9 PROVEN via real wx button → model → visible TextCtrl, but asserts TextCtrl selection/value/font, not xterm). No WebView, no FitAddon, no output buffering, no readiness handshake, no external-navigation blocking.

---

## 3. Legacy command-input ambiguity — finding

`TerminalInput` exists and is tested (`login_widget.py:315, cmd_in`), but the integrated production GUI hides it:

```python
# login_widget.py:330-332
self.quick_command_row = QWidget()
self.quick_command_row.setLayout(cmd_row)   # holds TerminalInput + Run button
self.quick_command_row.setVisible(False)   # ← dead surface, not reachable
right_lay.addWidget(self.quick_command_row)  # still in layout but hidden
self.console_title_label.setVisible(False)
```

`setVisible(False)` is unconditional; no code later shows the row (history navigation remains in `TerminalInput` but user cannot focus it). The visible command surface in production is the xterm itself via `terminal.onData → send_input`. The header Find/Clear/font remain reachable; the quick-command row does not.

**Disposition:** Document as hidden/dead in current production behavior. wx must **not** add a visible command-input row to "restore" it. If a future product decision re-enables a quick-command row, it must be a separate wave with explicit UX approval. Current wx `wx_terminal.py` also has no command row, which is correct for parity-by-intent. Do not block parity on reproducing a hidden surface.

---

## 4. Gap Matrix (authoritative)

Classification: `CRITICAL` = blocks `GUI-TERM-001` COVERED; `MAJOR` = visible behavior loss; `MINOR` = cosmetic/i18n nuance. All wx gaps below are measured against the Qt xterm reference, not against the wx test suite's self-referential asserts.

| # | Behavior | Qt (xterm.js) | wx (TextCtrl) current | Gap | Severity | Evidence |
|---|---|---|---|---|---|---|
| 1 | ANSI/VT parsing | `terminal.write` parses CSI/ESC, DCS, OSC per xterm.js | `render_output` does `ChangeValue("\n".join(splitlines()))`, never calls PTY parser; escape bytes rendered as text or stripped by later `splitlines` loss | No parser; all escape sequences displayed literally or lost | CRITICAL | `wx_terminal.py:143-146`, `bridge.js:terminal.write`, `shell_session.py:_sanitize` bypass comment |
| 2 | SGR colors/styles | xterm.js handles `select graphic rendition` (30-37/90-97, 1 bold, 0 reset, etc.) and renders styled spans | No SGR; `TE_RICH2` unused for styling, `ChangeValue` is plain text | Colors/bold/reset missing | CRITICAL | same |
| 3 | Carriage-return overwrite | `convertEol:false`, terminal honors `\r` as CARRIAGE RETURN (overwrite current line, used for `Progress 10%\r20%`) | `splitlines()` normalizes `\r`→`"\n"` boundaries, then `"\n".join(splitlines())` turns `\r` into newline; `Progress 10%\r20%` becomes two lines | Broken progress overwrite | CRITICAL | `shell_session.py:decode` preserves `\r`, wx discards |
| 4 | Cursor movement | xterm tracks cursor, `CUB/CUF/CUP` overwrite | No cursor state; TextCtrl insertion point is unrelated to VT cursor | Movement ignored | CRITICAL | — |
| 5 | Erase line / erase screen | `EL (2K)/ED (2J)` handled by xterm viewport/scrollback | No erase handling; `splitlines` never erases | Erase becomes literal | CRITICAL | — |
| 6 | Alternate screen | `SM ?1049h / RM ?1049l` buffer swap; exit restores primary scrollback | No alternate buffer; exit never restores | Alt-screen broken | CRITICAL | — |
| 7 | Scrollback | `scrollback:2000` in bridge.js, xterm viewport + search addon can reach it | `model.text` capped 5000 lines then `ChangeValue` rebuilds full text each fragment (5000-line concat) — bounded string but not xterm scrollback; search via `find` on Python string | Scrollback model diverges; rendering rebuilds entire text per fragment (performance) | MAJOR | `wx_terminal.py:25-29`, `bridge.js:scrollback:2000` |
| 8 | Shell history via arrows | `TerminalInput` history store + Up/Down `history.items` sentinel (disconnected only for `r`); inside xterm, history is shell-side via Up `\x1b[A` | wx: no history store, `key_input` does not send `\x1b[A/B` for Up/Down; arrows filtered via `chr` path and never reach shell | History via arrows missing | CRITICAL | `terminal_input.py:44-68`, `wx_terminal.py:148-170`, `login_widget.py:_terminal_key_sequence` |
| 9 | Home / End | Qt sends `\x1b[H` / `\x1b[F` via `_terminal_key_sequence` | wx: `chr(GetKeyCode)` passthrough; `Home/End` become unmapped codepoints or ignored | Wrong sequence | CRITICAL | — |
| 10 | Delete | Qt `\x1b[3~` | wx no mapping | Missing | CRITICAL | — |
| 11 | Insert | Qt `\x1b[2~` | wx no mapping | Missing | CRITICAL | — |
| 12 | PageUp / PageDown | Qt `\x1b[5~` / `\x1b[6~` | wx no mapping | Missing | CRITICAL | — |
| 13 | Ctrl+A .. Ctrl+_ (0x01-0x1F) | Qt: `Ctrl+letter` with `text` → `chr(ord(ch)-64)` for `@.._` (covers `Ctrl+A→\x01 … Ctrl+Z→\x1a, Ctrl+[→\x1b, Ctrl+\→\x1c, Ctrl+]→\x1d, Ctrl+^→\x1e, Ctrl+_→\x1f`) | wx: only `C→\x03, D→\x04, Z→\x1a`, strict `not shift and not command` gate, copy/paste hijack prevents others, `Ctrl+A/B/E…` lost or copied | 26/31 codes missing | CRITICAL | `login_widget.py:578-581`, `wx_terminal.py:31-44` |
| 14 | Enter | Qt `\r` | wx via `chr` of `WXK_RETURN` → `"\r"` only if key maps; inconsistent across platforms | Partial/incorrect | MAJOR | — |
| 15 | Tab | Qt `\t` (+ `\x1b[Z` for Backtab) | wx `TE_PROCESS_TAB` but `EVT_CHAR` swallows `\t` into `model.key_input(" ")` path; backtab absent | Broken | MAJOR | — |
| 16 | Backspace | Qt `\x7f` (DEL) | wx via chr path yields `"\x08"` or codepoint mismatch | Wrong erase code | MAJOR | `login_widget.py:588`, wx expects 127 |
| 17 | Escape | Qt `\x1b` | wx similar but via chr fallback; may work but not proven via xterm | Fragile | MAJOR | — |
| 18 | Unicode input | Qt xterm `onData` preserves full Unicode (Türkçe, 日本語) → `send_input` UTF-8 | wx: `if key==WXK_NONE or not (32<=key<=126): key=GetKeyCode` → `chr(key)` — non-ASCII outside 32-126 replaced by keycode int → `chr` may throw or mangle; `Türkçe` chars lost | ASCII-only | CRITICAL | `wx_terminal.py:158-164` |
| 19 | Unicode output | xterm renders combining marks, CJK double-width, etc. | TextCtrl may render but via Python string only; no width handling, surrogate handling depends on wxWidgets | Lossy | MAJOR | — |
| 20 | Clipboard paste into remote shell | Qt: `clipboard.text().replace("\r\n","\n").replace("\r","\n").replace("\n","\r") → send_shell_input` | wx: `text.Paste()` writes locally into TextCtrl, never calls `send_shell_input`; multiline paste stays local, `\n` not normalized to `\r` | Paste stays local; multiline broken; remote PTY never sees data | CRITICAL | `login_widget.py:624-641`, `wx_terminal.py:151-153` |
| 21 | PTY resize | Qt: `FitAddon.fit() → terminal.cols/rows → hpcBridge.resize → ssh.resize_shell_pty` on `loadFinished`, `resizeEvent` (50 ms), `focus_terminal`, font change; 1×1 clamp | wx: `model.resize(width,height,8,18)` fixed 8×18 → `width//8 × height//18` | Fixed cell size (8x18) assumption; final cols/rows diverge from fitted xterm | CRITICAL | `terminal_widget.py:_fit`, `wx_terminal.py:46-50` |
| 22 | Resize after font changes | Qt re-fits: `hpcSetFontSize(size){terminal.options.fontSize=size; fit.fit();}` → resize | wx: `apply_font → SetPointSize` only; no `resize` or PTY update | Font change does not resize PTY | CRITICAL | `bridge.js:hpcSetFontSize`, `wx_terminal.py:105-112` |
| 23 | Reconnect behavior | Qt: `_begin_connect_async` → `terminal_widget.detach()` pre-connect, `on_session_changed` attach new ssh, `_pending_old_ssh` cleanup, generation-aware, `status_label` → Connecting/Connected | wx: `set_ssh(new_ssh)` re-subscribes but does not detach old channel atomically; old subscriber may remain if `_wx_output_subscribers` list object replaced by ssh implementation; generation absent | Stale-session output may leak; reconnect not proven | CRITICAL | `login_widget.py:680-813`, `wx_terminal.py:224-248` |
| 24 | Output subscription lifecycle | Qt: `bridge.output → terminal.write`, lifecycle via `attach/detach` emits `open/closed`, `receive_output` guarded `if text:` | wx: `ssh._wx_output_subscribers.append(CallAfter(render_output))`, no `output` signal, `render_output` discards `\r`/ESC, unsubscription via `list.remove` only if same object identity; destroy→CallAfter may target destroyed wx.TextCtrl | Callbacks into destroyed controls possible; stale output possible | CRITICAL | `wx_terminal.py:186-193,210-222,260` |
| 25 | Embedded terminal | Qt: `TerminalWidget` inside `LoginWidget` right pane, no detached frame | wx: `build_terminal_panel(notebook, ssh)` tab `help.section_terminal` (wx-only deviation; Qt has no notebook Terminal tab) — structural mismatch documented in `WX_MIGRATION_WAVE_STATUS.md:11` | Deviation (wx notebook terminal is extra tab, not in Qt) | MAJOR | `wx_shell.py:186-193`, `login_widget.py:342` |
| 26 | Detached terminal | Qt: none (commit `da44f639` has no `show_terminal` host; detached popout not in Qt reference) | wx: `show_terminal(parent, ssh)` creates `wx.Frame` wrapping same panel, but still TextCtrl; `EVT_CLOSE → Destroy` with lifecycle double-register | Both renderers must be xterm; currently both TextCtrl → non-parity | CRITICAL | `wx_terminal.py:264-302` |
| 27 | Find | Qt: `terminal_widget.find_text → QWebEnginePage.findText` searches rendered xterm buffer including scrollback, sequential Find Next advances, visible highlight | wx: `model.find(query) → TextCtrl SetSelection+ShowPosition` on `model.text` Python string, no xterm search addon; scrollback truncated by `splitlines`→join rebuild; repeated Find via button only re-selects first match | Search against stale Python string, not xterm buffer; next-match not implemented | MAJOR | `terminal_widget.py:find_text`, `wx_terminal.py:114-124` |
| 28 | Clear | Qt: `window.hpcClear → terminal.clear()` clears viewport+scrollback per xterm semantics | wx: `model.clear + ChangeValue("")` clears both but does not disconnect SSH nor send `clear\n` (correct: Qt also does not send remote command) — locally correct but must prove no SSH side-effect | Parity plausible; must prove isolation from SSH | MINOR | — |
| 29 | Connection status | Qt: `status_label` (`Disconnected`/`Connecting`/`Connected`/`Mock`) driven by `ConnectionController` + `state_changed open/closed` | wx: same header exists but status not wired to `bridge.state_changed`; `status_label` left at initial `Disconnec ted` unless shell frame updates it (shell does not update terminal header on connect) | Stale status | MAJOR | `terminal_header.py:set_status` unused in wx |
| 30 | Identity | Qt: `identity_label` (`user@host` or `SSH`/`Mock` via `ssh.info`) bold, updated on attach | wx: `identity_label` exists but `_wx_terminal_panel` never sets it from `session.ssh.info`; shell notebook page does not expose identity update helper | Wrong/fixed identity | MAJOR | — |
| 31 | Rows/columns display | Qt: `dimensions_label` (`—` → `120×40`) updated by `_sync_shell_geometry` from real `terminal.cols/rows` after each fit | wx: `dimensions_label` absent from panel layout (`wx_terminal.py` toolbar has Find/Clear/A-/A+ but no dimensions label; shell embeds no dimensions anywhere terminal-adjacent). `model.resize` returns size but never displayed | No dimensions display | MAJOR | `terminal_header.py:dimensions_label`, `wx_terminal.py:82-89` missing |
| 32 | Accessibility | Qt: `setAccessibleName(t("login.terminal_accessible_name"))`, `StrongFocus`, `find` keyboard reachable via dialog, status not by color alone | wx: no `SetName`/`AccessibleName` on TextCtrl, `text.SetFocus()` only; toolbar buttons have tooltips but header not focusable via `Tab`, terminal may trap focus | Inaccessible | MAJOR | — |
| 33 | Performance | Qt: batched `terminal.write` per output signal; `scrollback` bound 2000, no full-text rebuild per fragment | wx: `model.receive + "\n".join(text.splitlines()[-5000:])` + `ChangeValue(entire text)` on every fragment → O(N) per output, rebuilds entire 5000-line buffer each time | Unbounded per-fragment cost | MAJOR | `wx_terminal.py:143-146` |

---

## 5. What wx Tests Claim Today (and Why They Do Not Prove Parity)

- `tests/test_wx_terminal.py:2` — unit test for `TerminalModel.key_input/resize/find/clear/font` — exercises Python model, never touches a renderer or SSH adapter.
- `tests/test_wx_embedded_terminal.py:9` — uses real `wx.Panel` + `wx.TextCtrl`, asserts `GetValue`, `GetSelection`, `GetFont().GetPointSize` — proves TextCtrl wiring, not VT/PTY par ity. Accepts fixed 8×18 geometry as correct.
- `tests/test_terminal_bridge.py` — Qt `TerminalBridge` unit test; wx never uses this class.
- `tests/test_terminal_assets.py` — checks vendored assets exist and page has no `http://`; does not check wx loads them.
- Ledger `WX_MIGRATION_WAVE_STATUS.md:22` marks Wave 45 `VERIFIED_COMPLETE` on that basis. **Verdict: overclaim.** 45 carried 11 passing tests but zero xterm-visible, zero ANSI, zero `\r` overwrite, zero alternate-screen, zero Unicode-multiline-paste→PTY, zero FitAddon→real cols/rows→PTY evidence.

`audit/PARITY_EVIDENCE_INTEGRITY_62A.md` classified Wave 45 `PROVEN` on same evidence; that classification survives only for the TextCtrl contract, not for xterm parity. This contract supersedes it for `GUI-TERM-001`.

---

## 6. Contract for Waves 73–77

Wave 72 freezes behavior without implementing renderer. Waves 73–77 must satisfy, in order:

**73 — renderer:** `wx.html2.WebView` → `src/hpc_gui/assets/terminal/wx_index.html` + `wx_bridge.js` (vendored `xterm.js/css/addon-fit.js` only, no `QWebChannel`, no CDN, `connect-src 'none'`, navigation guard, `{"type":"ready"/"input"/"resize"}` single JSON bridge, `hpcWrite/hpcClear/hpcFocus/hpcSetFontSize/hpcFit` → `terminal.write/clear/focus/fit`, bounded pending-output queue ordered flush, batched coalescing, page-loaded + xterm-initialized + bridge-ready + readiness timeout + close-before-ready safety, unavailable-backend explicit error not silent fallback).

**74 — input/geometry:** `terminal.onData → WebView JSON → wx adapter → ssh.send_shell_input` (no `chr(wx_keycode)` for special keys), full `Ctrl+A..Ctrl+_` → `\x01..\x1f`, Enter `\r`, Tab `\t`, Backspace `\x7f`, Escape `\x1b`, arrows `\x1b[A/B/C/D`, Home `\x1b[H`, End `\x1b[F`, Delete `\x1b[3~`, Insert `\x1b[2~`, PageUp `\x1b[5~`, PageDown `\x1b[6~`; shell history via disposable PTY fixture (A then B, Up→B, Up→A, Down forward); multiline paste `clipboard → xterm → onData → send_shell_input` (no local Paste, no logging), Unicode `Türkçe/çğıöşü/日本語` input+output no ASCII clamp, PTY geometry `WebView resize → FitAddon.fit() → terminal.cols/rows → resize_shell_pty` removing fixed 8×18, font change re-fits, debounced resize final-value invariant, destroyed-terminal receives no resize.

**75 — chrome/lifecycle:** header `Connected/Disconnected`, `user@host`, `cols×rows` from real xterm before display (not fabricated), updated on disconnected/connecting/connected/reconnecting/session replacement/detach; Find against xterm buffer (Find, Find next, repeated advance, scrollback visible, `F3/Shift+F3` if contract-matched, local search addon vendored if needed, no CDN); Clear only presentation/scrollback, not SSH disconnect nor remote `clear\n`; bounded monospace font stack, every font change re-fits; embedded + detached share same WebView renderer (no mixed TextCtrl); reconnect invariant `SSH A attached → reconnect → SSH A removed → SSH B attached once` with `active subscribers==1` after N reconnects, old session output dropped; destruction cleans subscribers/language timers/callbacks/pending/resize; i18n `EN→TR→EN` live with no raw `[key]`; a11y name/focus/toolbar names/status not by color alone/find reachable/no trap.

**76 — execution evidence:** gate for `GUI-TERM-001=COVERED` / `VERIFIED_COMPLETE`. Required chain `real wx event → WebView/xterm → production adapter → production SSH adapter boundary → disposable fake/loopback PTY → output → adapter → real xterm renderer → verifiable rendered state`. Deterministic VT fixture exercises SGR (normal/color/bold/reset not literally displayed), `\r` progress overwrite, cursor move overwrite, erase line/screen, alternate screen (enter→alt content→leave→primary restored), shell execution/history/Ctrl-C/Ctrl-D/navigation, Unicode round-trip, multiline paste, resize font Find/Clear via real wx controls; stress 500 inputs/500 resizes/100 reconnects/repeated font/find/clear/embedded-detached/large burst/close-while-in-flight with invariants `duplicate subscribers==0`, `callbacks into destroyed==0`, `stale output==0`, `unbounded accumulation==0`; performance: no rebuild-entire-terminal per fragment, measured size/runtime recorded.

**77 — platform/packaging:** packaged artifact `wx_index.html/wx_bridge.js/xterm.js/xterm.css/addon-fit.js` (+ local addons) present, not loaded from checkout; offline (network disabled) still starts; no CDN/external script/navigation/fetch; keystrokes/paste/screen not logged/diagnostic-exported unless privacy contract allows; per-platform independent `Windows: VERIFIED / macOS: BLOCKED / Linux: BLOCKED` (do not invent), WebView2/Edge and GTK/WebKit requirements documented accurately after real packaged launch `wx runtime → terminal → ready → input/output → resize → close clean`.

---

## 7. Ledger Correction (Wave 72 Gate)

- `WX_MIGRATION_WAVE_STATUS.md:22` Wave 45 `VERIFIED_COMPLETE` → **PARTIAL** (xterm renderer absent; header dimensions missing; input/geometry not xterm-driven; paste not remote; gaps #1-7,13,20-23,31).
- `V2_PARITY_STATUS.md:17` `GUI-TERM-001` `COVERED` → **PARTIAL** (audited above; retains `GUI-TERM-002` COVERED independently where proven via `test_wx_term002`).
- `audit/PARITY_EVIDENCE_INTEGRITY_62A.md:20-21` `GUI-TERM-001/002` `PROVEN` → `GUI-TERM-001: **PARTIAL** — TextCtrl chain PROVEN, xterm chain MISSING; GUI-TERM-002: PROVEN (editor/file → terminal dispatch)` with downgrade note referencing this contract.
- This contract is the authoritative behavioral truth for Wave 73+ implementation and Wave 76 gating. No next-wave `VERIFIED_COMPLETE` may be claimed before measured evidence is reproduced against this contract.

---

## 8. Verification Performed (Wave 72)

- Branch/HEAD/working-tree inspected via `git branch --show-current`, `git rev-parse HEAD`, `git status --porcelain` (see header).
- Read: `docs/v2/WX_MIGRATION_WAVE_STATUS.md`, `V2_PARITY_STATUS.md`, `GUI_FEATURE_PARITY_BASELINE.md`, `GUI_KEYBOARD_INTERACTION_CONTRACT.md`, `audit/PARITY_EVIDENCE_INTEGRITY_62A.md` + newer `GUI_CONN_001_004_EXECUTION_EVIDENCE.md` etc.
- Inspected: `src/hpc_gui/wx_terminal.py:1-305`, `wx_shell.py:186-193`, `ui/widgets/terminal_widget.py`, `terminal_header.py`, `terminal_input.py`, `services/terminal_bridge.py`, `assets/terminal/index.html/bridge.js/xterm.js/xterm.css/addon-fit.js`, `ssh/shell_session.py`, `ssh/client.py`, `runtime.py`, `i18n/en+tr.json`, `tests/test_wx_terminal.py/test_wx_embedded_terminal.py/test_terminal_bridge.py`.
- Confirmed: `quick_command_row.setVisible(False)` → hidden/dead; wx embedded terminal is notebook tab `help.section_terminal` (Qt deviation); wx has no dimensions label; `splitlines()` destroys `\r`/ESC; `8x18` hardcode; paste local-only; Ctrl only C/D/Z; Unicode ASCII-clamped.
- Updated ledger and JSON gaps produced; no renderer changed; `git diff --check` clean; `ruff` clean on touched docs; commit gate `docs: rebaseline wx terminal parity`.

---

*Wave 72 succeeds when baseline is accurate and there are no false parity claims — no renderer change, no GUI-TERM-001 COVERED.*
