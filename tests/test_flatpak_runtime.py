"""Keep the Flatpak runtime compatible with the Linux WebKitGTK UI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.linux_release_validation import PackagingError, validate_flatpak_manifest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "build/linux/flatpak/io.github.mskomek.HpcClientGui.json"
RELEASE_WORKFLOW = ROOT / ".github/workflows/release.yml"
LOCAL_RELEASE = ROOT / "scripts/build_release.ps1"


def test_flatpak_manifest_uses_gnome_runtime_for_webkitgtk() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["runtime"] == "org.gnome.Platform"
    assert manifest["runtime-version"] == "51"
    assert manifest["sdk"] == "org.gnome.Sdk"


def test_release_builders_install_the_manifest_runtime() -> None:
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    local_release = LOCAL_RELEASE.read_text(encoding="utf-8")
    for text in (workflow, local_release):
        assert "org.gnome.Platform//51" in text
        assert "org.gnome.Sdk//51" in text
        assert "org.freedesktop.Platform//24.08" not in text


def test_flatpak_validator_rejects_runtime_without_webkitgtk(tmp_path: Path) -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["runtime"] = "org.freedesktop.Platform"
    manifest["sdk"] = "org.freedesktop.Sdk"
    path = tmp_path / "missing-webkit-runtime.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(PackagingError, match="GNOME.*WebKitGTK"):
        validate_flatpak_manifest(path)
