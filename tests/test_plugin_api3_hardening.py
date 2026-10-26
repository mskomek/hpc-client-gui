"""API3 hardening: pin path validation, symlink rejection, malformed metadata.

Focused attack-surface tests for the application-owned API v3 gate. Every
case must fail closed with no import, no test bypass, and no compact
line-count tricks. Production pins stay empty; pins are monkeypatched.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from hpc_gui.plugins import trusted_api3
from hpc_gui.plugins.trusted_api3 import (
    Api3Pin,
    api3_error_for_dir,
    api3_pin_path_error,
    api3_static_error,
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


ENGINE = b"def create_plugin():\n    return {}\n"
ENGINE_REL = "engine/openfoam_lint/__init__.py"
LINTER_ID = "org.hpcclient.openfoamlint"
LINTER_VERSION = "0.2.0-w65r17-auditfix1"


def _manifest(**overrides) -> dict:
    base = {
        "schema_version": 1,
        "plugin_api": 3,
        "id": LINTER_ID,
        "name": "OpenFOAM Linter",
        "version": LINTER_VERSION,
        "publisher": "HPC Client GUI",
        "license": "MIT",
        "description": "d",
        "requires_app": ">=1.5.9",
        "capabilities": ["linter-tool"],
        "entrypoints": {"linter_engine": ENGINE_REL},
        "files": [
            {
                "path": ENGINE_REL,
                "sha256": _sha(ENGINE),
                "size": len(ENGINE),
                "role": "linter-engine",
            }
        ],
    }
    base.update(overrides)
    return base


def _pin(manifest_sha: str, files=None) -> Api3Pin:
    pinned = files if files is not None else (
        (ENGINE_REL, "linter-engine", _sha(ENGINE)),
    )
    return Api3Pin(
        LINTER_ID,
        LINTER_VERSION,
        capabilities=("linter-tool",),
        entrypoints=(("linter_engine", ENGINE_REL),),
        files=pinned,
        manifest_sha256=manifest_sha,
    )


def _pins(*pins: Api3Pin) -> dict:
    return {(pin.plugin_id, pin.version): pin for pin in pins}


def _write_package(root: Path, manifest: dict, payloads: dict[str, bytes]) -> Path:
    package = root / "packages" / manifest["id"] / manifest["version"]
    package.mkdir(parents=True, exist_ok=True)
    (package / "manifest.json").write_bytes(json.dumps(manifest).encode())
    for rel, data in payloads.items():
        target = package / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return package


@pytest.mark.contract
def test_pin_path_attacks_rejected_before_filesystem_access():
    bad_paths = [
        "/absolute/path.py",
        "C:/drive/path.py",
        "engine\\backslash.py",
        "engine/../escape.py",
        "../escape.py",
        "engine/./dot.py",
        "engine//empty.py",
        "https://evil.example/payload.py",
        "engine/%2e%2e/encoded.py",
        "engine/\x00nul.py",
        "engine/\ncontrol.py",
        "",
    ]
    assert len(bad_paths) == 12
    for bad in bad_paths:
        assert api3_pin_path_error(bad, "linter-engine") is not None, bad


@pytest.mark.contract
def test_pin_suffix_role_combinations_are_narrow():
    assert api3_pin_path_error(ENGINE_REL, "linter-engine") is None
    assert api3_pin_path_error("data.json", "linter-data") is None
    assert api3_pin_path_error("doc.md", "documentation") is None
    assert api3_pin_path_error("index.json", "template-index") is None
    assert api3_pin_path_error("data.json", "linter-engine") is not None
    assert api3_pin_path_error("engine.py", "linter-data") is not None
    assert api3_pin_path_error("payload.exe", "documentation") is not None


@pytest.mark.contract
def test_short_ids_never_match_dotted_pins():
    manifest = _manifest()
    table = _pins(_pin(_sha(b"manifest")))
    short = dict(manifest, id="openfoam-linter")
    assert api3_static_error(short, pins=table) is not None
    assert "no host release pin" in (api3_static_error(short, pins=table) or "")


@pytest.mark.contract
def test_symlink_package_manifest_and_payload_fail_closed(tmp_path: Path):
    manifest = _manifest()
    manifest_bytes = json.dumps(manifest).encode()
    table = _pins(_pin(_sha(manifest_bytes)))
    package = _write_package(tmp_path, manifest, {ENGINE_REL: ENGINE})
    link_target = tmp_path / "link-package"
    try:
        link_target.symlink_to(package, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable on this platform")
    assert api3_error_for_dir(manifest, link_target, pins=table) is not None
    manifest_link = package / "manifest.json"
    real_bytes = manifest_link.read_bytes()
    manifest_link.unlink()
    try:
        manifest_link.symlink_to(tmp_path / "real-manifest.json")
        (tmp_path / "real-manifest.json").write_bytes(real_bytes)
    except OSError:
        pytest.skip("symlinks unavailable on this platform")
    try:
        assert api3_error_for_dir(manifest, package, pins=table) is not None
    finally:
        manifest_link.unlink()
        manifest_link.write_bytes(real_bytes)
    payload_link = package / ENGINE_REL
    payload_link.unlink()
    try:
        payload_link.symlink_to(tmp_path / "real-engine.py")
        (tmp_path / "real-engine.py").write_bytes(ENGINE)
    except OSError:
        pytest.skip("symlinks unavailable on this platform")
    try:
        assert api3_error_for_dir(manifest, package, pins=table) is not None
    finally:
        payload_link.unlink()
        payload_link.write_bytes(ENGINE)


@pytest.mark.contract
def test_symlink_path_component_and_extra_link_fail_closed(tmp_path: Path):
    manifest = _manifest()
    manifest_bytes = json.dumps(manifest).encode()
    table = _pins(_pin(_sha(manifest_bytes)))
    package = _write_package(tmp_path, manifest, {ENGINE_REL: ENGINE})
    engine_dir = package / "engine"
    moved = tmp_path / "real-engine-dir"
    engine_dir.rename(moved)
    try:
        engine_dir.symlink_to(moved, target_is_directory=True)
    except OSError:
        engine_dir.rename(package / "engine")
        pytest.skip("symlinks unavailable on this platform")
    try:
        assert api3_error_for_dir(manifest, package, pins=table) is not None
    finally:
        engine_dir.unlink()
        moved.rename(engine_dir)
    extra_link = package / "extra.json"
    try:
        extra_link.symlink_to(tmp_path / "real-manifest.json")
    except OSError:
        pytest.skip("symlinks unavailable on this platform")
    assert api3_error_for_dir(manifest, package, pins=table) is not None


@pytest.mark.contract
def test_malformed_package_metadata_fails_closed(tmp_path: Path):
    manifest = _manifest()
    manifest_bytes = json.dumps(manifest).encode()
    good_table = _pins(_pin(_sha(manifest_bytes)))
    package = _write_package(tmp_path, manifest, {ENGINE_REL: ENGINE})
    (package / "manifest.json").write_bytes(b"{not json")
    assert api3_error_for_dir(manifest, package, pins=good_table) is not None
    (package / "manifest.json").write_bytes(manifest_bytes)
    (package / ENGINE_REL).write_bytes(b"tampered")
    assert api3_error_for_dir(manifest, package, pins=good_table) is not None
    (package / ENGINE_REL).write_bytes(ENGINE)
    (package / "unexpected.json").write_bytes(b"{}")
    assert api3_error_for_dir(manifest, package, pins=good_table) is not None


@pytest.mark.contract
def test_production_pins_stay_empty_and_fail_closed(tmp_path: Path):
    assert trusted_api3.APPROVED_API3_PINS == {}
    assert api3_error_for_dir(_manifest(), tmp_path, pins=None) is not None
