"""W65 r12: safe host-owned integration fixes (HOST-002/G02, LINT-013/G38).

Implements the two concrete gaps accepted in r10/r11:

1. Application-owned explicit trust approval plus a matching linter-engine
   entrypoint for the verified OpenFOAM Linter plugin identity
   (``openfoam-linter`` / ``HPC Client GUI`` /
   ``engine/openfoam_lint/__init__.py``). Manifests still cannot
   self-authorize: publisher/entrypoint/capability/API mismatches stay
   rejected, and the engine module itself is inert (static lint only, wx
   page factory fails closed).
2. A narrow host-owned File-context contribution/dispatch extension for
   the OpenFOAM case actions (``of.newCase``/``of.openStudio``/
   ``of.validate``/``of.createJob``) using validated ids/capabilities and
   safe no-op/disabled behavior until plugin/host readiness is verified.

No solver/HPC execution, no UI construction, no manifest/installer/loader
edits, no i18n string changes (of.* labels reuse paired openfoam.* keys).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from hpc_gui.plugins import models
from hpc_gui.plugins.linter_tools import ToolLoadError, load_tool_for_plugin
from hpc_gui.plugins.openfoam_lint import (
    ENGINE_ENTRYPOINT,
    PLUGIN_ID as LINTER_PLUGIN_ID,
    SUPPORTED_SUFFIXES,
    create_plugin,
)
from hpc_gui.plugins.trusted_tools import (
    APPROVED_TRUSTED_TOOLS,
    TRUSTED_TOOL_API_VERSION,
    is_approved_trusted_tool,
    trusted_tool_error,
)
from hpc_gui.services import file_context_actions as fca

REPO_ROOT = Path(__file__).resolve().parents[1]

LINTER_MANIFEST = {
    "plugin_api": 2,
    "id": "openfoam-linter",
    "publisher": "HPC Client GUI",
    "capabilities": ["lint-rules", "linter-tool"],
    "entrypoints": {"linter_engine": "engine/openfoam_lint/__init__.py"},
}


def _studio_plugin() -> models.InstalledPlugin:
    manifest = models.PluginManifest(
        schema_version=1, plugin_api=1, id="openfoam-case-studio",
        name="OpenFOAM Case Studio", version="0.3.0-w65r17-auditfix1",
        publisher="HPC Client GUI", license="test", description="test",
        requires_app=">=1.5.9", capabilities=("application-tools",),
        entrypoints={}, files=(),
    )
    return models.InstalledPlugin(manifest=manifest, directory=Path("."))


def _linter_plugin() -> models.InstalledPlugin:
    manifest = models.PluginManifest(
        schema_version=1, plugin_api=1, id="openfoam-linter",
        name="OpenFOAM Linter", version="0.2.0-w65r17-auditfix1",
        publisher="HPC Client GUI", license="test", description="test",
        requires_app=">=1.5.9", capabilities=("lint-rules", "linter-tool"),
        entrypoints={}, files=(),
    )
    return models.InstalledPlugin(manifest=manifest, directory=Path("."))


# --- fix 1: application-owned trust approval -----------------------------


def test_trust_approves_verified_openfoam_linter_identity():
    assert LINTER_PLUGIN_ID == "openfoam-linter"
    assert ENGINE_ENTRYPOINT == "engine/openfoam_lint/__init__.py"
    assert trusted_tool_error(LINTER_MANIFEST) is None
    assert is_approved_trusted_tool(LINTER_MANIFEST) is True


def test_trust_entry_matches_verified_engine_module():
    policy = APPROVED_TRUSTED_TOOLS["openfoam-linter"]
    assert policy["entrypoint"] == ENGINE_ENTRYPOINT
    assert policy["publisher"] == "HPC Client GUI"
    assert policy["api"] == TRUSTED_TOOL_API_VERSION
    # The ANSYS approval is untouched.
    assert APPROVED_TRUSTED_TOOLS["org.hpcclient.ansyslint"]["entrypoint"] == (
        "engine/ansys_lint/__init__.py")


def test_trust_still_rejects_spoofed_openfoam_manifests():
    base = dict(LINTER_MANIFEST)
    assert trusted_tool_error({**base, "publisher": "Evil Corp"}) != ""
    assert trusted_tool_error(
        {**base, "entrypoints": {"linter_engine": "engine/evil/__init__.py"}}) != ""
    assert trusted_tool_error(
        {**base, "capabilities": ["application-tools"]}) != ""
    assert trusted_tool_error({**base, "plugin_api": 1}) != ""
    assert trusted_tool_error({**base, "id": "openfoam-linter-evil"}) != ""
    assert is_approved_trusted_tool({**base, "publisher": "Evil Corp"}) is False


# --- fix 1: matching linter-engine entrypoint ----------------------------


def _fake_openfoam_tool(tmp_path: Path, *, broken: bool = False,
                        rel: str = ENGINE_ENTRYPOINT,
                        plugin_id: str = "openfoam-linter"):
    package = tmp_path / "engine" / "openfoam_lint"
    package.mkdir(parents=True, exist_ok=True)
    if broken:
        init = "raise RuntimeError('broken')\n"
    else:
        init = (
            "from hpc_gui.plugins.openfoam_lint import (\n"
            "    SUPPORTED_SUFFIXES, create_plugin, lint_paths, lint_text,\n"
            ")\n"
        )
    init_path = package / "__init__.py"
    init_path.write_text(init, encoding="utf-8")
    data = init.encode()
    files = (models.PluginFile(
        path="engine/openfoam_lint/__init__.py",
        sha256=hashlib.sha256(data).hexdigest(), size=len(data),
        role="linter-engine"),)
    manifest = models.PluginManifest(
        schema_version=1, plugin_api=2, id=plugin_id,
        name="OpenFOAM Linter", version="0.2.0-w65r17-auditfix1",
        publisher="HPC Client GUI", license="test", description="test",
        requires_app=">=1.5.9", capabilities=("lint-rules", "linter-tool"),
        entrypoints={"linter_engine": rel}, files=files)
    return models.InstalledPlugin(
        manifest=manifest, directory=tmp_path, linter_engine={"module": rel})


def test_engine_loads_through_approved_entrypoint(tmp_path: Path):
    installed = _fake_openfoam_tool(tmp_path)
    tool = load_tool_for_plugin(installed)
    assert tool.plugin_id == "openfoam-linter"
    assert tool.version == "0.2.0-w65r17-auditfix1"
    assert tool.title == create_plugin()["title"] == "OpenFOAM Linter"


def test_engine_lints_static_without_execution(tmp_path: Path):
    import importlib

    tool = load_tool_for_plugin(_fake_openfoam_tool(tmp_path))
    module = importlib.import_module(tool.module_name)
    diags = module.lint_text("application simpleFoam\n",
                             file_name="system/controlDict")
    assert any(d.rule == "OF-DICT-001" for d in diags)  # malformed dictionary structure
    sec = module.lint_text("#codeStream\n{\ncode 1;\n}\n", file_name="0/U")
    assert any(d.rule == "OF-SEC-001" for d in sec)  # flagged, not executed
    case = tmp_path / "case"
    (case / "system").mkdir(parents=True)
    (case / "system" / "controlDict").write_text(
        "application simpleFoam\n", encoding="utf-8")
    found = module.lint_paths([case])
    assert any(d.file.endswith("controlDict") for d in found)
    missing = module.lint_paths([tmp_path / "missing"])
    assert any(d.rule == "OF-CASE-006" for d in missing)


def test_engine_page_factory_fails_closed():
    with pytest.raises(RuntimeError, match="no wx tool page"):
        create_plugin()["page_factory"](parent=None)


def test_engine_suffix_routing_explicitly_unsupported(tmp_path: Path):
    from hpc_gui.plugins.linter_tools import tool_supported_suffixes

    assert SUPPORTED_SUFFIXES == frozenset()
    tool = load_tool_for_plugin(_fake_openfoam_tool(tmp_path))
    assert tool_supported_suffixes(tool) == frozenset()


def test_engine_rejects_unapproved_entrypoints(tmp_path: Path):
    # Manifest entrypoint diverging from the approved policy entrypoint
    # fails at the trust gate (fail closed, no import).
    with pytest.raises(ToolLoadError, match="disabled"):
        load_tool_for_plugin(_fake_openfoam_tool(
            tmp_path, rel="engine/ansys_lint/__init__.py"))
    # An approved manifest whose recorded engine module diverges from the
    # policy entrypoint fails at the entrypoint gate (never imported).
    approved = _fake_openfoam_tool(tmp_path)
    with pytest.raises(ToolLoadError, match="not approved"):
        load_tool_for_plugin(models.InstalledPlugin(
            manifest=approved.manifest, directory=tmp_path,
            linter_engine={"module": "engine/evil/__init__.py"}))
    with pytest.raises(ToolLoadError, match="disabled"):
        load_tool_for_plugin(_fake_openfoam_tool(
            tmp_path, plugin_id="openfoam-linter-evil"))
    # An approved manifest whose engine file is absent fails closed.
    with pytest.raises(ToolLoadError, match="missing"):
        approved = _fake_openfoam_tool(tmp_path)
        load_tool_for_plugin(models.InstalledPlugin(
            manifest=approved.manifest, directory=tmp_path / "empty",
            linter_engine={"module": ENGINE_ENTRYPOINT}))
    with pytest.raises(ToolLoadError):
        load_tool_for_plugin(_fake_openfoam_tool(tmp_path, broken=True))


# --- fix 2: host-owned file-context extension ----------------------------


def _one_dir():
    return fca.context_selection("cavity", True, ("cavity",), (True,))


def _one_file():
    return fca.context_selection("case.foam", False, ("case.foam",), (False,))


def test_file_context_requires_an_application_pinned_api3_plugin():
    assert fca.is_openfoam_file_context_ready() is False
    for selection in (_one_dir(), _one_file()):
        assert fca.openfoam_file_context_actions(selection, _studio_plugin()) == ()
        assert fca.openfoam_file_context_actions(
            selection, _linter_plugin(), remote=True) == ()


def test_file_context_rejects_unpinned_identity_and_shape():
    evil = models.InstalledPlugin(
        manifest=models.PluginManifest(
            schema_version=1, plugin_api=1, id="openfoam-case-studio",
            name="x", version="0.3.0-w65r17-auditfix1", publisher="Evil Corp",
            license="test", description="test", requires_app=">=1.5.9",
            capabilities=("application-tools",), entrypoints={}, files=()),
        directory=Path("."))
    assert fca.openfoam_file_context_actions(_one_dir(), evil) == ()
    unknown = models.InstalledPlugin(
        manifest=models.PluginManifest(
            schema_version=1, plugin_api=1, id="openfoam-evil",
            name="x", version="1.0.0", publisher="HPC Client GUI",
            license="test", description="test", requires_app=">=1.5.9",
            capabilities=("application-tools",), entrypoints={}, files=()),
        directory=Path("."))
    assert fca.openfoam_file_context_actions(_one_dir(), unknown) == ()
    bare = models.InstalledPlugin(
        manifest=models.PluginManifest(
            schema_version=1, plugin_api=1, id="openfoam-case-studio",
            name="x", version="0.3.0-w65r17-auditfix1", publisher="HPC Client GUI",
            license="test", description="test", requires_app=">=1.5.9",
            capabilities=(), entrypoints={}, files=()),
        directory=Path("."))
    assert fca.openfoam_file_context_actions(_one_dir(), bare) == ()
    background = fca.context_selection(None, None, (), (), background=True)
    assert fca.openfoam_file_context_actions(background, _studio_plugin()) == ()
    empty = fca.context_selection(None, None, (), ())
    assert fca.openfoam_file_context_actions(empty, _studio_plugin()) == ()
    multi = fca.context_selection("a", False, ("a", "b"), (False, False))
    assert fca.openfoam_file_context_actions(multi, _studio_plugin()) == ()


def test_file_context_visible_path_unchanged():
    for selection in (_one_dir(), _one_file()):
        for remote in (False, True):
            seen = set(fca.visible_actions(selection, remote=remote))
            assert not any("openfoam" in action for action in seen)
            assert not any(action.startswith("of.") for action in seen)


def test_file_context_dispatch_rejects_legacy_unpinned_packages():
    studio, linter = _studio_plugin(), _linter_plugin()
    ok, reason = fca.dispatch_openfoam_file_context_action("of.bogus", studio)
    assert ok is False and "unknown" in reason
    ok, reason = fca.dispatch_openfoam_file_context_action(
        "of.newCase", studio, _one_dir())
    assert ok is False and "approved owner" in reason
    ok, reason = fca.dispatch_openfoam_file_context_action(
        "of.validate", studio, _one_dir())
    assert ok is False and "approved owner" in reason
    ok, reason = fca.dispatch_openfoam_file_context_action(
        "of.validate", linter, _one_dir())
    assert ok is False and "approved owner" in reason


def test_file_context_label_keys_reuse_paired_i18n():
    en = json.loads((REPO_ROOT / "src" / "hpc_gui" / "i18n" / "en.json").read_text(
        encoding="utf-8"))["openfoam"]
    tr = json.loads((REPO_ROOT / "src" / "hpc_gui" / "i18n" / "tr.json").read_text(
        encoding="utf-8"))["openfoam"]
    assert set(en) == set(tr)
    for action in fca.OPENFOAM_FILE_CONTEXT_IDS:
        key = fca.FILE_CONTEXT_LABEL_KEYS[action]
        assert key.startswith("openfoam.")
        assert en[key.removeprefix("openfoam.")].strip()
        assert tr[key.removeprefix("openfoam.")].strip()
