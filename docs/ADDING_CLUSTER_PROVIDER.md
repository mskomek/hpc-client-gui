# Adding a cluster provider

Cluster providers are declarative plugins maintained in the
[HPC Client GUI plugin registry](https://github.com/mskomek/hpc-client-gui-plugins).
They describe public site defaults such as Slurm guidance and storage paths;
they do not install software on a cluster or contain credentials.

Providers declare supported Slurm intent and metadata; they cannot introduce
arbitrary remote shell operations. The application owns accepted scheduler
commands and shell-quotes substituted values. Provider-specific status behavior
requires an application allowlisted adapter; unknown legacy commands fail closed.

Use the plugin repository's [complete provider tutorial](https://github.com/mskomek/hpc-client-gui-plugins/blob/main/docs/ADDING_CLUSTER_PROVIDER.md)
for scaffolding, schema fields, storage, optional quota, packaging, hashes,
validation, and pull requests.

Unknown values may remain blank. In particular, a provider can describe Home,
Scratch, Project, Slurm, and public documentation while leaving quota disabled.
A missing or disabled quota definition performs no quota request, probing,
timer, retry, `df`, `du`, or `find` fallback. Do not copy quota commands from
another site.
If you want support added but do not want to prepare the profile yourself, use
the plugin repository's [request form](https://github.com/mskomek/hpc-client-gui-plugins/issues/new?template=plugin-request.yml).
