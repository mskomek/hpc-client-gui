"""Offline macOS wx migration audit checks."""

from __future__ import annotations

from dataclasses import dataclass

from hpc_gui.core.secret_store import keychain_available
from hpc_gui.services.app_updater import release_asset_names
from hpc_gui.services.platform_keymap import bindings_for
from hpc_gui.services.xserver_manager import ensure_xquartz_available


@dataclass(frozen=True)
class AuditResult:
    name: str
    passed: bool
    detail: str = ""


def run_audit() -> tuple[AuditResult, ...]:
    bindings = bindings_for("macos")
    shell = {item.command_id: item.binding for item in bindings if item.context == "shell"}
    return (
        AuditResult("command map", shell.get("APP-SETTINGS") == "Cmd+,"),
        AuditResult("keychain adapter", callable(keychain_available)),
        AuditResult("xquartz adapter", callable(ensure_xquartz_available)),
        AuditResult("native architectures", release_asset_names("macos_arm64")[0].endswith("_arm64.dmg") and release_asset_names("macos_x86_64")[0].endswith("_x86_64.dmg")),
    )


__all__ = ["AuditResult", "run_audit"]
