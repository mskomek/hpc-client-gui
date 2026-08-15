# Architecture

> Türkçe: [[Architecture-TR]]

A summary of `src/hpc_gui/docs/ARCHITECTURE.md`, which is canonical.

The application is a **PySide6 desktop program** for SSH and Slurm workflows,
with optional X11 support through external helpers. Its product loop is:
start, establish or reuse a remote session, browse or edit remote content,
prepare or submit Slurm scripts, observe queue and accounting state, and
inspect diagnostics and logs.

## Layers

| Package | Owns | Does not own |
|---|---|---|
| `src/hpc_gui/ui/` | Windows, dialogs, widgets, user interaction, progress and status display | Reusable Slurm parsing, deep session logic, hidden business rules |
| `src/hpc_gui/services/` | Slurm service abstractions, remote file operations, the process registry, X11 helper orchestration, integration with PuTTY and VcXsrv | — |
| `src/hpc_gui/ssh/` | Remote client behavior and connection-level wrappers | — |
| `src/hpc_gui/config/` | Local configuration models, storage of user preferences, safe persistence helpers | — |
| `src/hpc_gui/core/` | Logging setup, i18n, diagnostics helpers, path and resource helpers | — |
| `src/hpc_gui/cli/` | The command-line surface and its exit-code contract | Behavior the services do not already expose |
| `templates/` | Starter Slurm script templates for CPU, GPU, and MPI flows | — |
| `scripts/` | Repository validation, smoke tests, packaging and release helpers | — |

## Priorities

In the order the project resolves conflicts between them:

1. Interface responsiveness
2. Explicit, inspectable remote operations
3. Reusable service and domain logic
4. Observable failures
5. i18n consistency
6. Practical packaging

## Design rules

- **Keep the Qt layer thin.** If logic can be tested outside a widget, move it
  out of the widget into a service.
- **Keep long work off the interface thread.** Session, transfer, and process
  work runs asynchronously so the window never blocks on the network.
- **Keep user-visible strings in the language layer.** Turkish and English
  resources are updated together — see
  [[Interface Language and i18n|Interface-Language-and-i18n]].
- **Keep external command execution easy to reason about.** Arguments are
  explicit and quoted rather than assembled from free-form strings.
- **Keep test seams available** for fake file and Slurm layers, as in
  `tests/test_editor_flow.py`. This is why the offline suite can exercise
  transfer and job flows without a cluster — see
  [[Testing and CI|Testing-and-CI]].

## Why the interface never blocks

Every remote operation — connecting, listing a directory, transferring a file,
querying the scheduler — can take arbitrarily long or fail. Running any of it
on the interface thread would freeze the window. The services layer exists
partly so that this work has somewhere to live that is not a widget, and
failures surface as logged, observable events rather than as a hung interface.

## See also

[[Building from Source|Building-from-Source]] ·
[[Testing and CI|Testing-and-CI]] ·
[[Contributing|Contributing]]
