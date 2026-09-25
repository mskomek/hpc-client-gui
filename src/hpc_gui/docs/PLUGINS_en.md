# Plugins

HPC Client GUI supports **declarative plugins**: small, downloadable
packages that provide cluster profiles, job templates, and lint rules.
Plugin API v1 distributes data only — no Python code, scripts, or binaries
are ever downloaded or executed by the plugin system.

## Opening the Plugin Manager

The menubar **Plugins** menu opens the Plugin Manager with three tabs:

- **Browse & Install...** opens the **Discover** tab — browse the official
  registry catalog. Loading starts automatically when the manager opens
  (status shows *Loading plugins…*, then *Online*, *Cached*, or *Offline*);
  Refresh re-checks manually.
- **Manage Installed...** opens the **Installed** tab — see installed
  versions, enable/disable, or remove plugins.
- **Check for Plugin Updates...** opens the **Updates** tab — compatible
  newer versions appear here; updating is always your explicit choice
  (no auto-update).

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

## Installed versions, rollback, and local integrity

The *Installed* tab shows the actually active version and lists every
installed version in version order (1.10 is newer than 1.9). Selecting a
version offers **Activate** (newer) or **Roll back** (older) after an
explicit confirmation. Rollback never deletes installed versions, keeps your
enabled/disabled choice independent of versions, and automatically restores
the previous active version if validation fails.

On every load and activation the app re-verifies installed files locally:
the manifest must match the hash recorded at install time, all declared
files are checked for size and SHA-256, and unexpected extra files are
rejected. A plugin that fails is skipped with a reinstall hint — never
deleted — while healthy plugins keep loading. Installs made before this
record keeping existed are migrated once by verifying against their current
manifest; that one-time migration cannot detect changes that happened
between installation and migration.

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

You can also configure structured **Storage Areas** directly on a new Generic
Slurm connection; a provider plugin is not required. Home, Scratch, Project,
Custom, and Node local areas can carry passive path and policy metadata. Local
profiles have no plugin provenance, and their structured data is saved only in
the connection or user system template. Quota remains optional: the GUI only
uses reviewed application-owned backends, and a local profile cannot define a
quota command, parser, hook, or executable provider content. With no supported
backend, storage still works and quota performs no remote work.

## Provider authoring: text, paths, and optional metadata

Provider JSON is UTF-8. All manifest, profile, label, description, and path
values are textual `str` values inside the application; use names such as
`Çalışmalar_日本語` directly. `bytes` belongs only at an I/O or integrity
boundary (for example, downloading a payload or calculating its SHA-256).
Do not decode and re-encode a path through Latin-1, the Windows code page, or
an `errors="ignore"`/`errors="replace"` conversion.

Remote paths are data, not shell fragments. Keep them in `paths` or
`storage[].path_template` and use the documented `{user}`, `{project}`, and
`{account}` placeholders. The application resolves the placeholders and owns
quoting for scheduler commands. Provider data must not add `shell`, `exec`,
`callback`, or arbitrary command fields; only the application's allow-listed
Slurm templates are accepted.

`storage` is passive display/policy metadata. `quota_sources` is optional:
omit it or leave it empty when the site has no reviewed quota source. A
missing quota definition performs no quota request, probe, retry, `df`, `du`,
or `find` fallback. Never invent quota values or copy a command from another
site. Labels may be localized with `en` and `tr` values.

Minimal Unicode profile example:

```json
{
  "schema_version": 2,
  "profile_id": "example_unicode",
  "name": "Çalışma Kümesi 日本語",
  "scheduler": "slurm",
  "paths": {
    "home_dir": "/home/{user}",
    "scratch_dir": "/scratch/{user}/Çalışmalar_日本語"
  },
  "storage": [
    {
      "id": "scratch",
      "label": "Scratch / Çalışmalar 日本語",
      "kind": "scratch",
      "path_template": "/scratch/{user}/Çalışmalar_日本語",
      "access_context": "shared"
    }
  ]
}
```

## Plugin manifest authoring

Every plugin version ships a `manifest.json` that the loader validates
before anything else. Required keys (`schema_version`, `plugin_api`, `id`,
`name`, `version`, `publisher`, `license`, `description`, `requires_app`,
`capabilities`, `entrypoints`, `files`):

- `schema_version` is `1`.
- `plugin_api` is `1` (data-only plugins). The numeric marker `2` is
  accepted only for application-approved trusted tools and never grants
  code execution by itself.
- `id` is a dotted reverse-DNS identity such as `org.hpcclient.truba`
  (lowercase, segments separated by dots). Free-form display names are
  rejected: two plugins must never silently shadow each other.
- `name` is the human label (at most 128 characters); `version` is a
  semantic version (`1.0.0`); `requires_app` is the compatible app range
  (for example `>=1.3.0`) and incompatible plugins are reported with a
  clear rejected status instead of loading.
- `capabilities` names what the plugin provides: `cluster-profile`,
  `lint-rules`, `job-template`, `application-tools`, `linter-tool`.
- `entrypoints` maps each capability to its declarative payload path
  (for example `{"cluster_profiles": ["cluster-profile.json"]}`). Paths
  are relative, forward-slash separated, and must stay inside the package;
  they are never imported or executed.
- `files` lists every payload with its `path`, SHA-256 `sha256`, byte
  `size`, and `role`. Declared files are re-verified on every load and
  undeclared extra files are rejected.

Optional advisory keys (`provider_ids`, `optional_dependencies`) document
intent but never grant loading, execution, or capability by themselves:

- `provider_ids` lists provider ids the plugin documents (for example
  `["truba"]`). A plugin registers a provider only through its
  `cluster-profile` payload and capability declaration, never through
  this list alone.
- `optional_dependencies` lists ids (or `{"id", "version"}` objects) the
  plugin was tested with. A missing or invalid optional dependency is
  reported as a diagnostic; the declaring plugin still loads normally and
  host startup is never blocked.

Any malformed manifest, incompatible API marker, or failed integrity check
is recorded as a contained diagnostic naming `plugin_id@version` and only
that plugin version is skipped — unrelated plugins and the core app always
finish loading.

## Job templates and lint

Plugins can deliver job script templates (*New from Template...* in the
editor) and declarative lint rule packs (the editor's *Lint* action).
Templates render by plain placeholder substitution, always open in an
unsaved tab for review, and nothing runs until you explicitly save/submit.

See [PLUGINS_tr.md](PLUGINS_tr.md) for the Turkish version.

For provider authoring, use the authoritative
[English guide in the plugin repository](https://github.com/mskomek/hpc-client-gui-plugins/blob/main/docs/ADDING_CLUSTER_PROVIDER.md).
The [plugin request form](https://github.com/mskomek/hpc-client-gui-plugins/issues/new?template=plugin-request.yml)
is available if you want to request a provider without authoring its profile.

## Trusted tools

ANSYS Lint is a separately reviewed **Trusted Tool**, not a generic
executable plugin. Its identity is application-approved and its code is
loaded only after the usual manifest/file hash checks.
Nothing runs at install time - the engine loads only when you open it,
and every byte is pinned by SHA-256 exactly like declarative data.

The current tool is **ANSYS Script & Journal Linter**
(`org.hpcclient.ansyslint`). It is an *unofficial* offline checker for
Ansys journals and scripts: Fluent journals (TUI/Scheme), Workbench
`.wbjn` files including nested `SendCommand` payloads, Mechanical APDL
inputs, CFX/CFD-Post/TurboGrid CCL sessions and states, ICEM replay
scripts, System Coupling scripts, plus structural detection for
DesignModeler, Mechanical, SpaceClaim/Discovery, Electronics Desktop and
Motion files.

Once its registry package is published and installed, its card on the
**Installed** tab gains an
**Open tool** button. The page offers file/folder selection, automatic
product detection with manual override, an Ansys version selector
(24.2 / 25.1 / 25.2 / 26.1), batch/headless/interactive mode, Linux/Windows
portability targets, severity filters, per-diagnostic official source
links, and JSON/text export. The same engine provides a CLI in the plugin
repository checkout (`scripts/ansys-journal-lint.py`).

It is not affiliated with or endorsed by ANSYS, Inc., does not replace the
official documentation, and labels heuristic findings explicitly -
verify scripts against your installed release.
