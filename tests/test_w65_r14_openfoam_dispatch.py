"""W65 r14: scoped OpenFOAM host dispatch integration (unit-only).

Unit tests only; GUI acceptance remains for the interactive guest run via
``Invoke-Windows11Interactive.ps1`` (``test_w65_r2_gui.py``). No pytest run
here, no execution, no network.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from hpc_gui.plugins import models
from hpc_gui.plugins.trusted_api3 import (
    API3_LINTER_ID,
    API3_LINTER_VERSION,
    API3_STUDIO_ID,
    API3_STUDIO_VERSION,
    Api3Pin,
    api3_error_for_dir,
)
from hpc_gui.services import plugin_menu_actions as pma
from hpc_gui.services.wx_plugin_menu_host import WxPluginMenuHost
from hpc_gui.ui.plugin_menu_qt_host import QtPluginMenuHost

ENGINE_REL = "engine/openfoam_lint/__init__.py"
TEMPLATES_REL = "templates/index.json"
STUDIO_ENGINE_REL = "engine/openfoam_studio/__init__.py"
ENGINE_SRC = (
    "def create_plugin():\n"
    "    return {'id': 'org.hpcclient.openfoamlint', 'title': 'OF Linter',\n"
    "            'description': 'd',\n"
    "            'page_factory': lambda parent=None, **kw: object(),\n"
    "            'wx_page_factory': lambda parent=None, **kw: object()}\n"
    "SUPPORTED_SUFFIXES = frozenset()\n"
).encode()
TEMPLATES_SRC = b'{"schema_version": 1, "templates": []}'
STUDIO_ENGINE_SRC = (
    "from types import SimpleNamespace\n"
    "def _wx(parent=None, *, plugin, session_state=None, initial_path=None, remote=False, **kwargs):\n"
    "    return SimpleNamespace(action=kwargs.get('action'))\n"
    "def _qt(parent=None, *, plugin, session_state=None, initial_path=None, remote=False, **kwargs):\n"
    "    return SimpleNamespace(action=kwargs.get('action'))\n"
    "def create_plugin():\n"
    "    return {'id': 'org.hpcclient.openfoamcasestudio', 'title': 'Studio',\n"
    "            'wx_page_factory': _wx, 'qt_page_factory': _qt}\n"
).encode()
STUDIO_ENGINE_BOOM_SRC = (
    "def _wx(*args, **kwargs):\n"
    "    raise RuntimeError('page exploded')\n"
    "def _qt(*args, **kwargs): return object()\n"
    "def create_plugin():\n"
    "    return {'id': 'org.hpcclient.openfoamcasestudio', 'title': 'Studio',\n"
    "            'wx_page_factory': _wx, 'qt_page_factory': _qt}\n"
).encode()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_package(tmp_path: Path, manifest: dict, payloads: dict[str, bytes]) -> Path:
    payloads = dict(payloads)
    if manifest.get("id") == API3_STUDIO_ID:
        payloads.setdefault(STUDIO_ENGINE_REL, STUDIO_ENGINE_SRC)
        payloads.setdefault(TEMPLATES_REL, TEMPLATES_SRC)
    package = tmp_path / "plugins" / "packages" / manifest["id"] / manifest["version"]
    package.mkdir(parents=True, exist_ok=True)
    (package / "manifest.json").write_bytes(json.dumps(manifest).encode())
    for rel, data in payloads.items():
        target = package / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return package


def _linter_manifest(manifest_bytes_holder: dict | None = None) -> tuple[dict, Path | None]:
    manifest = {
        "schema_version": 1, "plugin_api": 3, "id": API3_LINTER_ID,
        "name": "OpenFOAM Linter", "version": API3_LINTER_VERSION,
        "publisher": "HPC Client GUI", "license": "MIT", "description": "d",
        "requires_app": ">=1.5.9", "capabilities": ["linter-tool"],
        "entrypoints": {"linter_engine": ENGINE_REL},
        "files": [{"path": ENGINE_REL, "sha256": _sha(ENGINE_SRC),
                   "size": len(ENGINE_SRC), "role": "linter-engine"}],
    }
    return manifest, None


def _studio_manifest() -> dict:
    return {
        "schema_version": 1, "plugin_api": 3, "id": API3_STUDIO_ID,
        "name": "Studio", "version": API3_STUDIO_VERSION,
        "publisher": "HPC Client GUI", "license": "MIT", "description": "d",
        "requires_app": ">=1.5.9",
        "capabilities": ["application-tools", "job-template"],
        "entrypoints": {"application_tool": STUDIO_ENGINE_REL,
                        "job_templates": TEMPLATES_REL},
        "files": [
            {"path": STUDIO_ENGINE_REL, "sha256": _sha(STUDIO_ENGINE_SRC),
             "size": len(STUDIO_ENGINE_SRC), "role": "application-engine"},
            {"path": TEMPLATES_REL, "sha256": _sha(TEMPLATES_SRC),
             "size": len(TEMPLATES_SRC), "role": "template-index"},
        ],
    }


def _installed(manifest: dict, package: Path) -> models.InstalledPlugin:
    import hpc_gui.plugins.storage as storage

    files = tuple(
        models.PluginFile(path=e["path"], sha256=e["sha256"], size=e["size"], role=e["role"])
        for e in manifest["files"]
    )
    wrapped = models.PluginManifest(
        schema_version=manifest["schema_version"], plugin_api=manifest["plugin_api"],
        id=manifest["id"], name=manifest["name"], version=manifest["version"],
        publisher=manifest["publisher"], license=manifest["license"],
        description=manifest["description"], requires_app=manifest["requires_app"],
        capabilities=tuple(manifest["capabilities"]),
        entrypoints=dict(manifest["entrypoints"]), files=files,
    )
    engine = {"module": ENGINE_REL} if manifest["id"] == API3_LINTER_ID else None
    application_tool = {"module": STUDIO_ENGINE_REL} if manifest["id"] == API3_STUDIO_ID else None
    plugin_root = package.parents[2]
    storage.write_active_versions({manifest["id"]: manifest["version"]}, root=plugin_root)
    storage.write_disabled_ids(set(), root=plugin_root)
    return models.InstalledPlugin(
        manifest=wrapped, directory=package, plugin_root=plugin_root,
        linter_engine=engine, application_tool=application_tool,
    )


def _pins_for(manifest: dict, manifest_bytes: bytes):
    if manifest["id"] == API3_LINTER_ID:
        pin = Api3Pin(API3_LINTER_ID, API3_LINTER_VERSION,
                      capabilities=("linter-tool",),
                      entrypoints=(("linter_engine", ENGINE_REL),),
                      files=((ENGINE_REL, "linter-engine", _sha(ENGINE_SRC)),),
                      manifest_sha256=_sha(manifest_bytes))
    else:
        pin = Api3Pin(API3_STUDIO_ID, API3_STUDIO_VERSION,
                      capabilities=("application-tools", "job-template"),
                      entrypoints=(("application_tool", STUDIO_ENGINE_REL),
                                   ("job_templates", TEMPLATES_REL)),
                      files=((STUDIO_ENGINE_REL, "application-engine", _sha(STUDIO_ENGINE_SRC)),
                             (TEMPLATES_REL, "template-index", _sha(TEMPLATES_SRC))),
                      manifest_sha256=_sha(manifest_bytes))
    return {(pin.plugin_id, pin.version): pin}


def _wx_frame_context(monkeypatch):
    """Model an active wx application and record the page mounted in its frame."""
    import sys

    frames = []

    class Sizer:
        def __init__(self):
            self.children = []

        def Add(self, child, proportion, flags):
            self.children.append((child, proportion, flags))

    class Frame:
        def __init__(self, parent, *, title):
            self.parent = parent
            self.title = title
            self.sizer = None
            self.visible = False
            self.size = None
            frames.append(self)

        def SetSize(self, size):
            self.size = size

        def SetSizer(self, sizer):
            self.sizer = sizer

        def GetSizer(self):
            return self.sizer

        def Layout(self):
            pass

        def Show(self):
            self.visible = True

        def Destroy(self):
            self.destroyed = True

    monkeypatch.setitem(
        sys.modules,
        "wx",
        SimpleNamespace(
            GetApp=lambda: object(), Frame=Frame,
            BoxSizer=lambda _orientation: Sizer(), VERTICAL=1, EXPAND=2,
        ),
    )
    application_frame = object()
    editor = SimpleNamespace(
        GetParent=lambda: application_frame,
        session_state={"session": {"connection_id": "test-session"}},
    )
    return editor, frames


def _qt_dialog_context(monkeypatch):
    from PySide6 import QtWidgets

    dialogs = []

    class Dialog:
        def __init__(self, parent):
            self.parent = parent
            self.title = ""
            self.widget = None
            self.executed = False
            dialogs.append(self)

        def setWindowTitle(self, title):
            self.title = title

        def resize(self, *_size):
            pass

        def exec(self):
            self.executed = True
            return 0

    class Layout:
        def __init__(self, dialog):
            self.dialog = dialog
            self.widget = None

        def addWidget(self, widget):
            self.widget = widget
            self.dialog.widget = widget

    monkeypatch.setattr(QtWidgets, "QDialog", Dialog)
    monkeypatch.setattr(QtWidgets, "QVBoxLayout", Layout)
    return object(), dialogs


def _legacy_short(plugin_id: str) -> models.InstalledPlugin:
    caps = ("application-tools",) if "studio" in plugin_id else ("lint-rules", "linter-tool")
    manifest = models.PluginManifest(
        schema_version=1, plugin_api=1, id=plugin_id, name="x",
        version="0.2.0-w65r17-auditfix1" if "linter" in plugin_id else "0.3.0-w65r17-auditfix1",
        publisher="HPC Client GUI", license="t", description="t",
        requires_app=">=1.5.9", capabilities=caps, entrypoints={}, files=(),
    )
    return models.InstalledPlugin(manifest=manifest, directory=Path("."))


def test_legacy_short_ids_stay_pending():
    for action, plugin in (("openfoam.open_studio", _legacy_short("openfoam-case-studio")),
                           ("openfoam.validate", _legacy_short("openfoam-linter"))):
        allowed, reason = pma.can_execute_action(action, plugin)
        assert allowed is False and reason == pma.OPENFOAM_PENDING_REASON
    assert pma.is_openfoam_dispatch_ready(_legacy_short("openfoam-case-studio")) is False


def test_empty_production_pins_fail_closed(tmp_path: Path):
    manifest = _studio_manifest()
    package = _write_package(tmp_path, manifest, {TEMPLATES_REL: TEMPLATES_SRC})
    installed = _installed(manifest, package)
    allowed, reason = pma.can_execute_action("openfoam.open_studio", installed)
    assert allowed is False and "no host release pin" in reason
    assert api3_error_for_dir(installed.manifest, package) is not None
    assert pma.is_openfoam_dispatch_ready(installed) is False
    assert WxPluginMenuHost().run_openfoam_studio(installed) is False
    assert QtPluginMenuHost().run_openfoam_studio(installed) is False


def test_wrong_ids_never_fall_back(tmp_path: Path, monkeypatch):
    manifest = _studio_manifest()
    manifest_bytes = json.dumps(manifest).encode()
    import hpc_gui.plugins.trusted_api3 as t3

    monkeypatch.setattr(t3, "APPROVED_API3_PINS", _pins_for(manifest, manifest_bytes))
    package = _write_package(tmp_path, manifest, {TEMPLATES_REL: TEMPLATES_SRC})
    studio = _installed(manifest, package)
    # Linter-owned action with the studio plugin must fail, not route to linter.
    allowed, reason = pma.can_execute_action("openfoam.validate", studio)
    assert allowed is False and ("capability" in reason or "owning plugin" in reason)
    assert pma.dispatch_plugin_menu_action("openfoam.validate", studio, WxPluginMenuHost()) is False
    # Unknown/foreign identity with correct caps is rejected by exact id.
    evil_manifest = models.PluginManifest(
        schema_version=1, plugin_api=3, id="evil.plugin", name="x", version="1.0.0",
        publisher="HPC Client GUI", license="t", description="t", requires_app=">=1.5.9",
        capabilities=("application-tools", "job-template"), entrypoints={}, files=(),
    )
    evil = models.InstalledPlugin(manifest=evil_manifest, directory=Path("."))
    allowed, reason = pma.can_execute_action("openfoam.open_studio", evil)
    assert allowed is False and "owning plugin" in reason


def test_capability_and_compat_guards_fire_first():
    bare = models.InstalledPlugin(
        manifest=models.PluginManifest(
            schema_version=1, plugin_api=3, id=API3_STUDIO_ID, name="x",
            version=API3_STUDIO_VERSION, publisher="HPC Client GUI", license="t",
            description="t", requires_app=">=1.5.9", capabilities=(),
            entrypoints={"job_templates": TEMPLATES_REL}, files=()),
        directory=Path("."))

    allowed, reason = pma.can_execute_action("openfoam.open_studio", bare)
    assert allowed is False and "capability" in reason
    bad_req = models.InstalledPlugin(
        manifest=models.PluginManifest(
            schema_version=1, plugin_api=3, id=API3_STUDIO_ID, name="x",
            version=API3_STUDIO_VERSION, publisher="HPC Client GUI", license="t",
            description="t", requires_app=">=99.0.0",
            capabilities=("application-tools", "job-template"),
            entrypoints={"job_templates": TEMPLATES_REL}, files=()),
        directory=Path("."))
    allowed, reason = pma.can_execute_action("openfoam.open_studio", bad_req)
    assert allowed is False and "incompatible" in reason


def test_tamper_fails_closed(tmp_path: Path, monkeypatch):
    import hpc_gui.plugins.trusted_api3 as t3

    manifest, _ = _linter_manifest()
    manifest_bytes = json.dumps(manifest).encode()
    monkeypatch.setattr(t3, "APPROVED_API3_PINS", _pins_for(manifest, manifest_bytes))
    package = _write_package(tmp_path, manifest, {ENGINE_REL: ENGINE_SRC})
    installed = _installed(manifest, package)
    assert pma.can_execute_action("openfoam.validate", installed)[0] is True
    (package / ENGINE_REL).write_bytes(ENGINE_SRC + b"# tampered\n")
    allowed, reason = pma.can_execute_action("openfoam.validate", installed)
    assert allowed is False and ("mismatch" in reason or "integrity" in reason or "digest" in reason)
    assert pma.dispatch_plugin_menu_action("openfoam.validate", installed, WxPluginMenuHost()) is False


def test_missing_callback_blocks_without_fallback(tmp_path: Path, monkeypatch):
    import hpc_gui.plugins.trusted_api3 as t3

    manifest = _studio_manifest()
    manifest_bytes = json.dumps(manifest).encode()
    monkeypatch.setattr(t3, "APPROVED_API3_PINS", _pins_for(manifest, manifest_bytes))
    package = _write_package(tmp_path, manifest, {TEMPLATES_REL: TEMPLATES_SRC})
    installed = _installed(manifest, package)
    assert pma.can_execute_action("openfoam.open_studio", installed)[0] is True
    # No host: dispatch must fail, not execute.
    assert pma.dispatch_plugin_menu_action("openfoam.open_studio", installed) is False
    # Host missing the method: fail closed with explicit reason, no fallback.
    assert pma.dispatch_plugin_menu_action(
        "openfoam.open_studio", installed, SimpleNamespace()) is False
    ok, reason = pma._openfoam_gate("openfoam.open_studio", installed, host=SimpleNamespace())
    assert ok is False and "host callback" in reason


def test_disabled_or_inactive_plugin_blocks_at_dispatch(tmp_path: Path, monkeypatch):
    import hpc_gui.plugins.trusted_api3 as t3
    import hpc_gui.plugins.storage as storage

    manifest = _studio_manifest()
    manifest_bytes = json.dumps(manifest).encode()
    monkeypatch.setattr(t3, "APPROVED_API3_PINS", _pins_for(manifest, manifest_bytes))
    package = _write_package(tmp_path, manifest, {TEMPLATES_REL: TEMPLATES_SRC})
    installed = _installed(manifest, package)
    root = package.parents[2]
    storage.write_active_versions({manifest["id"]: manifest["version"]}, root=root)
    host = WxPluginMenuHost()

    storage.write_disabled_ids({manifest["id"]}, root=root)
    allowed, reason = pma.can_execute_action("openfoam.open_studio", installed)
    assert allowed is False and reason == "plugin is disabled"
    assert pma.dispatch_plugin_menu_action("openfoam.open_studio", installed, host) is False

    storage.write_disabled_ids(set(), root=root)
    storage.write_active_versions({}, root=root)
    allowed, reason = pma.can_execute_action("openfoam.open_studio", installed)
    assert allowed is False and reason == "plugin version is not the currently active version"


def test_wx_linter_validate_uses_verified_bytes(tmp_path: Path, monkeypatch):
    import hpc_gui.plugins.trusted_api3 as t3

    manifest, _ = _linter_manifest()
    manifest_bytes = json.dumps(manifest).encode()
    monkeypatch.setattr(t3, "APPROVED_API3_PINS", _pins_for(manifest, manifest_bytes))
    package = _write_package(tmp_path, manifest, {ENGINE_REL: ENGINE_SRC})
    installed = _installed(manifest, package)
    editor, frames = _wx_frame_context(monkeypatch)
    host = WxPluginMenuHost(
        editor_page=editor, initial_paths=["/case/0/U"],
        session_state=editor.session_state,
    )
    assert host.validate_with_openfoam_linter(installed) is True
    assert len(frames) == 1 and frames[0].visible
    assert frames[0].title == f"OF Linter — {API3_LINTER_ID}"
    assert frames[0].sizer.children[0][0] is not None
    assert pma.dispatch_plugin_menu_action("openfoam.validate", installed, host) is True
    # Wrong plugin never falls back to the linter engine.
    studio_manifest = _studio_manifest()
    studio_bytes = json.dumps(studio_manifest).encode()
    monkeypatch.setattr(t3, "APPROVED_API3_PINS", _pins_for(studio_manifest, studio_bytes))
    studio_pkg = _write_package(tmp_path / "s", studio_manifest, {TEMPLATES_REL: TEMPLATES_SRC})
    studio = _installed(studio_manifest, studio_pkg)
    assert host.validate_with_openfoam_linter(studio) is False


def test_qt_linter_and_studio_route_through_pinned_descriptors(tmp_path: Path, monkeypatch):
    import hpc_gui.plugins.trusted_api3 as t3

    manifest, _ = _linter_manifest()
    manifest_bytes = json.dumps(manifest).encode()
    studio_manifest = _studio_manifest()
    studio_bytes = json.dumps(studio_manifest).encode()
    monkeypatch.setattr(
        t3, "APPROVED_API3_PINS",
        _pins_for(manifest, manifest_bytes) | _pins_for(studio_manifest, studio_bytes),
    )
    package = _write_package(tmp_path, manifest, {ENGINE_REL: ENGINE_SRC})
    installed = _installed(manifest, package)
    window, dialogs = _qt_dialog_context(monkeypatch)
    qhost = QtPluginMenuHost(editor_widget=None, host_window=window)
    assert qhost.validate_with_openfoam_linter(installed) is True
    assert len(dialogs) == 1 and dialogs[0].executed
    assert dialogs[0].widget is not None
    studio_package = _write_package(tmp_path / "studio", studio_manifest, {})
    studio = _installed(studio_manifest, studio_package)
    assert qhost.run_openfoam_studio(studio) is True
    assert qhost.new_openfoam_case(studio) is True
    assert qhost.create_openfoam_job_draft(studio) is True
    assert len(dialogs) == 4 and all(dialog.widget is not None for dialog in dialogs)


def test_wx_studio_routes_to_owned_page(tmp_path: Path, monkeypatch):
    import hpc_gui.plugins.trusted_api3 as t3

    manifest = _studio_manifest()
    manifest_bytes = json.dumps(manifest).encode()
    monkeypatch.setattr(t3, "APPROVED_API3_PINS", _pins_for(manifest, manifest_bytes))
    package = _write_package(tmp_path, manifest, {
        STUDIO_ENGINE_REL: STUDIO_ENGINE_SRC, TEMPLATES_REL: TEMPLATES_SRC,
    })
    installed = _installed(manifest, package)
    editor, frames = _wx_frame_context(monkeypatch)
    host = WxPluginMenuHost(editor_page=editor)
    assert host.run_openfoam_studio(installed) is True
    assert host.new_openfoam_case(installed) is True
    assert host.create_openfoam_job_draft(installed) is True
    assert len(frames) == 3 and all(frame.visible for frame in frames)
    actions = [frame.sizer.children[0][0].action for frame in frames]
    assert actions == [None, "new", "draft"]
    assert pma.dispatch_plugin_menu_action("openfoam.open_studio", installed, host) is True
    assert len(frames) == 4 and frames[-1].visible


def test_error_isolation_between_actions(tmp_path: Path, monkeypatch):
    import hpc_gui.plugins.trusted_api3 as t3

    manifest = _studio_manifest()
    manifest_bytes = json.dumps(manifest).encode()
    monkeypatch.setattr(t3, "APPROVED_API3_PINS", _pins_for(manifest, manifest_bytes))
    package = _write_package(tmp_path, manifest, {
        STUDIO_ENGINE_REL: STUDIO_ENGINE_BOOM_SRC, TEMPLATES_REL: TEMPLATES_SRC,
    })
    installed = _installed(manifest, package)
    editor, _frames = _wx_frame_context(monkeypatch)
    host = WxPluginMenuHost(editor_page=editor)

    def _boom(*a, **k):
        raise RuntimeError("page exploded")

    assert host.run_openfoam_studio(installed) is False
    # A failing studio action does not poison the linter path.
    lmanifest, _ = _linter_manifest()
    lbytes = json.dumps(lmanifest).encode()
    monkeypatch.setattr(t3, "APPROVED_API3_PINS", _pins_for(lmanifest, lbytes))
    lpackage = _write_package(tmp_path / "l", lmanifest, {ENGINE_REL: ENGINE_SRC})
    linter = _installed(lmanifest, lpackage)
    editor, frames = _wx_frame_context(monkeypatch)
    assert WxPluginMenuHost(editor_page=editor).validate_with_openfoam_linter(linter) is True
    assert len(frames) == 1 and frames[0].visible


def test_job_draft_stays_review_only():
    repo = Path(__file__).resolve().parents[1]
    host_src = (repo / "src" / "hpc_gui" / "services" / "wx_plugin_menu_host.py").read_text(
        encoding="utf-8")
    actions_src = (repo / "src" / "hpc_gui" / "services" / "plugin_menu_actions.py").read_text(
        encoding="utf-8")
    for forbidden in ("sbatch", "subprocess", "Popen", "os.system", "shell=True"):
        assert forbidden not in host_src
        assert forbidden not in actions_src
    store_src = (repo / "src" / "hpc_gui" / "plugin_engines" / "openfoam_studio"
                 / "run_script_store.py").read_text(encoding="utf-8")
    assert "O_EXCL" in store_src and "FileExistsError" in store_src
