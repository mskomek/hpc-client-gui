from __future__ import annotations

import pytest

from hpc_gui.core import platform as app_platform


@pytest.mark.parametrize(
    ("platform_name", "expected"),
    [("win32", "windows"), ("linux", "linux"), ("darwin", "macos"), ("freebsd", "unsupported")],
)
def test_current_os_normalizes_supported_platforms(platform_name, expected):
    assert app_platform.current_os(platform_name) == expected


@pytest.mark.parametrize(
    ("machine", "expected"),
    [("arm64", "arm64"), ("aarch64", "arm64"), ("AMD64", "x86_64"), ("x86_64", "x86_64")],
)
def test_current_architecture_normalizes_release_names(machine, expected):
    assert app_platform.current_architecture(machine) == expected


def test_release_platform_key_rejects_unknown_values():
    with pytest.raises(RuntimeError, match="Unsupported release platform"):
        app_platform.release_platform_key("darwin", "ppc64")


def test_release_platform_key_and_frozen_state(monkeypatch):
    monkeypatch.setattr(app_platform.sys, "frozen", True, raising=False)

    assert app_platform.release_platform_key("darwin", "aarch64") == "macos_arm64"
    assert app_platform.is_frozen() is True
