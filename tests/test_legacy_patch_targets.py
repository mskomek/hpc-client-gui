from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import patch

from hpc_gui.core._legacy_patch_targets import enable_legacy_patch_targets


def test_lazy_facade_patch_restores_the_leaf_module() -> None:
    target_name = "hpc_gui_test_legacy_patch_target"
    facade_name = "hpc_gui_test_legacy_patch_facade"
    target = ModuleType(target_name)
    facade = ModuleType(facade_name)

    def original() -> list[str]:
        return ["saved"]

    def resolve(name: str) -> object:
        return getattr(target, name)

    target.load_profiles = original
    facade.__getattr__ = resolve
    sys.modules[target_name] = target
    sys.modules[facade_name] = facade
    try:
        enable_legacy_patch_targets(
            facade_name,
            {"load_profiles": ((target_name, "load_profiles"),)},
        )
        with patch(f"{facade_name}.load_profiles", return_value=[]):
            assert target.load_profiles() == []
        assert target.load_profiles is original
        assert facade.load_profiles is original
    finally:
        sys.modules.pop(facade_name, None)
        sys.modules.pop(target_name, None)
