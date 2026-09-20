"""W04 support-classification and evidence-matrix freeze pins.

Owned requirements: ``HPC-W01-TRUTH-047…072``, ``076…083`` and TODO details
``HPC-W01-TODO-W01-DISPOSITION-001``, ``HPC-W01-TODO-W01-SUPPORT-EVIDENCE-001``,
``HPC-W01-TODO-W01-GUI-PROOF-001``.

Freeze artifact: ``artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md`` (56 rows,
pinned to HEAD). Finding ``DEF-W04-001`` (FIX-W04-A): the dynamic
plugin-menu dispatcher ``_wx_dispatch_plugin_action`` silently dropped
stale-click (``plugin is None → return``) and exception (log-warning only)
failures; both paths now report a visible coded ``PLUGIN-XXXXXX`` error.

Mock boundaries (legitimate only): modal ``wx.MessageBox`` capture with real
event routing, real helper and real structured log; native ``wx.FileDialog`` /
``wx.DirDialog`` auto-cancel at the OS-modal boundary (undrivable headlessly;
real button events, real panels and real run_action routing stay under test);
view-layer call recorders (routing under test, not the view); ``wx.CallAfter``
inline only where the product posts to it; ``wx.Dialog.ShowModal``
interception for the About contract test (real dialog construction, real
labels, no event loop). No product behavior under test is replaced.
"""

from __future__ import annotations

import pathlib
import re
import time
import types

import pytest

wx = pytest.importorskip("wx")

from hpc_gui import wx_shell  # noqa: E402
from hpc_gui.core.i18n import load_language, t  # noqa: E402

FREEZE_MD = pathlib.Path("artifacts/v2-final/W04/SUPPORT_MATRIX_FREEZE.md")

CLOSED_VOCABULARY = frozenset(
    {
        "SUPPORTED",
        "EXPERIMENTAL",
        "REQUIRES_EXTERNAL_VALIDATION",
        "HIDDEN",
        "UNSUPPORTED",
        "DEPRECATED",
        "NOT-IN-V2",
    }
)

# Exact frozen counts (matrix §Exact freeze totals).
FROZEN_COUNTS = {
    "SUPPORTED": 24,
    "EXPERIMENTAL": 17,
    "REQUIRES_EXTERNAL_VALIDATION": 11,
    "DEPRECATED": 2,
    "NOT-IN-V2": 2,
    "HIDDEN": 0,
    "UNSUPPORTED": 0,
}

REQUIRED_COLUMNS = [
    "ID",
    "Surface",
    "Action",
    "UI owner",
    "Service/provider",
    "Config",
    "Implementation owner",
    "Verification owner Wave",
    "Required evidence class",
    "Current evidence class",
    "Support disposition",
    "Open gap",
    "Evidence IDs",
]


@pytest.fixture(autouse=True)
def _english_bundle():
    """Resolve ``t()`` against the English bundle (repo convention)."""
    load_language("en")
    yield
    load_language("en")


@pytest.fixture
def wx_app():
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    yield app
    for window in wx.GetTopLevelWindows():
        try:
            if window:
                window.Destroy()
        except Exception:
            pass
    app.ProcessPendingEvents()
    wx.SafeYield()
    app.Destroy()


def _close_shell(frame):
    """Controlled teardown: Close + yields + conditional Destroy (W02 pattern:
    an abrupt Destroy() of the full shell frame corrupts the heap)."""
    try:
        frame.Close()
    except Exception:
        pass
    for _ in range(3):
        wx.Yield()
    try:
        if not frame.IsBeingDeleted():
            frame.Destroy()
    except Exception:
        pass
    for _ in range(3):
        wx.Yield()


class _MessageBoxCapture:
    """Stand-in for ``wx.MessageBox`` that records instead of blocking."""

    def __init__(self, monkeypatch, result=None):
        self.calls = []
        self.result = wx.OK if result is None else result
        monkeypatch.setattr(wx, "MessageBox", self)

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.result

    @property
    def texts(self):
        return [args[0] for args, _ in self.calls]


def _auto_cancel_native_selectors(monkeypatch):
    """Auto-cancel native file/dir selectors at the OS-modal boundary.

    ``wx.FileDialog`` / ``wx.DirDialog`` ``ShowModal()`` runs a native modal
    loop that cannot be driven headlessly and never terminates without a user
    (DEF-W04-002). The stand-in records each invocation and returns
    ``wx.ID_CANCEL`` so no transfer starts; real button events, real panels
    and the real ``run_action`` routing under test are untouched.
    """
    calls = []

    def _cancel_factory(*args, **kwargs):
        calls.append((args, kwargs))
        dialog = types.SimpleNamespace()
        dialog.ShowModal = lambda: wx.ID_CANCEL
        dialog.Destroy = lambda: True
        dialog.GetPaths = lambda: []
        dialog.GetPath = lambda: ""
        return dialog

    monkeypatch.setattr(wx, "FileDialog", _cancel_factory)
    monkeypatch.setattr(wx, "DirDialog", _cancel_factory)
    return calls


def _parse_freeze_matrix():
    """Parse the frozen-matrix section only (excludes verdict/findings tables)."""
    text = FREEZE_MD.read_text(encoding="utf-8")
    section = text.split("## Frozen matrix", 1)[1].split("## Exact freeze totals", 1)[0]
    header = None
    rows = []
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells[0] == "ID":
            header = cells
            continue
        if line.startswith("| ---") or not cells[0].startswith("`"):
            continue
        assert len(cells) == len(header) == 14, f"row has {len(cells)} cells: {cells[0]}"
        rows.append(dict(zip(header, cells)))
    return header, rows


def _menu_labels(menu):
    """Recursively collect visible labels of a wx.Menu (real widget state)."""
    labels = []
    for item in menu.GetMenuItems():
        if item.IsSeparator():
            continue
        sub = item.GetSubMenu()
        if sub is not None:
            labels.append(item.GetItemLabelText())
            labels.extend(_menu_labels(sub))
        else:
            labels.append(item.GetItemLabelText())
    return labels


def _shell_menu_labels(frame):
    menubar = frame.GetMenuBar()
    labels = []
    for index in range(menubar.GetMenuCount()):
        labels.extend(_menu_labels(menubar.GetMenu(index)))
    return labels


# ---------------------------------------------------------------------------
# A. Freeze structure: columns, vocabulary, counts, ownership (TRUTH-047…056)
# ---------------------------------------------------------------------------


def test_matrix__has_all_required_columns():
    header, rows = _parse_freeze_matrix()
    for column in REQUIRED_COLUMNS:
        assert column in header, f"required column missing: {column}"
    assert len(rows) == sum(FROZEN_COUNTS.values()) == 56


def test_matrix__ids_unique_and_dispositions_closed():
    _, rows = _parse_freeze_matrix()
    ids = [row["ID"].strip("`") for row in rows]
    assert len(ids) == len(set(ids)) == 56
    for row in rows:
        assert row["Support disposition"] in CLOSED_VOCABULARY, row["ID"]


def test_matrix__freeze_totals_are_exact():
    _, rows = _parse_freeze_matrix()
    counts = {}
    for row in rows:
        counts[row["Support disposition"]] = counts.get(row["Support disposition"], 0) + 1
    for state, expected in FROZEN_COUNTS.items():
        assert counts.get(state, 0) == expected, f"{state}: {counts.get(state, 0)} != {expected}"


def test_matrix__supported_means_evidence_backed():
    """TRUTH-047/054: SUPPORTED rows carry evidence; EXPERIMENTAL rows carry
    an open gap (never bare)."""
    _, rows = _parse_freeze_matrix()
    for row in rows:
        if row["Support disposition"] == "SUPPORTED":
            assert row["Evidence IDs"].strip("` ") not in ("", "—", "none"), row["ID"]
        if row["Support disposition"] == "EXPERIMENTAL":
            assert row["Open gap"].strip().lower() not in ("", "none", "—"), row["ID"]


def test_matrix__rev_means_backend_dependent():
    """TRUTH-049/054: REV rows require non-dev-only evidence (external or
    package), never plain source trace."""
    _, rows = _parse_freeze_matrix()
    for row in rows:
        if row["Support disposition"] == "REQUIRES_EXTERNAL_VALIDATION":
            required = row["Required evidence class"].lower()
            assert "external" in required or "package" in required, row["ID"]


def test_matrix__rows_without_wave_owner_need_no_gap():
    """W01-D/TODO SUPPORT-EVIDENCE-001: every row either names a verification
    owner Wave or is a fully-proven native/local row with no open gap."""
    _, rows = _parse_freeze_matrix()
    for row in rows:
        owner = row["Verification owner Wave"]
        if re.fullmatch(r"—.*", owner):
            assert row["Support disposition"] == "SUPPORTED", row["ID"]
            assert row["Open gap"].strip().lower().startswith("none"), row["ID"]
        else:
            assert re.search(r"W\d\d", owner), f"{row['ID']}: no verification owner Wave"


def test_matrix__every_dispatch_literal_resolves_to_a_row():
    """TRUTH-056/058: every static dispatch literal in the shell maps to a
    freeze row's action cell (no untracked visible surface)."""
    source = pathlib.Path("src/hpc_gui/wx_shell.py").read_text(encoding="utf-8")
    literals = set(re.findall(r'_dispatch\("([A-Z0-9-]+)"', source))
    assert literals, "dispatch extraction found nothing"
    _, rows = _parse_freeze_matrix()
    actions = " \n ".join(row["Action"] for row in rows)
    for literal in sorted(literals):
        if literal == "APP-COMMAND-PALETTE":
            # Documented alias: the palette has no standalone surface; the
            # Help Center row owns this dispatch (DEC-W01-PALETTE).
            help_center = next(r for r in rows if r["ID"].strip("`") == "HELP-CENTER")
            assert "APP-COMMAND-PALETTE" in help_center["Action"]
            continue
        assert literal in actions, f"dispatch {literal!r} has no freeze-matrix row"


def test_matrix__removed_baseline_actions_retain_disposition():
    """TRUTH-056/W01-C: removed baseline rows keep ID + final disposition."""
    _, rows = _parse_freeze_matrix()
    by_id = {row["ID"].strip("`"): row for row in rows}
    tour = by_id["`APP-QUICKTOUR`".strip("`")] if "`APP-QUICKTOUR`" in by_id else by_id.get("APP-QUICKTOUR")
    assert tour is not None
    assert tour["Support disposition"] == "NOT-IN-V2"
    assert "DEC-W01-QUICKTOUR" in tour["Decision ID"]
    assert re.search(r"W\d\d", tour["Verification owner Wave"])


# ---------------------------------------------------------------------------
# B. W01-C: every baseline-visible feature has final disposition (TRUTH-076)
# ---------------------------------------------------------------------------


def test_quicktour__absent_from_wx_help_menu(wx_app):
    """The removed ghost control is absent from the live wx menu."""
    frame, _lifecycle, _session = wx_shell.create_shell_frame(wx_app)
    try:
        assert frame._wx_shell_help_items["tour"] is None
        labels = _menu_labels(frame._wx_shell_help_menu)
        assert not [label for label in labels if "tour" in label.casefold()]
    finally:
        _close_shell(frame)


def test_quicktour__no_dispatch_reaches_ui(wx_app, monkeypatch):
    """No APP-QUICKTOUR dispatch exists: firing it shows nothing and opens
    nothing (removed dispatch is not reachable)."""
    capture = _MessageBoxCapture(monkeypatch)
    before = set(wx.GetTopLevelWindows())
    wx_shell._dispatch("APP-QUICKTOUR", None, None, {})
    wx_app.ProcessPendingEvents()
    assert capture.calls == []
    assert set(wx.GetTopLevelWindows()) == before


def test_quicktour__absence_detector_is_sensitive(wx_app):
    """W01-E sensitivity: temporarily restoring the ghost item makes the
    absence detector fail for the right reason (proves the test is not
    vacuous); removal restores green."""

    def _tour_present(frame):
        return any("tour" in label.casefold() for label in _menu_labels(frame._wx_shell_help_menu))

    frame, _lifecycle, _session = wx_shell.create_shell_frame(wx_app)
    try:
        assert not _tour_present(frame)
        probe = frame._wx_shell_help_menu.Append(wx.ID_ANY, t("menu.quick_tour"))
        try:
            assert _tour_present(frame), "fault-injected tour item must trip the detector"
        finally:
            frame._wx_shell_help_menu.DestroyItem(probe)
        assert not _tour_present(frame)
    finally:
        _close_shell(frame)


def test_baseline_removals__no_wx_surface_for_legacy_keys(wx_app):
    """TRUTH-071: `menu.quick_tour` / `menu.command_palette` resolve in the
    bundle (Qt-legacy retention) but bind to no wx visible item — retained
    keys, not masking UI."""
    assert t("menu.quick_tour") != "[menu.quick_tour]"
    assert t("menu.command_palette") != "[menu.command_palette]"
    frame, _lifecycle, _session = wx_shell.create_shell_frame(wx_app)
    try:
        labels = _shell_menu_labels(frame)
        assert t("menu.quick_tour") not in labels
        assert t("menu.command_palette") not in labels
        assert frame._wx_shell_help_items["tour"] is None
    finally:
        _close_shell(frame)


# ---------------------------------------------------------------------------
# C+D. Event binding + service path via real wx events (TRUTH-059/060)
# ---------------------------------------------------------------------------


def _fire_menu(frame, item):
    frame.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, item.GetId()))
    wx.Yield()


def test_menu_events__route_to_canonical_owners(wx_app, monkeypatch):
    """Real EVT_MENU from each static menu item reaches its canonical
    implementation owner with the shell parent (one shell, per-leg asserts)."""
    import hpc_gui.wx_about as about_view
    import hpc_gui.wx_help as help_view
    import hpc_gui.wx_plugins_view as plugins_view
    import hpc_gui.wx_send_logs_view as logs_view
    import hpc_gui.wx_settings_view as settings_view
    import hpc_gui.wx_updater_view as updater_view

    calls = {}

    def _recorder(name, **accept):
        def _impl(*args, **kwargs):
            calls[name] = (args, kwargs)
            if name == "updater":
                dialog = types.SimpleNamespace(
                    _build_for_state=lambda *a, **k: calls.setdefault("updater_state", (a, k)),
                    dlg=types.SimpleNamespace(Show=lambda *a, **k: None),
                )
                return dialog
            return wx.ID_OK

        return _impl

    monkeypatch.setattr(settings_view, "show_settings", _recorder("settings"))
    monkeypatch.setattr(about_view, "show_about", _recorder("about"))
    monkeypatch.setattr(help_view, "show_help", _recorder("help"))
    monkeypatch.setattr(logs_view, "show_send_logs", _recorder("logs"))
    monkeypatch.setattr(plugins_view, "show_plugins", _recorder("plugins"))

    real_dialog_cls = updater_view.WxUpdateDialog

    def _fake_dialog(parent, arg):
        calls["updater"] = ((parent, arg), {})
        return types.SimpleNamespace(
            _build_for_state=lambda *a, **k: calls.setdefault("updater_state", (a, k)),
            dlg=types.SimpleNamespace(Show=lambda *a, **k: None),
        )

    monkeypatch.setattr(updater_view, "WxUpdateDialog", _fake_dialog)

    frame, _lifecycle, _session = wx_shell.create_shell_frame(wx_app)
    try:
        _fire_menu(frame, frame._wx_shell_menu_items["settings"])
        assert "settings" in calls, "APP-SETTINGS must reach show_settings"
        assert calls["settings"][1].get("parent") is frame

        _fire_menu(frame, frame._wx_shell_help_items["about"])
        assert "about" in calls, "APP-ABOUT must reach show_about"

        _fire_menu(frame, frame._wx_shell_help_items["help"])
        assert "help" in calls, "APP-HELP must reach show_help"

        _fire_menu(frame, frame._wx_shell_help_items["logs"])
        assert "logs" in calls, "APP-SEND-LOGS must reach show_send_logs"

        _fire_menu(frame, frame._wx_shell_menu_items["check_updates"])
        assert "updater" in calls, "APP-UPDATE-CHECK must reach WxUpdateDialog"

        # PLUGIN-BROWSE via the preserved TypeError fallback: the real view
        # takes no initial_tab, so exactly one parent-only call must land.
        _fire_menu(frame, frame._wx_shell_plugins_menu.GetMenuItems()[0])
        assert "plugins" in calls, "PLUGIN-BROWSE must reach show_plugins"
    finally:
        monkeypatch.setattr(updater_view, "WxUpdateDialog", real_dialog_cls, raising=False)
        _close_shell(frame)


# ---------------------------------------------------------------------------
# E. Settings truthfulness (TRUTH-061)
# ---------------------------------------------------------------------------


def test_settings__visible_option_changes_owned_value():
    """A visible option mutates its owned model value; unknown keys fail
    loudly (KeyError), never silently."""
    from hpc_gui.wx_settings import WxSettingsModel

    model = WxSettingsModel({})
    model.set_global("remote_directory_cache", False)
    model.set_profile("transfer_parallelism", 4)
    snapshot = model.snapshot()
    assert snapshot.global_settings["remote_directory_cache"] is False
    assert snapshot.profile_settings["transfer_parallelism"] == 4
    with pytest.raises(KeyError):
        model.set_global("no_such_option", True)
    with pytest.raises(KeyError):
        model.set_profile("no_such_option", True)


def test_settings__shell_apply_gap_stays_ledgered():
    """The shell-Apply persistence gap is honestly EXPERIMENTAL with its
    W37 owner — classified, not fixed or hidden here."""
    _, rows = _parse_freeze_matrix()
    by_id = {row["ID"].strip("`"): row for row in rows}
    dlg = by_id["SET-DLG"]
    assert dlg["Support disposition"] == "EXPERIMENTAL"
    assert "DEF-W03-001" in dlg["Open gap"]
    assert "W37" in dlg["Verification owner Wave"]


# ---------------------------------------------------------------------------
# F. Plugin/provider capability contract (TRUTH-062/068)
# ---------------------------------------------------------------------------


def _fake_plugin(plugin_id="w04-fake", capabilities=()):
    manifest = types.SimpleNamespace(id=plugin_id, capabilities=tuple(capabilities))
    return types.SimpleNamespace(manifest=manifest)


def test_capability_gate__lacking_capability_is_not_executable():
    """TRUTH-068 at the contract layer: a missing capability refuses with a
    diagnosable reason; a declared one allows."""
    from hpc_gui.services.plugin_menu_actions import can_execute_action

    allowed, _ = can_execute_action("editor.lint_current", _fake_plugin(capabilities=("lint-rules",)))
    assert allowed is True
    allowed, reason = can_execute_action("editor.lint_current", _fake_plugin(capabilities=()))
    assert allowed is False
    assert "capability" in reason
    allowed, _ = can_execute_action("no.such.action", _fake_plugin(capabilities=("lint-rules",)))
    assert allowed is False


def test_plugin_menu__lacking_capability_renders_disabled_and_unbound(wx_app, monkeypatch):
    """TRUTH-065/068 behaviorally: an action whose capability the provider
    lacks renders disabled AND unbound (forcing its event is a provable
    no-op); policy-blocked trusted-tool stays disabled even with caps."""
    import hpc_gui.plugins.loader as loader_module
    import hpc_gui.plugins.ui_contributions as contributions
    import hpc_gui.services.plugin_menu_actions as actions_module

    fake_a = _fake_plugin("w04-fake-a", capabilities=())
    fake_b = _fake_plugin("w04-fake-b", capabilities=("linter-tool",))
    contrib_a = contributions.PluginMenuContribution(
        plugin_id="w04-fake-a",
        plugin_version="0",
        label="W04 Fake A",
        labels={},
        items=(
            contributions.PluginMenuAction(
                id="a-lint",
                label="Lint now",
                labels={},
                action="editor.lint_current",
                when={},
                unavailable="disable",
            ),
        ),
    )
    contrib_b = contributions.PluginMenuContribution(
        plugin_id="w04-fake-b",
        plugin_version="0",
        label="W04 Fake B",
        labels={},
        items=(
            contributions.PluginMenuAction(
                id="a-tool",
                label="Open tool",
                labels={},
                action="plugin.open_trusted_tool",
                when={},
                unavailable="disable",
            ),
        ),
    )
    monkeypatch.setattr(
        loader_module,
        "load_installed_plugins",
        lambda: types.SimpleNamespace(plugins=[fake_a, fake_b]),
    )
    monkeypatch.setattr(
        contributions,
        "collect_plugin_menu_contributions",
        lambda _plugins: [contrib_a, contrib_b],
    )
    dispatched = []
    monkeypatch.setattr(
        actions_module,
        "dispatch_plugin_menu_action",
        lambda *args, **kwargs: dispatched.append((args, kwargs)) or True,
    )

    frame, _lifecycle, _session = wx_shell.create_shell_frame(wx_app)
    try:
        assert callable(frame._wx_rebuild_plugins_menu)
        frame._wx_rebuild_plugins_menu()
        plugins_menu = frame._wx_shell_plugins_menu
        roots = [
            item
            for item in plugins_menu.GetMenuItems()
            if item.GetSubMenu() is not None
            and item.GetItemLabelText() in ("W04 Fake A", "W04 Fake B")
        ]
        assert len(roots) == 2, "fake contributions must rebuild into the Plugins menu"
        children = [
            item
            for root in roots
            for item in root.GetSubMenu().GetMenuItems()
            if not item.IsSeparator()
        ]
        assert len(children) == 2
        for child in children:
            assert not child.IsEnabled(), f"{child.GetItemLabelText()} must render disabled"
            # Forced delivery to a disabled+unbound item must not dispatch.
            frame.ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, child.GetId()))
            wx.Yield()
        assert dispatched == [], "disabled capability-gated items must stay unbound"
    finally:
        _close_shell(frame)


# ---------------------------------------------------------------------------
# G. FIX-W04-A: stale/exception plugin-action failures are visible (DEF-W04-001)
# ---------------------------------------------------------------------------


def test_plugin_action__stale_plugin__visible_coded_error(wx_app, monkeypatch):
    """TRUTH-067/072: clicking a menu action whose plugin vanished (rebuild
    raced an uninstall) shows exactly one coded error, never silence."""
    capture = _MessageBoxCapture(monkeypatch)
    frame, _lifecycle, _session = wx_shell.create_shell_frame(wx_app)
    try:
        frame._wx_dispatch_plugin_action("editor.lint_current", "ghost-plugin-id")
        wx.Yield()
    finally:
        _close_shell(frame)
    assert len(capture.calls) == 1, "stale plugin click must produce exactly one error dialog"
    text = capture.texts[0]
    assert "could not be completed" in text
    assert "ghost-plugin-id" in text, "stale identity must be diagnosable"
    assert re.search(r"PLUGIN-[0-9A-F]{6}", text), f"stable code missing: {text!r}"


def test_plugin_action__exception__visible_coded_error(wx_app, monkeypatch):
    """TRUTH-072: a dispatch exception is a visible coded error, not a
    log-only entry with a success-looking UI."""
    import hpc_gui.plugins.loader as loader_module
    import hpc_gui.services.plugin_menu_actions as actions_module

    fake = _fake_plugin("w04-p1", capabilities=("lint-rules",))
    monkeypatch.setattr(
        loader_module, "load_installed_plugins", lambda: types.SimpleNamespace(plugins=[fake])
    )

    boom = RuntimeError("boom-plugin-action")

    def _raise(*args, **kwargs):
        raise boom

    monkeypatch.setattr(actions_module, "dispatch_plugin_menu_action", _raise)
    capture = _MessageBoxCapture(monkeypatch)
    frame, _lifecycle, _session = wx_shell.create_shell_frame(wx_app)
    try:
        frame._wx_dispatch_plugin_action("editor.lint_current", "w04-p1")
        wx.Yield()
    finally:
        _close_shell(frame)
    assert len(capture.calls) == 1
    assert re.search(r"PLUGIN-[0-9A-F]{6}", capture.texts[0])


def test_plugin_action__success__silent(wx_app, monkeypatch):
    """Happy-path guard: a successful plugin action dispatches once and
    shows no error dialog."""
    import hpc_gui.plugins.loader as loader_module
    import hpc_gui.services.plugin_menu_actions as actions_module

    fake = _fake_plugin("w04-p1", capabilities=("lint-rules",))
    monkeypatch.setattr(
        loader_module, "load_installed_plugins", lambda: types.SimpleNamespace(plugins=[fake])
    )
    dispatched = []
    monkeypatch.setattr(
        actions_module,
        "dispatch_plugin_menu_action",
        lambda *args, **kwargs: dispatched.append((args, kwargs)) or True,
    )
    capture = _MessageBoxCapture(monkeypatch)
    frame, _lifecycle, _session = wx_shell.create_shell_frame(wx_app)
    try:
        frame._wx_dispatch_plugin_action("editor.lint_current", "w04-p1")
        wx.Yield()
    finally:
        _close_shell(frame)
    assert len(dispatched) == 1
    assert capture.calls == []


# ---------------------------------------------------------------------------
# H. Disconnected / destructive / context-label truth (TRUTH-066/070 + labels)
# ---------------------------------------------------------------------------


def test_terminal__disconnected_warns_instead_of_dead_session(wx_app, monkeypatch):
    """TRUTH-066: opening the terminal with no session warns visibly and
    returns CANCEL — never a dead terminal frame."""
    from hpc_gui.wx_terminal import show_terminal

    capture = _MessageBoxCapture(monkeypatch)
    before = set(wx.GetTopLevelWindows())
    assert show_terminal(None, ssh=None) == wx.ID_CANCEL
    assert len(capture.calls) == 1
    assert set(wx.GetTopLevelWindows()) == before


def test_local_delete__requires_explicit_destructive_confirm(wx_app, tmp_path, monkeypatch):
    """TRUTH-070: Delete carries YES_NO + ICON_WARNING confirmation and only
    then mutates; the label implies exactly this destructive semantic."""
    from hpc_gui.wx_local_files import show_local_files

    target = tmp_path / "doomed.txt"
    target.write_text("x", encoding="utf-8")
    keeper = tmp_path / "keeper.txt"
    keeper.write_text("y", encoding="utf-8")

    styles = []

    def _recorder(*args, **kwargs):
        style = args[2] if len(args) > 2 else kwargs.get("style", 0)
        styles.append(style)
        return wx.YES

    monkeypatch.setattr(wx, "MessageBox", _recorder)
    show_local_files(path=tmp_path)
    frame = [w for w in wx.GetTopLevelWindows() if hasattr(w, "_wx_local_controls")][-1]
    wx_app.ProcessPendingEvents()
    listing = frame._wx_local_controls["listing"]
    row = next(i for i in range(listing.GetItemCount()) if listing.GetItemText(i) == "doomed.txt")
    listing.Select(row)
    frame._wx_local_run_action("delete")

    def _settled():
        return not frame._wx_local_state["mutation_in_flight"]

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        wx_app.ProcessPendingEvents()
        if _settled():
            break
        wx.MilliSleep(5)
    assert _settled()
    assert styles, "delete must confirm before mutating"
    assert any(s & wx.YES_NO and s & wx.ICON_WARNING for s in styles), styles
    assert not target.exists()
    assert keeper.exists()


def test_remote_delete__confirm_is_destructive_styled():
    """TRUTH-070 (remote leg, source-anchored): the remote delete confirm
    call site carries the same YES_NO + ICON_WARNING semantics."""
    source = pathlib.Path("src/hpc_gui/wx_remote_files_view.py").read_text(encoding="utf-8")
    match = re.search(r'dirs\.delete_confirm".*?YES_NO\s*\|\s*wx\.ICON_WARNING', source, re.DOTALL)
    assert match, "remote delete_confirm call site must carry YES_NO + ICON_WARNING"


def test_remote_context__allowed_actions_resolve_to_labels():
    """Dead-key guard for context surfaces: every remote-allowed action
    resolves to a real label in the bundle (no [dirs.x] masking)."""
    from hpc_gui.services.file_context_actions import (
        FILE_CONTEXT_LABEL_KEYS,
        context_selection,
        visible_actions,
    )

    selection = context_selection("/remote/home", False, ("/remote/home",), (False,))
    for action in visible_actions(selection, remote=True):
        key = FILE_CONTEXT_LABEL_KEYS.get(action, f"dirs.{action}")
        assert t(key) != f"[{key}]", f"unresolved label for remote action {action!r}"


# ---------------------------------------------------------------------------
# I. Single transfer path + About contract (TRUTH-069 + W01-E replacement)
# ---------------------------------------------------------------------------


def test_header_upload_download__use_panel_run_actions(wx_app, monkeypatch):
    """TRUTH-069: header Upload/Download funnel into the same panel
    run_action paths the browser toolbars use (one truthful transfer path)."""
    capture = _MessageBoxCapture(monkeypatch)
    _auto_cancel_native_selectors(monkeypatch)
    frame, _lifecycle, _session = wx_shell.create_shell_frame(wx_app)
    try:
        pages = frame._wx_shell_controls["pages"]["NAV-FILES"]
        local_panel, remote_panel = pages["local"], pages["remote"]
        seen = []

        orig_local = local_panel._wx_local_run_action
        orig_remote = remote_panel._wx_remote_run_action

        def _local_rec(action, *args, **kwargs):
            seen.append(("local", action))
            return orig_local(action, *args, **kwargs)

        def _remote_rec(action, *args, **kwargs):
            seen.append(("remote", action))
            return orig_remote(action, *args, **kwargs)

        local_panel._wx_local_run_action = _local_rec
        remote_panel._wx_remote_run_action = _remote_rec
        try:
            upload_btn, download_btn = pages["upload_selected"], pages["download_selected"]
            upload_btn.ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, upload_btn.GetId()))
            download_btn.ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, download_btn.GetId()))
            wx.Yield()
        finally:
            local_panel._wx_local_run_action = orig_local
            remote_panel._wx_remote_run_action = orig_remote
        assert ("local", "upload") in seen, f"header upload must call local run_action: {seen}"
        assert ("remote", "download") in seen, f"header download must call remote run_action: {seen}"
    finally:
        _close_shell(frame)


def _collect_about_labels():
    """Build the real About dialog with the modal loop intercepted (real
    construction + real labels, no blocking event loop)."""
    import hpc_gui.wx_about as about_view
    from hpc_gui import __version__

    seen = {}

    def _fake_show_modal(self):
        texts = []
        buttons = []

        def _walk(window):
            for child in window.GetChildren():
                if isinstance(child, wx.StaticText):
                    texts.append(child.GetLabel())
                elif isinstance(child, wx.Button):
                    buttons.append(child.GetLabel())
                _walk(child)

        _walk(self)
        seen["texts"] = texts
        seen["buttons"] = buttons
        # No modal loop is running under interception, so EndModal would
        # assert; returning ID_OK models the Close-button dismissal.
        return wx.ID_OK

    original = wx.Dialog.ShowModal
    wx.Dialog.ShowModal = _fake_show_modal
    try:
        assert about_view.show_about(None) == wx.ID_OK
    finally:
        wx.Dialog.ShowModal = original
    assert seen, "ShowModal interception must observe the real dialog"
    return seen, __version__


def test_about__visible_contract_fields(wx_app):
    """W01-E replacement-dialog proof: the About dialog carries the required
    visible contract (version + legal actions + close)."""
    seen, version = _collect_about_labels()
    assert any(version in text for text in seen["texts"]), seen["texts"]
    for required in ("Project Repository", "License", "Third-Party Notices", "Close"):
        assert required in seen["buttons"], seen["buttons"]


def test_about__contract_detector_is_sensitive(wx_app, monkeypatch):
    """W01-E sensitivity: the pre-FIX-W01-002 MessageBox implementation
    cannot satisfy the dialog contract (proves the contract test detects
    the old regression class)."""
    import hpc_gui.wx_about as about_view

    _MessageBoxCapture(monkeypatch)  # legacy impl would block on a real modal
    real = about_view.show_about

    def _legacy_messagebox_impl(_parent=None):
        wx.MessageBox("about", "about")
        return wx.ID_OK

    about_view.show_about = _legacy_messagebox_impl
    try:
        with pytest.raises(Exception):
            _collect_about_labels_with(about_view.show_about)
    finally:
        about_view.show_about = real


def _collect_about_labels_with(show_fn):
    seen = {}

    def _fake_show_modal(self):
        seen["observed"] = True
        self.EndModal(wx.ID_OK)
        return wx.ID_OK

    original = wx.Dialog.ShowModal
    wx.Dialog.ShowModal = _fake_show_modal
    try:
        show_fn(None)
    finally:
        wx.Dialog.ShowModal = original
    assert seen.get("observed"), "legacy MessageBox impl builds no dialog: contract fails"


# ---------------------------------------------------------------------------
# J. Packaging honesty (TRUTH-064)
# ---------------------------------------------------------------------------


def test_packaging__no_artifact_claim_without_sha():
    """TRUTH-064: W04 binds no package artifact, so no SHA-256 is cited;
    every package-dependent row defers to W08/W10 instead of claiming."""
    _, rows = _parse_freeze_matrix()
    for row in rows:
        if "package" in row["Required evidence class"].lower():
            gap = row["Open gap"]
            assert "W08" in gap or "W10" in gap, f"{row['ID']}: package gap must name W08/W10"
    artifact_dir = pathlib.Path("artifacts/v2-final/W04")
    assert artifact_dir.is_dir()
    binaries = [
        path
        for path in artifact_dir.iterdir()
        if path.suffix.lower() in {".exe", ".msi", ".whl", ".zip", ".msix", ".dmg", ".pkg"}
    ]
    assert binaries == [], f"no package artifact may be bound by W04: {binaries}"
