"""Forward legacy facade monkeypatches to the leaf that owns each symbol."""

from __future__ import annotations

import sys
from importlib import import_module
from types import ModuleType
from typing import Mapping


class _LegacyPatchableModule(ModuleType):
    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        targets = self.__dict__.get("_legacy_patch_targets", {}).get(name, ())
        for module_name, target_name in targets:
            setattr(import_module(module_name), target_name, value)


def enable_legacy_patch_targets(
    module_name: str,
    targets: Mapping[str, tuple[tuple[str, str], ...]],
) -> None:
    """Keep historical test and plugin monkeypatch paths working after extraction."""
    module = sys.modules[module_name]
    module.__class__ = _LegacyPatchableModule
    module._legacy_patch_targets = dict(targets)
