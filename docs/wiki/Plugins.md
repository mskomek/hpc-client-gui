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

Plugin API v1 plugins contain declarative data only: no Python, no scripts,
no binaries are downloaded or executed. Every file is SHA-256-verified before
activation, installs happen only on your desktop (nothing is installed on the
cluster), and saved connection profiles are never silently rewritten — they
keep their copied settings snapshot. Plugins can be disabled or removed at
any time from the *Installed* tab.

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
