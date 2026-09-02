# User Data and Keymap Migration

The wx path reuses the existing profile, credential, known-host, plugin, and
history stores. It does not move or re-encrypt credentials. Qt-only renderer
settings are ignored by wx and remain available to the Qt runtime.

Existing installations may choose `standard` (native platform bindings) or
`legacy` (the prior Ctrl-based bindings) once. New installations default to
`standard`. The choice is stored beside the existing versioned shortcut
bindings; migration is additive and preserves the original binding payload.

Migration must be tested with a disposable copy of user data. Before any
write, create the normal settings backup/rollback point; failed migration must
leave the original file readable. Never include secrets or private-key content
in migration logs.
