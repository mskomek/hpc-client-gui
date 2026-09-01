"""Provider-declared, non-blocking storage policy guidance."""

from __future__ import annotations

import posixpath
from dataclasses import dataclass
from collections.abc import Mapping


@dataclass(frozen=True)
class StoragePolicyWarning:
    path_kind: str
    path: str
    storage_id: str
    messages: tuple[str, ...]


class StoragePolicyEvaluator:
    def __init__(self, provider: Mapping | None):
        storage = provider.get("storage", ()) if isinstance(provider, Mapping) else ()
        self._areas = tuple(area for area in storage if isinstance(area, Mapping) and area.get("enabled", True) is not False)

    def evaluate(self, paths: Mapping[str, str | None]) -> tuple[StoragePolicyWarning, ...]:
        results = []
        for path_kind, path in paths.items():
            if not path:
                continue
            area = self._match(str(path))
            if area is None:
                continue
            policy = area.get("policy") if isinstance(area.get("policy"), Mapping) else {}
            messages = []
            if policy.get("backup") is False:
                messages.append("Not backed up")
            if policy.get("retention_days") is not None:
                messages.append(f"Retention: {policy['retention_days']} days")
            if policy.get("cleanup_note"):
                messages.append(f"Cleanup: {policy['cleanup_note']}")
            if messages:
                results.append(StoragePolicyWarning(path_kind, str(path), str(area.get("id") or ""), tuple(messages)))
        return tuple(results)

    def _match(self, path: str):
        if not path.startswith("/"):
            return None
        candidate = posixpath.normpath(path)
        matches = []
        for area in self._areas:
            root = str(area.get("path_template") or "").strip()
            if not root.startswith("/"):
                continue
            root = posixpath.normpath(root)
            try:
                if posixpath.commonpath((candidate, root)) == root:
                    matches.append((len(root), area))
            except ValueError:
                continue
        return max(matches, key=lambda item: item[0])[1] if matches else None
