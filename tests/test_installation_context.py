import plistlib
from pathlib import Path

from hpc_gui.services import installation_context


def _platform(monkeypatch, os_name: str, executable: Path) -> None:
    monkeypatch.setattr(installation_context, "current_os", lambda: os_name)
    monkeypatch.setattr(installation_context, "current_architecture", lambda: "x86_64")
    monkeypatch.setattr(installation_context, "_executable", lambda: executable.resolve())


def test_windows_frozen_uses_explicit_portable_strategy(monkeypatch, tmp_path: Path):
    executable = tmp_path / "hpc-client-gui.exe"
    executable.write_bytes(b"")
    _platform(monkeypatch, "windows", executable)
    monkeypatch.setattr(installation_context.sys, "frozen", True, raising=False)

    assert installation_context.detect_installation().capability == "windows-portable"


def test_linux_installation_strategies_are_evidence_based(monkeypatch, tmp_path: Path):
    executable = tmp_path / "client.AppImage"
    executable.write_bytes(b"image")
    _platform(monkeypatch, "linux", executable)
    monkeypatch.delenv("FLATPAK_ID", raising=False)
    monkeypatch.setenv("APPIMAGE", str(executable))
    assert installation_context.detect_installation().capability == "linux-appimage"

    monkeypatch.setenv("FLATPAK_ID", "io.github.mskomek.HpcClientGui")
    assert installation_context.detect_installation().capability == "linux-flatpak"


def test_deb_and_source_strategies_do_not_guess(monkeypatch, tmp_path: Path):
    executable = tmp_path / "hpc-client-gui"
    executable.write_bytes(b"")
    _platform(monkeypatch, "linux", executable)
    monkeypatch.delenv("FLATPAK_ID", raising=False)
    monkeypatch.delenv("APPIMAGE", raising=False)
    monkeypatch.setattr(
        installation_context,
        "_run",
        lambda args: (
            "hpc-client-gui: /usr/bin/hpc-client-gui"
            if args[1] == "-S"
            else "hpc-client-gui\n1.5.5\namd64"
        ),
    )
    assert installation_context.detect_installation().capability == "linux-deb"

    monkeypatch.setattr(installation_context, "_run", lambda _args: "")
    assert installation_context.detect_installation().capability == "source"


def test_unknown_installation_is_unsupported(monkeypatch, tmp_path: Path):
    executable = tmp_path / "client"
    executable.write_bytes(b"")
    _platform(monkeypatch, "other", executable)

    assert installation_context.detect_installation().capability == "unsupported"


def test_macos_bundle_identity_is_read_from_info_plist(monkeypatch, tmp_path: Path):
    bundle = tmp_path / "HPC Client GUI.app"
    executable = bundle / "Contents" / "MacOS" / "hpc-client-gui"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"")
    info = bundle / "Contents" / "Info.plist"
    info.parent.mkdir(parents=True, exist_ok=True)
    info.write_bytes(plistlib.dumps({
        "CFBundleIdentifier": "io.github.mskomek.HpcClientGui",
        "CFBundleShortVersionString": "1.5.5",
    }))
    _platform(monkeypatch, "macos", executable)

    context = installation_context.detect_installation()
    assert context.capability == "macos-bundle"
    assert context.identity == "io.github.mskomek.HpcClientGui"
