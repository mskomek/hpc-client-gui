# Plugins

HPC Client GUI supports **declarative plugins**: small, downloadable
packages that provide cluster profiles, job templates, and lint rules.
Plugin API v1 distributes data only — no Python code, scripts, or binaries
are ever downloaded or executed by the plugin system.

## The Plugins button

The top-right control strip contains a **Plugins** button (between Update
and Send Logs). It opens the Plugin Manager with three tabs:

- **Discover** — browse the official registry catalog. Loading starts
  automatically when the manager opens (status shows *Loading plugins…*,
  then *Online*, *Cached*, or *Offline*); Refresh re-checks manually.
- **Installed** — see installed versions, enable/disable, or remove plugins.
- **Updates** — compatible newer versions appear here; updating is always
  your explicit choice (no auto-update).

Each Discover card shows the plugin name and version, publisher, a short
description, translated capability badges (*Cluster profiles*, *Job
templates*, *Lint rules*), whether it is compatible with your running app
version, and its current state: installed, disabled, incompatible, or update
available. **Details** opens the full record: ID, publisher, version,
license, compatible app range, capabilities, description, older versions,
installed state, and the source (*Official plugin registry*).

Missing something? Use **Request a plugin** in the Plugin Manager header.
It opens the dedicated issue form in the plugin registry repository:

[Request a plugin](https://github.com/mskomek/hpc-client-gui-plugins/issues/new?template=plugin-request.yml)

Good requests include support for another HPC center, a new Slurm cluster
profile, PBS/other scheduler profiles for future consideration, ANSYS Fluent
or OpenFOAM templates, journal/job-script lint rules, and
institution-specific paths or queues. Application bugs stay in
[hpc-client-gui](https://github.com/mskomek/hpc-client-gui/issues/new/choose);
plugin requests and plugin content corrections belong in
[hpc-client-gui-plugins](https://github.com/mskomek/hpc-client-gui-plugins/issues/new/choose).

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
- Published plugin versions are immutable on disk: reinstalling an identical,
  verified version is idempotent, and conflicting same-version content is
  reported instead of overwritten.
- Only the official registry is supported in v1; custom registry URLs are
  not exposed.
- Plugins never silently rewrite previously saved connection profiles: saved
  profiles keep their copied settings snapshot.

## Transfers and parallelism (related setting)

The connection dialog's *Advanced → Maximum simultaneous transfers* controls
how many files upload/download concurrently. The **configured** value is per
profile; the transfer dialog also shows the **effective** limit for the
current connection, which can be lower depending on backend capability or
server limits. Multiple files may transfer concurrently; a single large file
is not currently segmented into parallel parts.

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

## Linter tools (Plugin API v2)

Starting with this release, the official registry can also publish
**linter tools**: optional plugins that ship a hash-verified, pure-Python
analysis engine inside the usual manifest/installer verification chain.
Nothing runs at install time - the engine loads only when you open it,
and every byte is pinned by SHA-256 exactly like declarative data.

The first linter tool is **ANSYS Script & Journal Linter**
(`org.hpcclient.ansyslint`). It is an *unofficial* offline checker for
Ansys journals and scripts: Fluent journals (TUI/Scheme), Workbench
`.wbjn` files including nested `SendCommand` payloads, Mechanical APDL
inputs, CFX/CFD-Post/TurboGrid CCL sessions and states, ICEM replay
scripts, System Coupling scripts, plus structural detection for
DesignModeler, Mechanical, SpaceClaim/Discovery, Electronics Desktop and
Motion files.

After installing it, its card on the **Installed** tab gains an
**Open tool** button. The page offers file/folder selection, automatic
product detection with manual override, an Ansys version selector
(24.2 / 25.1 / 25.2 / 26.1), batch/headless/interactive mode, Linux/Windows
portability targets, severity filters, per-diagnostic official source
links, and JSON/text export. The same engine provides a CLI in the plugin
repository checkout (`scripts/ansys-journal-lint.py`).

It is not affiliated with or endorsed by ANSYS, Inc., does not replace the
official documentation, and labels heuristic findings explicitly -
verify scripts against your installed release.
