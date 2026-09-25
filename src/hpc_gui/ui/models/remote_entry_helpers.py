"""Pure presentation helpers shared by the remote directory views.

These functions must stay Qt-free so they can be unit tested headless.

W44 (ARCH-QT-WX-002): the implementation lives in the framework-neutral
``hpc_gui.services.remote_entry_format`` so the wx runtime can consume it
without importing ``hpc_gui.ui.*``. This module re-exports the same names
for the Qt surface and existing tests.
"""

from __future__ import annotations

from hpc_gui.services.remote_entry_format import (
    category,
    file_type,
    fmt_mtime,
    fmt_size,
    natural_sort_key,
)

__all__ = ["category", "file_type", "fmt_mtime", "fmt_size", "natural_sort_key"]
