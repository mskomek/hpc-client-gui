## v1.1.17
- Connections: each saved connection now has its own "Allow this connection
  to be used from the CLI" checkbox (off by default for both new and
  existing connections). The CLI refuses `--profile NAME` for a profile
  with the checkbox unchecked, even when the global external CLI access
  toggle is enabled.
- Connections: editing a saved connection that has a stored password
  (Windows-credential-protected or master-password-encrypted) now always
  requires re-entering/validating that password before the edit dialog
  opens, regardless of the connection's password-prompt policy.
