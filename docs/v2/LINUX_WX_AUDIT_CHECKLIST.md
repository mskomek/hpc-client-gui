# Linux wx Audit Checklist

Automated coverage verifies that the optional wx runtime removes legacy
`QTWEBENGINE_*` graphics variables while leaving the saved settings file
untouched. Qt WebEngine is not a dependency of the wx path.

Manual release smoke:

- GTK/wx on X11 and Wayland; test 100/150/200% scaling and a missing display.
- Native file dialogs, clipboard, file drag-and-drop, menus, focus order,
  tray shutdown, terminal copy/Ctrl+C, PTY resize, and system OpenSSH X11.
- Verify wheel/AppImage/DEB/Flatpak resource discovery and declarative plugin
  loading; run transfer and the allowlisted ANSYS Trusted Tool lint flow.
- Verify updater cancellation/rollback and that no VcXsrv/plink workaround is
  required on Linux.

Known limits: Wayland clipboard/DnD and tray behavior depend on the desktop
portal/shell; X11 forwarding still depends on OpenSSH, xauth, and the remote
display. Missing optional components remain reported as unavailable.

No passwords, private keys, environment dumps, or remote paths belong in this
audit output.
