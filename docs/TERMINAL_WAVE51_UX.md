# Terminal Wave51 UX verification

- The embedded terminal is the primary first-page shell surface.
- The legacy Quick Command row remains available to existing programmatic
  callers but is hidden by default; no Run bar is shown in the connected layout.
- Connection state, safe `user@host`/Mock identity, SSH label, and terminal
  dimensions are outside the xterm scrollback.
- Find, clear, and font size controls operate on the local terminal view.
- Focus requested during connection is applied after the local page becomes
  ready.
- New control labels and tooltips exist in both English and Turkish resources.
- Windows smoke: LoginWidget created, Quick Command hidden, terminal primary,
  and all terminal controls enabled.

The broad TUI compatibility matrix and packaged CI gate remain Wave52 scope.
