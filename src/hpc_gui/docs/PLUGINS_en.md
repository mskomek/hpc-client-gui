# Plugins

HPC Client GUI supports **declarative plugins**: small, downloadable
packages that provide cluster profiles, job templates, and lint rules.
Plugin API v1 distributes data only — no Python code, scripts, or binaries
are ever downloaded or executed by the plugin system.

## The Plugins button

The top-right control strip contains a **Plugins** button (between Update
and Send Logs). It opens the Plugin Manager with three tabs:

- **Discover** — browse the official registry catalog.
- **Installed** — see installed versions, enable/disable, or remove plugins.
- **Updates** — compatible newer versions appear here; updating is always
  your explicit choice (no auto-update).

## Official registry and offline behavior

Plugins come from exactly one official registry:

`https://raw.githubusercontent.com/mskomek/hpc-client-gui-plugins`

Installation downloads **only the files declared for the selected plugin
version**, verifies every byte against SHA-256 hashes recorded in the
registry, and activates atomically. If the network is unavailable, the last
known-good registry catalog is shown as **Cached**; without any cache the
manager shows an **Offline** state and the app keeps working normally.

## Security model

- Installing never executes plugin content.
- Every manifest and payload file is hash-verified before activation.
- A failed or tampered install leaves previous state untouched; failed
  updates automatically roll back to the previously active version.
- Only the official registry is supported in v1; custom registry URLs are
  not exposed.

## Cluster profiles and System Templates

The built-in connection dialog ships with a generic **Generic Slurm**
template. Installing the TRUBA plugin adds a TRUBA entry under
*System Templates → Installed Plugins*. Applying it fills the site paths
and scheduler commands; you can edit everything afterwards.

Saved connections keep their own copied settings snapshot, so removing or
updating a plugin never changes existing connections. *Get more plugins...*
at the bottom of the template menu opens the Plugin Manager.

## Job templates and lint

Plugins can deliver job script templates (*New from Template...* in the
editor) and declarative lint rule packs (the editor's *Lint* action).
Templates render by plain placeholder substitution, always open in an
unsaved tab for review, and nothing runs until you explicitly save/submit.

See [PLUGINS_tr.md](PLUGINS_tr.md) for the Turkish version.
