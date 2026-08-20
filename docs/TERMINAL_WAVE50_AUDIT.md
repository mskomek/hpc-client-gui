# Terminal Wave50 transport audit

| Risk | Result | Evidence |
| --- | --- | --- |
| Receive chunk decoding | Fixed | One persistent UTF-8 incremental decoder per shell session. |
| Split UTF-8 sequences | Fixed | `tests/test_ssh_terminal_stream.py` splits Turkish text and emoji at every byte boundary. |
| Partial channel sends | Fixed | `_send_shell_payload()` loops until all bytes are accepted. |
| Zero/closed send | Fixed | A zero return or exception reports failure; no truncated success. |
| PTY type | Hardened | Requests `xterm-256color`, falls back to `xterm` with a sanitized diagnostic. |
| Resize after close | Safe | Existing resize path ignores an absent channel and clamps dimensions. |
| Session decoder reset | Fixed | Decoder is recreated for each shell channel and flushed at stop/EOF. |
| Credentials/raw terminal logging | Preserved | No new payload logging; existing sanitized logging remains the fallback. |
| Backpressure | Bounded by existing layers | The SSH reader keeps fixed-size reads, does not accumulate output, and xterm owns incremental write buffering; the 20,000-line burst test preserves order. |

The selected bridge unit remains UTF-8 text after one session-scoped decode;
the JavaScript side receives ordered text and xterm remains responsible for VT
interpretation. No live SSH or cluster operation was used.
