# macOS wx Audit Checklist

Automated coverage verifies the native Command shortcut map, Keychain/XQuartz
adapters, and separate Apple Silicon/Intel DMG asset names. The wx path keeps
the existing Keychain and system OpenSSH X11 services; it does not introduce a
mechanical Ctrl-to-Cmd rewrite.

Manual release smoke:

- Apple Silicon and Intel DMGs: launch, resource/plugin discovery, settings
  migration, updater cancel/rollback, and signed/notarized verification.
- Native menu bar, Settings placement, dialogs, focus order, clipboard/DnD,
  status/tray shutdown, terminal Cmd+C/Cmd+V, and PTY resize.
- XQuartz presence, `/opt/X11/bin/xauth`, system OpenSSH X11, transfer smoke,
  and the allowlisted ANSYS Trusted Tool lint flow.

Known limits: Keychain and XQuartz require macOS host services; X11 remains
optional and password-only X11 is rejected. Packaged DMG and ANSYS checks are
host-only and are documented here rather than faked on Windows CI.

Audit output must not include passwords, private keys, environment dumps, or
remote paths.
