"""Phase A: scoped host trust for Plugin API v3 OpenFOAM packages.

Narrow application-owned contract for ``org.hpcclient.openfoamlint``
(executable engine) and ``org.hpcclient.openfoamcasestudio`` (pinned
application engine). Production ships with NO host release pins in these
tests, so every unpinned API 3 package
fails closed; tests inject pins with ``monkeypatch`` only (never a
production bypass). Host process execution is not an OS sandbox.

Covers wrong ID / publisher / API / entrypoint / capability / role /
version, executable hashes and manifest digest; tampering rejected before
import; API 2 ANSYS behavior preserved; malformed packages rejected.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

from hpc_gui.plugins import trusted_api3
from hpc_gui.plugins.installer import InstallError, install_plugin_from_registry
from hpc_gui.plugins.linter_tools import ToolLoadError, load_tool_for_plugin
from hpc_gui.plugins.loader import load_installed_plugins
from hpc_gui.plugins.models import SUPPORTED_PLUGIN_API_VERSIONS
from hpc_gui.plugins.registry_client import OFFICIAL_RAW_BASE, RegistryError, parse_registry
from hpc_gui.plugins.storage import write_active_versions
from hpc_gui.plugins.trusted_api3 import (
    Api3Pin,
    api3_error,
    api3_error_for_dir,
    api3_integrity_error,
    api3_linter_entrypoint,
    api3_static_error,
    is_approved_api3,
)
from hpc_gui.plugins.trusted_tools import (
    APPROVED_TRUSTED_TOOLS,
    is_approved_trusted_tool,
    trusted_tool_error,
)
from hpc_gui.plugins.validator import validate_manifest_dict

LINTER_ID = "org.hpcclient.openfoamlint"
LINTER_VERSION = "0.2.0-w65r17-auditfix1"
STUDIO_ID = "org.hpcclient.openfoamcasestudio"
STUDIO_VERSION = "0.3.0-w65r17-auditfix1"
ENGINE_REL = "engine/openfoam_lint/__init__.py"
STUDIO_TEMPLATES_REL = "templates/index.json"
APP_VERSION = "1.5.9"
ENGINE_SRC = (
    "def create_plugin():\n"
    "    return {'id': 'org.hpcclient.openfoamlint', 'title': 'OF Linter', 'description': 'd',\n"
    "            'page_factory': lambda parent=None: None}\n"
    "SUPPORTED_SUFFIXES = frozenset()\n"
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _linter_manifest(engine: bytes, **overrides) -> dict:
    manifest = {
        "schema_version": 1, "plugin_api": 3, "id": LINTER_ID,
        "name": "OpenFOAM Linter", "version": LINTER_VERSION,
        "publisher": "HPC Client GUI", "license": "MIT",
        "description": "Static OpenFOAM case linter.",
        "requires_app": ">=1.5.9",
        "capabilities": ["linter-tool"],
        "entrypoints": {"linter_engine": ENGINE_REL},
        "files": [{"path": ENGINE_REL, "sha256": _sha(engine),
                   "size": len(engine), "role": "linter-engine"}],
    }
    manifest.update(overrides)
    return manifest


def _linter_pin(engine: bytes, manifest_sha: str | None = None) -> Api3Pin:
    return Api3Pin(LINTER_ID, LINTER_VERSION,
                   capabilities=("linter-tool",),
                   entrypoints=(("linter_engine", ENGINE_REL),),
                   files=((ENGINE_REL, "linter-engine", _sha(engine)),),
                   manifest_sha256=manifest_sha)


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
    write_active_versions({manifest["id"]: manifest["version"]}, root=root)
    return package


def _fetch(manifest: dict, manifest_bytes: bytes, payloads: dict[str, bytes]):
    base = f"plugins/{manifest['id'].split('.')[-1]}/{manifest['version']}"
    responses = {OFFICIAL_RAW_BASE + base + "/manifest.json": manifest_bytes}
    for rel, data in payloads.items():
        responses[OFFICIAL_RAW_BASE + base + "/" + rel] = data

    def fetch(url: str, max_bytes: int) -> bytes:
        payload = responses[url]
        assert len(payload) <= max_bytes
        return payload

    return fetch


def _entry(manifest: dict, manifest_bytes: bytes) -> dict:
    return {
        "id": manifest["id"], "name": manifest["name"], "version": manifest["version"],
        "plugin_api": 3, "type": "linter-tool", "description": manifest["description"],
        "publisher": manifest["publisher"], "requires_app": manifest["requires_app"],
        "manifest_path": f"plugins/{manifest['id'].split('.')[-1]}/{manifest['version']}/manifest.json",
        "manifest_sha256": _sha(manifest_bytes), "official": True,
    }


def _file_entry(**overrides) -> dict:
    entry = {"path": ENGINE_REL, "sha256": "0" * 64, "size": 1, "role": "linter-engine"}
    entry.update(overrides)
    return entry


@pytest.mark.contract
def test_production_pin_table_is_empty():
    assert trusted_api3.APPROVED_API3_PINS == {}
    assert SUPPORTED_PLUGIN_API_VERSIONS == frozenset({1, 2, 3})


@pytest.mark.contract
def test_validator_rejects_api3_without_host_pin():
    errors = validate_manifest_dict(_linter_manifest(ENGINE_SRC.encode()))
    assert any("unapproved plugin_api 3 package" in e for e in errors)
    assert any("no host release pin" in e for e in errors)


@pytest.mark.contract
def test_full_gate_fails_closed_without_integrity_evidence():
    engine = ENGINE_SRC.encode()
    manifest = _linter_manifest(engine)
    pin = _linter_pin(engine, manifest_sha=_sha(b"manifest"))
    assert "fail closed" in (api3_error(manifest, pins=_pins(pin)) or "")
    assert is_approved_api3(manifest) is False
    assert api3_integrity_error(manifest, actual_files={}, actual_manifest_sha=None,
                               pins=_pins(pin)) is not None


@pytest.mark.contract
def test_registry_discovers_api3_entries_but_rejects_api4():
    base = {"schema_version": 1, "plugin_api": 1,
            "repository": {"raw_base": OFFICIAL_RAW_BASE}, "plugins": []}
    manifest = _linter_manifest(ENGINE_SRC.encode())
    good = _entry(manifest, json.dumps(manifest).encode())
    assert parse_registry(json.dumps({**base, "plugins": [good]}).encode())
    with pytest.raises(RegistryError):
        parse_registry(json.dumps({**base, "plugins": [dict(good, plugin_api=4)]}).encode())


@pytest.mark.contract
def test_static_accepts_exact_linter_contract():
    engine = ENGINE_SRC.encode()
    manifest = _linter_manifest(engine)
    table = _pins(_linter_pin(engine, manifest_sha=_sha(b"manifest")))
    assert api3_static_error(manifest, pins=table) is None
    assert is_approved_api3(manifest, pins=table) is True
    assert api3_linter_entrypoint(manifest, pins=table) == ENGINE_REL


@pytest.mark.contract
def test_static_rejects_wrong_contract_fields():
    engine = ENGINE_SRC.encode()
    manifest = _linter_manifest(engine)
    table = _pins(_linter_pin(engine, manifest_sha=_sha(b"manifest")))
    bad_engine = _file_entry(sha256=_sha(engine), size=len(engine))
    cases = [
        {"id": "org.hpcclient.openfoamlint.evil"},
        {"publisher": "Evil Corp"},
        {"plugin_api": 2},
        {"version": "9.9.9"},
        {"capabilities": ["application-tools"]},
        {"capabilities": ["linter-tool", "application-tools"]},
        {"entrypoints": {"linter_engine": "engine/evil/__init__.py"}},
        {"entrypoints": {}},
        {"files": [_file_entry(sha256="0" * 64)]},
        {"files": [{**bad_engine, "role": "linter-data"}]},
    ]
    assert len(cases) == 10
    for override in cases:
        bad = {**manifest, **override}
        assert api3_static_error(bad, pins=table) is not None, override
        assert is_approved_api3(bad, pins=table) is False


def _studio_manifest(payload: bytes, **overrides) -> dict:
    manifest = {
        "schema_version": 1, "plugin_api": 3, "id": STUDIO_ID,
        "name": "Studio", "version": STUDIO_VERSION,
        "publisher": "HPC Client GUI", "license": "MIT", "description": "d",
        "requires_app": ">=1.5.9", "capabilities": ["application-tools", "job-template"],
        "entrypoints": {"job_templates": STUDIO_TEMPLATES_REL},
        "files": [{"path": STUDIO_TEMPLATES_REL, "sha256": _sha(payload),
                   "size": len(payload), "role": "template-index"}],
    }
    manifest.update(overrides)
    return manifest


def _studio_pin(payload: bytes, manifest_sha: str) -> Api3Pin:
    return Api3Pin(STUDIO_ID, STUDIO_VERSION,
                   capabilities=("application-tools", "job-template"),
                   entrypoints=(("job_templates", STUDIO_TEMPLATES_REL),),
                   files=((STUDIO_TEMPLATES_REL, "template-index", _sha(payload)),),
                   manifest_sha256=manifest_sha)


@pytest.mark.contract
def test_static_rejects_executable_for_studio_identity():
    payload = b'{"schema_version": 1, "templates": []}'
    table = _pins(_studio_pin(payload, _sha(b"studio-manifest")))
    assert api3_static_error(_studio_manifest(payload), pins=table) is None
    evil = _studio_manifest(
        payload,
        capabilities=["application-tools", "job-template", "linter-tool"],
        entrypoints={"linter_engine": ENGINE_REL},
        files=[_file_entry(sha256=_sha(b"x"))],
    )
    assert "executable" in (api3_static_error(evil, pins=table) or "")
    evil_tool = _studio_manifest(
        payload,
        entrypoints={"application_tool": "engine/openfoam_studio/__init__.py"},
    )
    assert api3_static_error(evil_tool, pins=table) is not None


@pytest.mark.contract
def test_integrity_matches_and_rejects_tampering():
    engine = ENGINE_SRC.encode()
    manifest = _linter_manifest(engine)
    manifest_bytes = json.dumps(manifest).encode()
    table = _pins(_linter_pin(engine, manifest_sha=_sha(manifest_bytes)))
    good = {ENGINE_REL: _sha(engine)}
    assert api3_integrity_error(manifest, actual_files=good,
                               actual_manifest_sha=_sha(manifest_bytes),
                               pins=table) is None
    assert api3_integrity_error(manifest, actual_files={ENGINE_REL: _sha(b"tampered")},
                               actual_manifest_sha=_sha(manifest_bytes),
                               pins=table) is not None
    assert api3_integrity_error(manifest, actual_files=good,
                               actual_manifest_sha=_sha(b"other"),
                               pins=table) is not None
    assert api3_integrity_error(manifest, actual_files={**good, "extra.py": _sha(b"x")},
                               actual_manifest_sha=_sha(manifest_bytes),
                               pins=table) is not None
    assert api3_integrity_error(manifest, actual_files={},
                               actual_manifest_sha=_sha(manifest_bytes),
                               pins=table) is not None


@pytest.mark.contract
def test_integrity_fails_closed_without_pinned_digest():
    engine = ENGINE_SRC.encode()
    manifest = _linter_manifest(engine)
    table = _pins(_linter_pin(engine, manifest_sha=None))
    reason = api3_integrity_error(manifest, actual_files={ENGINE_REL: _sha(engine)},
                                 actual_manifest_sha=_sha(b"manifest"), pins=table)
    assert reason is not None and "manifest digest" in reason


@pytest.mark.integration
def test_installer_rejects_api3_without_pin(tmp_path: Path):
    engine = ENGINE_SRC.encode()
    manifest = _linter_manifest(engine)
    manifest_bytes = json.dumps(manifest).encode()
    with pytest.raises(InstallError, match="unapproved plugin_api 3"):
        install_plugin_from_registry(
            _entry(manifest, manifest_bytes), root=tmp_path, app_version=APP_VERSION,
            fetcher=_fetch(manifest, manifest_bytes, {ENGINE_REL: engine}))


@pytest.mark.integration
def test_installer_loader_roundtrip_with_pin(tmp_path: Path, monkeypatch):
    engine = ENGINE_SRC.encode()
    manifest = _linter_manifest(engine)
    manifest_bytes = json.dumps(manifest).encode()
    monkeypatch.setattr(trusted_api3, "APPROVED_API3_PINS",
                        _pins(_linter_pin(engine, _sha(manifest_bytes))))
    result = install_plugin_from_registry(
        _entry(manifest, manifest_bytes), root=tmp_path, app_version=APP_VERSION,
        fetcher=_fetch(manifest, manifest_bytes, {ENGINE_REL: engine}))
    assert result.activated
    assert result.installed.linter_engine == {"module": ENGINE_REL}
    loaded = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert not loaded.problems
    assert [p.manifest.id for p in loaded.plugins] == [LINTER_ID]


@pytest.mark.integration
def test_loader_skips_joint_manifest_payload_tampering(tmp_path: Path, monkeypatch):
    engine = ENGINE_SRC.encode()
    manifest = _linter_manifest(engine)
    monkeypatch.setattr(trusted_api3, "APPROVED_API3_PINS",
                        _pins(_linter_pin(engine, _sha(json.dumps(manifest).encode()))))
    tampered = ENGINE_SRC.encode() + b"# tampered\n"
    _write_package(tmp_path, _linter_manifest(tampered), {ENGINE_REL: tampered})
    loaded = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert loaded.plugins == []
    assert len(loaded.problems) == 1
    assert "unapproved plugin_api 3" in loaded.problems[0].reason


@pytest.mark.integration
def test_dispatch_loads_pinned_engine_and_rejects_tampering(tmp_path: Path, monkeypatch):
    engine = ENGINE_SRC.encode()
    manifest = _linter_manifest(engine)
    manifest_bytes = json.dumps(manifest).encode()
    monkeypatch.setattr(trusted_api3, "APPROVED_API3_PINS",
                        _pins(_linter_pin(engine, _sha(manifest_bytes))))
    package = _write_package(tmp_path, manifest, {ENGINE_REL: engine})
    installed = load_installed_plugins(root=tmp_path, app_version=APP_VERSION).plugins[0]
    assert load_tool_for_plugin(installed).title == "OF Linter"
    before = {name for name in sys.modules if name.startswith("_hpc_gui_trusted_")}
    (package / ENGINE_REL).write_bytes(b"raise RuntimeError('must not import')\n")
    with pytest.raises(ToolLoadError, match="application-approved"):
        load_tool_for_plugin(installed)
    assert {n for n in sys.modules if n.startswith("_hpc_gui_trusted_")} == before


@pytest.mark.integration
def test_studio_api3_stays_declarative(tmp_path: Path, monkeypatch):
    payload = b'{"schema_version": 1, "templates": []}'
    manifest = _studio_manifest(payload)
    manifest_bytes = json.dumps(manifest).encode()
    monkeypatch.setattr(trusted_api3, "APPROVED_API3_PINS",
                        _pins(_studio_pin(payload, _sha(manifest_bytes))))
    entry = dict(_entry(manifest, manifest_bytes), type="application-tools")
    result = install_plugin_from_registry(
        entry, root=tmp_path, app_version=APP_VERSION,
        fetcher=_fetch(manifest, manifest_bytes, {STUDIO_TEMPLATES_REL: payload}))
    assert result.activated
    assert result.installed.linter_engine is None
    loaded = load_installed_plugins(root=tmp_path, app_version=APP_VERSION)
    assert not loaded.problems
    assert loaded.plugins[0].linter_engine is None


@pytest.mark.contract
def test_api2_ansys_and_narrow_openfoam_approvals_unchanged():
    assert set(APPROVED_TRUSTED_TOOLS) == {"org.hpcclient.ansyslint", "openfoam-linter"}
    ansys = {"plugin_api": 2, "id": "org.hpcclient.ansyslint",
             "publisher": "HPC Client GUI", "capabilities": ["linter-tool"],
             "entrypoints": {"linter_engine": "engine/ansys_lint/__init__.py"}}
    assert trusted_tool_error(ansys) is None
    assert is_approved_trusted_tool(ansys) is True
    assert validate_manifest_dict({
        "schema_version": 1, "plugin_api": 2, "id": "org.hpcclient.ansyslint",
        "name": "ANSYS", "version": "0.1.0", "publisher": "HPC Client GUI",
        "license": "MIT", "description": "d", "requires_app": ">=1.5.0",
        "capabilities": ["linter-tool"],
        "entrypoints": {"linter_engine": "engine/ansys_lint/__init__.py"},
        "files": [_file_entry(path="engine/ansys_lint/__init__.py",
                              sha256="a" * 64, size=10)]}) == []
    linter_v2 = {"plugin_api": 2, "id": "openfoam-linter",
                 "publisher": "HPC Client GUI",
                 "capabilities": ["lint-rules", "linter-tool"],
                 "entrypoints": {"linter_engine": ENGINE_REL}}
    assert trusted_tool_error(linter_v2) is None
    assert trusted_tool_error({**linter_v2, "publisher": "Evil"}) is not None


@pytest.mark.contract
def test_api3_identity_never_passes_the_api2_gate(tmp_path: Path):
    manifest = _linter_manifest(ENGINE_SRC.encode())
    assert trusted_tool_error(manifest) is not None
    assert is_approved_trusted_tool(manifest) is False
    assert api3_error_for_dir(manifest, tmp_path / "missing-package") is not None
