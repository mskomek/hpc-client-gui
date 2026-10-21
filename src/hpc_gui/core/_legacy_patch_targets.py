"""Forward legacy facade monkeypatches to the leaf that owns each symbol."""

from __future__ import annotations

import sys
from importlib import import_module
from types import ModuleType
from typing import Mapping


class _LegacyPatchableModule(ModuleType):
    def __setattr__(self, name: str, value: object) -> None:
        targets = self.__dict__.get("_legacy_patch_targets", {}).get(name, ())
        if targets and name not in self.__dict__:
            originals = self.__dict__.setdefault("_legacy_patch_originals", {})
            if name not in originals:
                originals[name] = tuple(
                    getattr(import_module(module_name), target_name)
                    for module_name, target_name in targets
                )
        super().__setattr__(name, value)
        for module_name, target_name in targets:
            setattr(import_module(module_name), target_name, value)

    def __delattr__(self, name: str) -> None:
        targets = self.__dict__.get("_legacy_patch_targets", {}).get(name, ())
        super().__delattr__(name)
        originals = self.__dict__.get("_legacy_patch_originals", {})
        original_values = originals.pop(name, None)
        if original_values is None:
            return
        for (module_name, target_name), original in zip(targets, original_values):
            setattr(import_module(module_name), target_name, original)


def enable_legacy_patch_targets(
    module_name: str,
    targets: Mapping[str, tuple[tuple[str, str], ...]],
) -> None:
    """Keep historical test and plugin monkeypatch paths working after extraction."""
    module = sys.modules[module_name]
    module.__class__ = _LegacyPatchableModule
    module._legacy_patch_targets = dict(targets)
