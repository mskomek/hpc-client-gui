# Plugins

HPC Client GUI supports **declarative plugins** from one official registry.
Open the Plugin Manager with the **Plugins** button in the top-right control
strip; loading starts automatically (status: *Loading plugins…*, then
*Online*, *Cached*, or *Offline*).

## What plugins provide

- **Cluster profiles** — site paths and scheduler commands under
  *Connection Profile → System Templates → Installed Plugins*.
- **Slurm / solver job templates** — used via *New from Template...* in the editor.
- **Lint rule packs** — applied by the editor's *Lint* action.

Provider plugins contain declarative data only: no Python, no scripts,
no binaries are downloaded or executed. ANSYS Lint is a separately reviewed,
application-approved Trusted Tool. Every file is SHA-256-verified before
activation, installs happen only on your desktop (nothing is installed on the
cluster), and saved connection profiles are never silently rewritten - they
keep their copied settings snapshot. Plugins can be disabled or removed at
any time from the *Installed* tab.

Unknown executable packages remain disabled. Only the application-approved
ANSYS Trusted Tool can be imported, after identity and integrity checks.

## Installed versions: Activate and Roll back

When a plugin has more than one installed version, the *Installed* tab shows
a version list. The headline version is always the one that is actually
active, and versions are ordered by version number (1.10 is newer than 1.9).
Pick a version and confirm to **Activate** a newer one or **Roll back** to an
older one:

- Rollback never deletes any installed version.
- The plugin's enabled/disabled state is independent of the chosen version.
- If activation fails validation, the previously active version stays active.
- Version switching runs in the background; the UI stays responsive.

## Local integrity re-checks

Every time a plugin version is loaded or activated, the app re-verifies it
locally: the manifest must match the SHA-256 recorded at install time, all
declared files must have the exact size and hash, and unexpected extra files
inside the plugin folder are rejected. A plugin that fails these checks is
skipped with a clear reinstall message - it is never deleted automatically,
other plugins keep working, and you can roll back manually to an older
version that still verifies.

Older installations made before this record keeping existed are migrated once:
their files are verified against their current manifest and only then is that
hash trusted as the starting point. Note that this one-time migration cannot
detect changes that happened between installation and migration.

## Requesting a plugin

Missing a cluster profile, solver template, or lint pack? Use **Request a
plugin** in the Plugin Manager header, or open the request form directly:

[Request a plugin](https://github.com/mskomek/hpc-client-gui-plugins/issues/new?template=plugin-request.yml)

Issue routing:

- Application bugs (SSH/SFTP/FTP, UI, crashes, releases) →
  [hpc-client-gui issues](https://github.com/mskomek/hpc-client-gui/issues/new/choose)
- Plugin requests and plugin content corrections →
  [hpc-client-gui-plugins issues](https://github.com/mskomek/hpc-client-gui-plugins/issues/new/choose)

See [PLUGINS_en.md](https://github.com/mskomek/hpc-client-gui/blob/main/src/hpc_gui/docs/PLUGINS_en.md)
for the full guide.
