"""W65 linter/core compatibility: parser contract plus real engine entrypoint.

Direct facade/engine contract checks plus one end-to-end load of the real
``lint_text`` entrypoint through the API3 verified-byte loader. All
sources and test pins here are synthetic (``tmp_path`` + ``monkeypatch``);
production pins approve only the explicitly enumerated W65 candidate identities.
"""

from __future__ import annotations

import hashlib
import stat
from types import SimpleNamespace

import pytest

from hpc_gui.openfoam_core import (
    DecodedSource,
    Diagnostic,
    MAX_CASE_BYTES,
    MAX_CASE_FILES,
    MAX_DICTIONARY_BYTES,
    MAX_TEXT_BYTES,
    ParsedDictionary,
    Token,
    discover_case_files,
    is_dictionary_name,
    is_mesh_boundary_path,
    parse_dictionary,
    parse_mesh_boundary_names,
    parse_region_properties,
    parse_text,
    safe_relative_path,
)
from hpc_gui.plugin_engines.openfoam_lint import api as engine_api
from hpc_gui.plugin_engines.openfoam_lint.api import (
    lint_files,
    lint_paths,
    lint_text,
    rule_catalog,
    supports_filename,
)


def test_production_api3_pins_are_exact_candidate_versions():
    from hpc_gui.plugins import trusted_api3

    assert set(trusted_api3.APPROVED_API3_PINS) == {
        ("org.hpcclient.openfoamlint", "0.2.1-w65r18.20261027.3"),
        ("org.hpcclient.openfoamcasestudio", "0.3.1-w65r18.20261027.3"),
        ("org.hpcclient.openfoamlint", "0.2.1-w65r19.20261027.1"),
        ("org.hpcclient.openfoamcasestudio", "0.3.1-w65r19.20261027.1"),
        ("org.hpcclient.openfoamlint", "0.2.1-w65r19.20261027.2"),
        ("org.hpcclient.openfoamcasestudio", "0.3.1-w65r19.20261027.2"),
    }


def test_facade_contract_names():
    assert issubclass(ParsedDictionary, object)
    assert is_dictionary_name("system/controlDict")
    assert is_dictionary_name("0/U")
    assert not is_dictionary_name("Allrun")
    assert is_mesh_boundary_path("constant/polyMesh/boundary")
    assert not is_mesh_boundary_path("system/controlDict")
    assert safe_relative_path("system/controlDict")
    assert not safe_relative_path("../escape")
    assert not safe_relative_path("/absolute")
    assert rule_catalog()
    assert supports_filename("system/controlDict")
    assert not supports_filename("Allrun")
    assert isinstance(Token("atom", "x", 1, 1), Token)
    assert isinstance(Diagnostic("R", "info", "certain", "p", 1, 1, "m"), Diagnostic)


def test_legacy_parse_text_preserved():
    ok = parse_text("FoamFile\n{\n    version 2.0;\n}\napplication simpleFoam;\n")
    assert "application" in ok.entries and not ok.issues
    bad = parse_text("application simpleFoam\n")
    assert any("terminating" in issue.message for issue in bad.issues)
    assert parse_text("#codeStream\n{\ncode 1;\n}\n").has_executable_directive
    assert parse_text('#include "other"\n').includes == ["#include"]


def test_parse_dictionary_static_only():
    parsed = parse_dictionary('application simpleFoam;\n#codeStream\n{\ncode 1;\n}\n')
    assert parsed.value("application") == "simpleFoam"
    assert len(parsed.find("application")) == 1
    assert any(d.rule_id == "OF-SEC-001" for d in parsed.diagnostics)
    assert any(t.kind == "directive" for t in parsed.tokens)
    with pytest.raises(TypeError):
        parse_dictionary(b"bytes")  # noqa: B036 - must reject non-str


def test_parse_region_and_mesh_helpers():
    parsed = parse_dictionary("regions\n(\nfluid (water air)\nsolid (steel)\n);\n")
    metadata = parse_region_properties(parsed)
    assert metadata.names == ("water", "air", "steel")
    assert "fluid" in metadata.summary
    with pytest.raises(ValueError):
        parse_region_properties(parse_dictionary("application simpleFoam;\n"))
    mesh = (
        "3\n(\ninlet\n{\ntype patch;\n}\noutlet\n{\ntype patch;\n}\nwall\n{\ntype wall;\n}\n)\n"
    )
    assert parse_mesh_boundary_names(mesh) == frozenset({"inlet", "outlet", "wall"})
    assert parse_mesh_boundary_names("2\n(\n$patch\n{\ntype patch;\n}\n)\n") is None


def test_lint_text_short_and_clean():
    result = lint_text("application simpleFoam;\n", file_name="system/controlDict")
    assert result.files_checked == ("system/controlDict",)
    assert result.errors == 0


def test_lint_text_size_boundaries():
    exact = "x" * MAX_TEXT_BYTES
    assert lint_text(exact, file_name="note.dict").files_checked == ("note.dict",)
    multibyte = "é" * (MAX_TEXT_BYTES // 2)
    assert lint_text(multibyte, file_name="note.dict").files_checked == ("note.dict",)
    with pytest.raises(ValueError):
        lint_text("x" * (MAX_TEXT_BYTES + 1), file_name="note.dict")
    with pytest.raises(ValueError):
        lint_text("é" * (MAX_TEXT_BYTES // 2 + 1), file_name="note.dict")


def test_lint_text_rejects_non_string_and_surrogates():
    for bad in (None, 123, b"application simpleFoam;\n", ["x"]):
        with pytest.raises(TypeError):
            lint_text(bad, file_name="note.dict")
    with pytest.raises(ValueError):
        lint_text("bad \ud800 surrogate", file_name="note.dict")


def test_lint_text_rejects_dangerous_names():
    for bad_name in ("../escape", "/absolute/path", "C:/win/path", "..\\escape", "a\x00b", "a\nb"):
        with pytest.raises(ValueError):
            lint_text("application simpleFoam;\n", file_name=bad_name)
    for bad_type in (None, 123, b"note.dict"):
        with pytest.raises(TypeError):
            lint_text("application simpleFoam;\n", file_name=bad_type)  # type: ignore[arg-type]


def test_lint_files_invalid_utf8_diagnosed():
    result = lint_files({"system/controlDict": b"\xff\xfe not text"})
    assert any(d.rule_id == "OF-DICT-005" for d in result.diagnostics)
    assert result.files_checked == ()


def test_lint_files_rejects_non_text_values():
    result = lint_files({"system/controlDict": 123})  # type: ignore[dict-item]
    assert any(d.rule_id == "OF-DICT-005" for d in result.diagnostics)


def test_lint_files_per_file_and_case_limits(tmp_path):
    big = "x" * (MAX_DICTIONARY_BYTES + 1)
    result = lint_files({"system/controlDict": big})
    assert any(d.rule_id == "OF-CASE-005" for d in result.diagnostics)
    many = {f"system/field{i}Dict": "application simpleFoam;\n" for i in range(MAX_CASE_FILES + 5)}
    result = lint_files(many)
    assert len(result.files_checked) == MAX_CASE_FILES
    assert any("file-count" in d.message for d in result.diagnostics)
    chunk = "y" * MAX_DICTIONARY_BYTES
    names = [f"system/part{i}Dict" for i in range(MAX_CASE_BYTES // MAX_DICTIONARY_BYTES + 2)]
    result = lint_files({name: chunk for name in names})
    assert any("byte limit" in d.message for d in result.diagnostics)
    _ = tmp_path


def _write_case(root, mapping: dict[str, str]) -> None:
    for relative, text in mapping.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def test_lint_files_include_cycle(tmp_path):
    _write_case(tmp_path, {
        "system/controlDict": '#include "other"\napplication simpleFoam;\n',
        "system/other": '#include "controlDict"\n',
    })
    result = lint_files(
        {
            "system/controlDict": '#include "other"\napplication simpleFoam;\n',
            "system/other": '#include "controlDict"\n',
        },
        root=tmp_path,
    )
    assert any(d.rule_id == "OF-SEC-003" for d in result.diagnostics)


def test_lint_files_include_depth_limit(tmp_path):
    depth = 70
    mapping = {}
    for index in range(depth):
        nxt = f"inc{index + 1}" if index + 1 < depth else "leaf"
        mapping[f"system/inc{index}"] = f'#include "{nxt}"\n'
    mapping["system/leaf"] = "application simpleFoam;\n"
    _write_case(tmp_path, mapping)
    result = lint_files(dict(mapping), root=tmp_path)
    assert any(d.rule_id == "OF-SEC-004" for d in result.diagnostics)


def test_lint_paths_symlink_escape(tmp_path):
    outside = tmp_path / "outside.dict"
    outside.write_text("application simpleFoam;\n", encoding="utf-8")
    link = tmp_path / "linked.dict"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks unavailable")
    result = lint_paths([link])
    assert any(d.rule_id == "OF-CASE-006" for d in result.diagnostics)


def test_lint_paths_discovers_case(tmp_path):
    _write_case(tmp_path, {"system/controlDict": "application simpleFoam;\n"})
    result = lint_paths([tmp_path])
    assert result.files_checked
    assert discover_case_files(tmp_path)


def test_remote_path_validation():
    from hpc_gui.plugin_engines.openfoam_lint.remote_case import lint_remote_path

    class _Files:
        def stat_entry(self, _path):
            return SimpleNamespace(mode=stat.S_IFDIR | 0o755)

        lstat_entry = stat_entry

        def is_dir(self, _path):
            return True

    with pytest.raises(ValueError):
        lint_remote_path("../escape", _Files())
    with pytest.raises(ValueError):
        lint_remote_path("relative/path", _Files())


def test_remote_symlink_rejected():
    from hpc_gui.plugin_engines.openfoam_lint.remote_case import lint_remote_path

    class _Files:
        def stat_entry(self, _path):
            return SimpleNamespace(mode=stat.S_IFLNK | 0o777)

        lstat_entry = stat_entry

        def is_dir(self, _path):
            return False

    with pytest.raises(ValueError):
        lint_remote_path("/case/system/controlDict", _Files())


class _FakeRemote:
    def __init__(self, payloads: dict[str, bytes]) -> None:
        self.payloads = dict(payloads)

    def stat_entry(self, path):
        if path in self.payloads:
            return SimpleNamespace(mode=stat.S_IFREG | 0o644)
        return SimpleNamespace(mode=stat.S_IFDIR | 0o755)

    lstat_entry = stat_entry

    def stat(self, path):
        return (len(self.payloads[path]), 0)

    def is_dir(self, path):
        return path not in self.payloads

    def exists(self, path):
        return True

    def listdir_entries(self, directory):
        prefix = directory.rstrip("/") + "/"
        names = set()
        for path in self.payloads:
            if path.startswith(prefix):
                rest = path[len(prefix):]
                names.add(rest.split("/")[0])
        return [SimpleNamespace(name=name) for name in sorted(names)]

    def download(self, remote, local):
        with open(local, "wb") as handle:
            handle.write(self.payloads[remote])


def test_remote_happy_path_uses_verified_bounds():
    from hpc_gui.plugin_engines.openfoam_lint.remote_case import lint_remote_path

    files = _FakeRemote({"/case/system/controlDict": b"application simpleFoam;\n"})
    result = lint_remote_path("/case/system/controlDict", files)
    assert "/case/system/controlDict" in result.files_checked


def test_remote_results_keep_absolute_sftp_locations():
    from hpc_gui.plugin_engines.openfoam_lint.remote_case import lint_remote_path

    files = _FakeRemote({"/case/system/controlDict": b"application simpleFoam\n"})
    result = lint_remote_path("/case/system/controlDict", files)
    assert result.diagnostics
    assert all(item.path.startswith("/case/") for item in result.diagnostics)
    assert all(item.startswith("/case/") for item in result.files_checked)


def test_remote_scan_cancellation_stops_before_downloading():
    from threading import Event
    from hpc_gui.openfoam_core.cancellation import ScanCancelledError
    from hpc_gui.plugin_engines.openfoam_lint.remote_case import lint_remote_path

    class _ObservedRemote(_FakeRemote):
        downloaded = False

        def download(self, remote, local):
            self.downloaded = True
            super().download(remote, local)

    files = _ObservedRemote({"/case/system/controlDict": b"application simpleFoam;\n"})
    event = Event()
    event.set()
    with pytest.raises(ScanCancelledError):
        lint_remote_path("/case", files, cancel_event=event)
    assert not files.downloaded


def test_rejected_input_never_reaches_parsing(monkeypatch):
    import hpc_gui.plugin_engines.openfoam_lint.rules_dictionary as rules_dict

    calls: list[str] = []
    real = rules_dict.parse_dictionary

    def _spy(text, *, path="<memory>"):
        calls.append(path)
        return real(text, path=path)

    monkeypatch.setattr(rules_dict, "parse_dictionary", _spy)
    with pytest.raises(ValueError):
        lint_text("x" * (MAX_TEXT_BYTES + 1), file_name="note.dict")
    with pytest.raises(TypeError):
        lint_text(123, file_name="note.dict")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        lint_text("ok;\n", file_name="../escape")
    assert calls == []
    lint_text("application simpleFoam;\n", file_name="note.dict")
    assert calls == ["note.dict"]


def test_decoded_source_strict_and_round_trip():
    with pytest.raises(UnicodeError):
        DecodedSource.from_bytes(b"\xff\xfe")
    decoded = DecodedSource.from_bytes("application simpleFoam;\n".encode())
    assert decoded.encode(decoded.text).endswith(b"simpleFoam;\n")


def test_engine_entrypoint_via_verified_bytes(tmp_path, monkeypatch):
    from hpc_gui.plugins import linter_tools
    from hpc_gui.plugins.trusted_api3 import Api3Pin

    plugin_id = "org.hpcclient.openfoamlint"
    version = "9.9.9-synthetic"
    rel = "engine/openfoam_lint/__init__.py"
    engine = (
        b"from hpc_gui.plugin_engines.openfoam_lint.api import lint_files as _f\n"
        b"from hpc_gui.plugin_engines.openfoam_lint.api import lint_text as _t\n"
        b"lint_text = _t\n"
        b"lint_files = _f\n"
        b"SUPPORTED_SUFFIXES = frozenset({\".dict\"})\n"
        b"def create_plugin():\n"
        b"    return {'id': 'org.hpcclient.openfoamlint', 'title': 'T', 'description': 'd',"
        b" 'page_factory': lambda parent=None: None}\n"
    )
    package = tmp_path / "pkg"
    (package / "engine" / "openfoam_lint").mkdir(parents=True)
    (package / rel).write_bytes(engine)
    manifest_obj = {
        "id": plugin_id,
        "version": version,
        "publisher": "HPC Client GUI",
        "plugin_api": 3,
        "capabilities": ["linter-tool"],
        "entrypoints": {"linter_engine": rel},
        "files": [{"path": rel, "role": "linter-engine",
                   "sha256": hashlib.sha256(engine).hexdigest()}],
    }
    import json as _json

    manifest_bytes = _json.dumps(manifest_obj, sort_keys=True).encode()
    (package / "manifest.json").write_bytes(manifest_bytes)
    pin = Api3Pin(
        plugin_id, version,
        capabilities=("linter-tool",),
        entrypoints=(("linter_engine", rel),),
        files=((rel, "linter-engine", hashlib.sha256(engine).hexdigest()),),
        manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
    )
    monkeypatch.setattr(
        "hpc_gui.plugins.trusted_api3.APPROVED_API3_PINS", {(plugin_id, version): pin}
    )
    manifest = SimpleNamespace(
        id=plugin_id, version=version, publisher="HPC Client GUI", plugin_api=3,
        capabilities=["linter-tool"], entrypoints={"linter_engine": rel},
        files=[SimpleNamespace(path=rel, role="linter-engine",
                               sha256=hashlib.sha256(engine).hexdigest())],
    )
    installed = SimpleNamespace(manifest=manifest, directory=str(package))
    module_name = linter_tools._tool_module_name(installed)
    try:
        module = linter_tools._load_api3_engine_verified(installed, rel)
        assert module.__hpc_api3__ is True
        result = module.lint_text("application simpleFoam;\n", file_name="system/controlDict")
        assert "system/controlDict" in result.files_checked
        assert engine_api.lint_text("application simpleFoam;\n").files_checked == ("<memory>",)
    finally:
        linter_tools._remove_api3_finder(module_name)
        linter_tools._remove_module_namespace(module_name)
    assert module_name not in __import__("sys").modules
