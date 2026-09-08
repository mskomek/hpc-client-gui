"""Framework-neutral file filter registry with overlapping-view semantics.

Filters are *views*, not exclusive categories.  A file can match multiple
filters simultaneously.  ``Other`` means "not matched by any specialized
filter".  ``All`` includes everything.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import Any, Sequence


@dataclass(frozen=True)
class FileFilter:
    """A single file-filter definition."""

    id: str
    label_en: str
    label_tr: str = ""
    globs: tuple[str, ...] = ()
    suffixes: tuple[str, ...] = ()
    order: int = 1000
    source: str = "core"  # core | provider | plugin
    hidden: bool = False

    @property
    def label(self) -> str:
        return self.label_en


@dataclass
class FileFilterRegistry:
    """Mutable registry that holds all known file filters.

    Core filters are always present.  Provider / plugin filters are merged
    in deterministic order between the core filters and ``Other``.
    """

    _filters: list[FileFilter] = field(default_factory=list)
    _reserved: frozenset[str] = field(default_factory=lambda: frozenset({"all", "other"}))

    # -- construction --------------------------------------------------------

    def register(self, filt: FileFilter) -> None:
        """Add a filter.  Core filters with duplicate IDs are replaced."""
        if filt.id in self._reserved:
            raise ValueError(f"filter id {filt.id!r} is reserved")
        # Remove existing with same id (allows updates)
        self._filters = [f for f in self._filters if f.id != filt.id]
        self._filters.append(filt)
        self._filters.sort(key=lambda f: (f.order, f.id))

    def register_many(self, filters: Sequence[FileFilter]) -> None:
        for f in filters:
            self.register(f)

    def remove(self, filter_id: str) -> bool:
        before = len(self._filters)
        self._filters = [f for f in self._filters if f.id != filter_id]
        return len(self._filters) < before

    # -- query ---------------------------------------------------------------

    def all_filters(self, *, include_hidden: bool = False) -> list[FileFilter]:
        """Return all registered filters in display order.

        The returned list always starts with ``all`` and ends with ``other``
        as conceptual bookends; they are *not* ``FileFilter`` objects but
        their presence is implied by ``matches_all`` and ``matches_other``.
        """
        result = [f for f in self._filters if not f.hidden or include_hidden]
        return result

    def visible_filter_ids(self, *, include_hidden: bool = False) -> list[str]:
        """Return ``["all", <core...>, <provider/plugin...>, "other"]``."""
        ids = ["all"]
        for f in self.all_filters(include_hidden=include_hidden):
            ids.append(f.id)
        ids.append("other")
        return ids

    def get(self, filter_id: str) -> FileFilter | None:
        for f in self._filters:
            if f.id == filter_id:
                return f
        return None

    # -- matching ------------------------------------------------------------

    def matches(self, entry: Any, filter_id: str) -> bool:
        """Return whether *entry* should be visible under *filter_id*.

        ``entry`` is expected to have at least ``name`` (str) and
        ``is_dir`` (bool) attributes or dict keys.
        """
        if filter_id == "all":
            return True
        if filter_id == "other":
            return not self._matches_any_specialized(entry)
        filt = self.get(filter_id)
        if filt is None:
            return False
        return _matches_filter(entry, filt)

    def _matches_any_specialized(self, entry: Any) -> bool:
        for filt in self._filters:
            if filt.hidden:
                continue
            if _matches_filter(entry, filt):
                return True
        return False


# -- helper matching functions -----------------------------------------------

def _entry_name(entry: Any) -> str:
    if isinstance(entry, dict):
        return str(entry.get("name", entry.get("path", "")))
    return str(getattr(entry, "name", getattr(entry, "path", "")))


def _entry_is_dir(entry: Any) -> bool:
    if isinstance(entry, dict):
        return bool(entry.get("is_dir", entry.get("is_directory", False)))
    return bool(getattr(entry, "is_dir", getattr(entry, "is_directory", False)))


def _matches_filter(entry: Any, filt: FileFilter) -> bool:
    """Check if an entry matches a specific filter definition."""
    name = _entry_name(entry).lower()
    is_dir = _entry_is_dir(entry)

    if is_dir and filt.id == "folders":
        return True

    # Check globs
    for pattern in filt.globs:
        if fnmatch.fnmatch(name, pattern.lower()):
            return True

    # Check suffixes (case-insensitive)
    for suffix in filt.suffixes:
        if name.endswith(suffix.lower()):
            return True

    return False


# -- built-in core filters ---------------------------------------------------

CORE_FILTERS: list[FileFilter] = [
    FileFilter(
        id="folders",
        label_en="Folders",
        label_tr="Klasörler",
        order=10,
        source="core",
    ),
    FileFilter(
        id="iso",
        label_en="ISO",
        label_tr="ISO",
        globs=("*.iso",),
        order=20,
        source="core",
    ),
    FileFilter(
        id="archives",
        label_en="Archives",
        label_tr="Arşivler",
        suffixes=(".zip", ".rar", ".7z", ".tgz", ".tar.gz", ".tar"),
        order=30,
        source="core",
    ),
    FileFilter(
        id="slurm",
        label_en="Slurm",
        label_tr="Slurm",
        globs=("*.slurm", "*.sbatch"),
        order=40,
        source="core",
    ),
    FileFilter(
        id="shell",
        label_en="SH",
        label_tr="SH",
        globs=("*.sh", "*.bash"),
        order=50,
        source="core",
    ),
]


def build_core_registry() -> FileFilterRegistry:
    """Create a registry pre-populated with core filters."""
    registry = FileFilterRegistry()
    registry.register_many(CORE_FILTERS)
    return registry
