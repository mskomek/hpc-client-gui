"""W65 R17 slice: linter display-name safety, no-silent-drop, real-bytes entrypoint.

Focused negatives/boundaries for the newly tracked
``src/hpc_gui/plugin_engines/openfoam_lint`` entrypoint. Complements
``test_w65_lint_engine_contract.py`` (size limits, encoding, symlink,
depth, count/aggregate caps, remote adapters). Synthetic pins only
(``tmp_path`` + ``monkeypatch``); production release pins are never
touched here.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from hpc_gui.openfoam_core import MAX_TEXT_BYTES
from hpc_gui.plugin_engines.openfoam_lint.api import lint_files, lint_text, rule_catalog

ENGINE_SOURCES = Path(__file__).resolve().parents[1] / "src" / "hpc_gui" / "plugin_engines" / "openfoam_lint"
ENTRY_REL = "engine/openfoam_lint/__init__.py"
PLUGIN_ID = "org.hpcclient.openfoamlint"
PLUGIN_VERSION = "9.9.9-synthetic-r17slice"


def test_lint_text_rejects_unc_drive_and_absolute_names():
    for bad_name in (
        "//server/share/note.dict",
        "\\\\server\\share\\note.dict",
        "C:\\win\\note.dict",
        "/absolute/note.dict",
        "a\x01b",
        "a\x7fb",
    ):
        with pytest.raises(ValueError):
            lint_text("application simpleFoam;\n", file_name=bad_name)


def test_lint_text_memory_display_name_is_allowed():
    assert lint_text("application simpleFoam;\n").files_checked == ("<memory>",)
    assert lint_text("application simpleFoam;\n", file_name="<memory>").files_checked == ("<memory>",)


def test_lint_text_keeps_display_name_separate_from_source_path(tmp_path):
    target = tmp_path / "system" / "controlDict"
    target.parent.mkdir(parents=True)
    target.write_text("application simpleFoam;\n", encoding="utf-8")
    result = lint_text(target.read_text(encoding="utf-8"), file_name="system/controlDict")
    assert result.files_checked == ("system/controlDict",)


def test_lint_files_unsupported_names_are_diagnosed_not_dropped():
    result = lint_files({"notes.txt": "hello\n", "Allrun": "#!/bin/sh\n"})
    assert result.files_checked == ()
    assert [(d.rule_id, d.path) for d in result.diagnostics] == [
        ("OF-CASE-007", "Allrun"),
        ("OF-CASE-007", "notes.txt"),
    ]
    assert rule_catalog()["OF-CASE-007"]["title"] == "Unsupported input file"


def test_lint_text_static_only_flags_without_executing():
    result = lint_text("#codeStream\n{\ncode 1;\n}\n", file_name="0/U")
    assert any(d.rule_id == "OF-SEC-001" for d in result.diagnostics)
    assert result.files_checked == ("0/U",)


def test_real_engine_entrypoint_via_verified_bytes(tmp_path, monkeypatch):
    from hpc_gui.plugins import linter_tools
    from hpc_gui.plugins.trusted_api3 import Api3Pin

    package = tmp_path / "pkg"
    sources: dict[str, bytes] = {}
    for source in sorted(ENGINE_SOURCES.glob("*.py")):
        data = source.read_bytes()
        rel = f"engine/openfoam_lint/{source.name}"
        (package / rel).parent.mkdir(parents=True, exist_ok=True)
        (package / rel).write_bytes(data)
        sources[rel] = data
    manifest_obj = {
        "id": PLUGIN_ID,
        "version": PLUGIN_VERSION,
        "publisher": "HPC Client GUI",
        "plugin_api": 3,
        "capabilities": ["linter-tool"],
        "entrypoints": {"linter_engine": ENTRY_REL},
        "files": [
            {"path": rel, "role": "linter-engine", "sha256": hashlib.sha256(data).hexdigest()}
            for rel, data in sorted(sources.items())
        ],
    }
    manifest_bytes = json.dumps(manifest_obj, sort_keys=True).encode()
    (package / "manifest.json").write_bytes(manifest_bytes)
    pin = Api3Pin(
        PLUGIN_ID, PLUGIN_VERSION,
        capabilities=("linter-tool",),
        entrypoints=(("linter_engine", ENTRY_REL),),
        files=tuple(
            (rel, "linter-engine", hashlib.sha256(data).hexdigest())
            for rel, data in sorted(sources.items())
        ),
        manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
    )
    monkeypatch.setattr(
        "hpc_gui.plugins.trusted_api3.APPROVED_API3_PINS", {(PLUGIN_ID, PLUGIN_VERSION): pin}
    )
    manifest = SimpleNamespace(
        id=PLUGIN_ID, version=PLUGIN_VERSION, publisher="HPC Client GUI", plugin_api=3,
        capabilities=["linter-tool"], entrypoints={"linter_engine": ENTRY_REL},
        files=[
            SimpleNamespace(path=rel, role="linter-engine",
                            sha256=hashlib.sha256(data).hexdigest())
            for rel, data in sorted(sources.items())
        ],
    )
    installed = SimpleNamespace(manifest=manifest, directory=str(package))
    module_name = linter_tools._tool_module_name(installed)
    try:
        module = linter_tools._load_api3_engine_verified(installed, ENTRY_REL)
        assert module.__hpc_api3__ is True
        result = module.lint_text("application simpleFoam;\n", file_name="system/controlDict")
        assert result.files_checked == ("system/controlDict",)

        api_mod = sys.modules[module.__name__ + ".api"]
        calls: list[str] = []
        real = api_mod.lint_dictionary

        def _spy(text, *, path="<memory>"):
            calls.append(path)
            return real(text, path=path)

        monkeypatch.setattr(api_mod, "lint_dictionary", _spy)
        with pytest.raises(ValueError):
            module.lint_text("x" * (MAX_TEXT_BYTES + 1), file_name="note.dict")
        assert calls == []
    finally:
        linter_tools._remove_api3_finder(module_name)
        linter_tools._remove_module_namespace(module_name)
    assert module_name not in sys.modules
