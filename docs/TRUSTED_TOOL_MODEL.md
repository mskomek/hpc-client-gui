# Trusted Tool Model

Cluster provider plugins are declarative and data-only. They provide site
metadata, storage definitions, scheduler hints, and documentation; provider
packages cannot execute Python, shell hooks, binaries, or installer scripts.

ANSYS Script & Journal Lint is a separate application-owned Trusted Tool. The
application allowlist approves its exact ID, publisher, entrypoint, and API.
Registry metadata alone cannot grant executable privileges. The package still
passes the registry, manifest, file-hash, compatibility, and immutable-version
checks before its code is loaded on explicit user action.

The tool is intentionally narrow: it parses selected local content and emits
findings. It receives no SSH credentials, keyring, updater secrets, provider
registry write access, or automatic institutional-authentication capability.
Unknown executable plugins remain disabled.
