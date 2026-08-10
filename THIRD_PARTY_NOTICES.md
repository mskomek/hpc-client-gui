# Third-Party Notices

HPC Client GUI is licensed under the PolyForm Noncommercial License 1.0.0.
This application also bundles third-party runtime dependencies, each of which
is distributed under its own license.

## Bundled runtime dependencies

| Component | License | Notes |
| --- | --- | --- |
| PySide6 | LGPLv3 | Qt for Python bindings |
| shiboken6 | LGPLv3 | CPython bindings generator for Qt (runtime support for PySide6) |
| paramiko | LGPL-2.1+ | SSHv2 protocol implementation |
| cryptography | Apache-2.0 / BSD | Cryptographic primitives used by paramiko |

`cryptography`'s license texts (Apache-2.0, with additional terms under the
BSD 3-Clause License) ship inside the packaged application's `_internal`
directory as part of its wheel distribution metadata.

PySide6, shiboken6, and paramiko license texts are not currently bundled in
the packaged application's `_internal` directory; adding their dist-info or
license text to the PyInstaller `datas` list is tracked as follow-up
packaging work. Until then, obtain their license texts from their respective
projects: PySide6/shiboken6 from the Qt for Python project, and paramiko from
its project repository.

## License texts

The `LICENSE`, `COMMERCIAL_LICENSE.md`, and this notices file ship alongside
the packaged application. If you receive a copy of this software without
them, you may obtain them from the project's source repository.
