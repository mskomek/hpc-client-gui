"""GUI-FILE-003 final stress and invariant campaign.

Every stress group drives real wx events through the production view handlers
and records the measured invariants in ``METRICS``.  The last test in the file
prints the whole scoreboard and asserts the mandatory zeros, so a regression
shows up as a measured number rather than as a missing assertion.
"""

from __future__ import annotations

pytest_plugins = ('support.test_wx_file003_final_stress_shared',)
from support.test_wx_file003_final_stress_shared import (
    ConcurrencyProbe,
    LocalBrowserModel,
    METRICS,
    MockRemoteFilesBackend,
    Path,
    RemoteEntry,
    SENTINELS,
    _context_event,
    _fire_menu_item,
    _key,
    _local_frame,
    _pump,
    _record,
    _remote_frame,
    _row_position,
    _rows,
    _select_only,
    _settle,
    pytest,
    wx,
)

pytestmark = [pytest.mark.wx]

@pytest.mark.gui
@pytest.mark.semantic
@pytest.mark.regression
def test_stress_a_right_click_retarget(wx_app, monkeypatch):
    import hpc_gui.wx_remote_files_view as view

    assert wx.App.Get() is wx_app
    backend = MockRemoteFilesBackend()
    backend.entries.update({"/work/dir-a": True, "/work/c.txt": False, "/work/d.txt": False})
    frame = _remote_frame(wx_app, backend)
    listing = frame._wx_remote_controls["listing"]
    _pump(wx_app, lambda: listing.GetItemCount() >= 5)

    observed = []
    original_visible_actions = view.visible_actions

    def recording_visible_actions(selection, *args, **kwargs):
        observed.append(selection)
        return original_visible_actions(selection, *args, **kwargs)

    monkeypatch.setattr(view, "visible_actions", recording_visible_actions)
    listing.PopupMenu = lambda menu: None

    entries_of = lambda: [entry.path for entry in frame._wx_remote_tabs[0]["entries"]]  # noqa: E731
    executed = 0
    for index in range(200):
        paths = entries_of()
        mode = index % 5
        before = len(observed)
        if mode == 0:  # right-click a row that is not selected
            row = index % len(paths)
            other = (row + 1) % len(paths)
            _select_only(listing, other)
            listing.ProcessEvent(_context_event(listing, _row_position(listing, row)))
            expected = (paths[row],)
        elif mode == 1:  # right-click a row that is already the only selection
            row = index % len(paths)
            _select_only(listing, row)
            listing.ProcessEvent(_context_event(listing, _row_position(listing, row)))
            expected = (paths[row],)
        elif mode == 2:  # right-click inside a multiselection
            first = index % len(paths)
            second = (first + 1) % len(paths)
            _select_only(listing, first, second)
            listing.ProcessEvent(_context_event(listing, _row_position(listing, first)))
            expected = tuple(sorted((paths[first], paths[second])))
        elif mode == 3:  # background, below the last row
            _select_only(listing, 0)
            position = listing.ClientToScreen(wx.Point(5, listing.GetSize().height - 4))
            listing.ProcessEvent(_context_event(listing, position))
            expected = ()
        else:  # keyboard context menu key
            row = index % len(paths)
            _select_only(listing, row)
            listing.ProcessEvent(_context_event(listing, wx.DefaultPosition))
            expected = (paths[row],)
        executed += 1
        if len(observed) != before + 1:
            METRICS["wrong_targets"] += 1
            continue
        selection = observed[-1]
        actual = tuple(sorted(selection.effective_paths))
        if mode == 3:
            if actual or not selection.background:
                METRICS["wrong_targets"] += 1
            continue
        if actual != tuple(sorted(expected)):
            METRICS["wrong_targets"] += 1
            continue
        if mode == 2 and sum(listing.IsSelected(i) for i in range(listing.GetItemCount())) != 2:
            METRICS["wrong_targets"] += 1
        if mode == 0 and not listing.IsSelected(paths.index(expected[0])):
            METRICS["wrong_targets"] += 1

    _record("right-click retarget", executed, 200)
    assert METRICS["wrong_targets"] == 0

@pytest.mark.gui
@pytest.mark.semantic
@pytest.mark.regression
@pytest.mark.concurrency
@pytest.mark.slow
def test_stress_b_local_mutations(wx_app, tmp_path: Path, monkeypatch):
    other = tmp_path / "other"
    other.mkdir()
    probe = ConcurrencyProbe()
    for name in ("rename_at", "delete_at", "new_folder", "paste_into"):
        monkeypatch.setattr(LocalBrowserModel, name, probe.wrap(getattr(LocalBrowserModel, name)))

    frame = _local_frame(wx_app, tmp_path)
    notebook = frame._wx_local_notebook
    listing = frame._wx_local_controls["listing"]
    _pump(wx_app, lambda: "other" in _rows(listing))
    _select_only(listing, _rows(listing).index("other"))
    frame._wx_local_run_action("new_tab")
    _pump(wx_app, lambda: notebook.GetPageCount() == 2)

    typed = {"name": ""}

    class Dialog:
        def ShowModal(self):
            return wx.ID_OK

        def GetValue(self):
            return typed["name"]

        def Destroy(self):
            return None

    monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: Dialog())
    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: wx.YES)

    def active():
        return frame._wx_local_controls["listing"]

    def select_tab(index):
        notebook.SetSelection(index)
        _settle(wx_app)

    def wait_idle():
        _pump(wx_app, lambda: not frame._wx_local_state["mutation_in_flight"], timeout=5)
        _settle(wx_app)

    executed = 0
    for index in range(100):
        home = index % 2
        select_tab(home)
        home_dir = tmp_path if home == 0 else other
        away_dir = other if home == 0 else tmp_path
        seed = home_dir / f"s{index}.txt"
        seed.write_text("payload", encoding="utf-8")
        frame._wx_local_run_action("refresh")
        _pump(wx_app, lambda: seed.name in _rows(active()))
        listing = active()
        _select_only(listing, _rows(listing).index(seed.name))
        mode = index % 5
        if mode == 0:  # F2 rename
            typed["name"] = f"r{index}.txt"
            _key(listing, wx.WXK_F2)
            wait_idle()
            expected = home_dir / f"r{index}.txt"
            if not expected.exists() or seed.exists():
                METRICS["wrong_targets"] += 1
            expected.unlink(missing_ok=True)
        elif mode == 1:  # Delete key
            _key(listing, wx.WXK_DELETE)
            wait_idle()
            if seed.exists():
                METRICS["wrong_targets"] += 1
        elif mode == 2:  # background context menu New Folder
            typed["name"] = f"folder-{index}"
            background = listing.ClientToScreen(wx.Point(5, listing.GetSize().height - 4))
            assert _fire_menu_item(
                listing,
                "New Folder",
                lambda: listing.ProcessEvent(_context_event(listing, background)),
            )
            wait_idle()
            created = home_dir / f"folder-{index}"
            if not created.is_dir() or (away_dir / created.name).exists():
                METRICS["wrong_targets"] += 1
            created.rmdir()
            seed.unlink(missing_ok=True)
        elif mode == 3:  # Ctrl+C here, Ctrl+V in the other tab
            _key(listing, ord("C"), ctrl=True)
            select_tab(1 - home)
            _key(active(), ord("V"), ctrl=True)
            wait_idle()
            if not (away_dir / seed.name).exists() or not seed.exists():
                METRICS["wrong_targets"] += 1
            (away_dir / seed.name).unlink(missing_ok=True)
            seed.unlink(missing_ok=True)
        else:  # Ctrl+X here, Ctrl+V in the other tab
            _key(listing, ord("X"), ctrl=True)
            select_tab(1 - home)
            _key(active(), ord("V"), ctrl=True)
            wait_idle()
            if not (away_dir / seed.name).exists() or seed.exists():
                METRICS["wrong_targets"] += 1
            (away_dir / seed.name).unlink(missing_ok=True)
        executed += 1

        if index % 10 == 0:
            # Switch tabs while a mutation is still in flight: the mutation must
            # land in its origin directory and must not paint the other tab.
            select_tab(home)
            inflight = home_dir / f"inflight-{index}.txt"
            inflight.write_text("x", encoding="utf-8")
            frame._wx_local_run_action("refresh")
            _pump(wx_app, lambda: inflight.name in _rows(active()))
            listing = active()
            _select_only(listing, _rows(listing).index(inflight.name))
            typed["name"] = f"moved-{index}.txt"
            _key(listing, wx.WXK_F2)
            select_tab(1 - home)
            wait_idle()
            renamed = home_dir / f"moved-{index}.txt"
            if not renamed.exists():
                METRICS["wrong_targets"] += 1
            if renamed.name in _rows(active()):
                METRICS["stale_ui_overwrites"] += 1
            renamed.unlink(missing_ok=True)

    METRICS["peak_local_mutation_concurrency"] = max(
        METRICS["peak_local_mutation_concurrency"], probe.peak
    )
    _record("local mutations", executed, 100)
    assert METRICS["wrong_targets"] == 0
    assert METRICS["stale_ui_overwrites"] == 0
    assert probe.peak <= 1, probe.peak

@pytest.mark.gui
@pytest.mark.semantic
@pytest.mark.regression
@pytest.mark.concurrency
@pytest.mark.slow
def test_stress_c_remote_mutations(wx_app, monkeypatch):
    backend = MockRemoteFilesBackend()
    backend.entries["/scratch"] = True
    probe = ConcurrencyProbe()
    backend.operation = probe.wrap(backend.operation)

    frame = _remote_frame(wx_app, backend)
    notebook = frame._wx_remote_notebook
    frame._wx_remote_run_action("new_tab", ("/scratch",), "/scratch")
    _pump(wx_app, lambda: notebook.GetPageCount() == 2)

    typed = {"name": ""}

    class Dialog:
        def ShowModal(self):
            return wx.ID_OK

        def GetValue(self):
            return typed["name"]

        def Destroy(self):
            return None

    monkeypatch.setattr(wx, "TextEntryDialog", lambda *a, **k: Dialog())
    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: wx.YES)

    def active():
        return frame._wx_remote_controls["listing"]

    def select_tab(index):
        notebook.SetSelection(index)
        _settle(wx_app)

    def wait_idle():
        _pump(wx_app, lambda: not frame._wx_remote_state["busy"], timeout=5)
        _settle(wx_app)

    executed = 0
    mutating_calls = 0
    lost_modes = []
    wrong_modes = []
    for index in range(100):
        home = index % 2
        select_tab(home)
        home_dir = "/work" if home == 0 else "/scratch"
        away_dir = "/scratch" if home == 0 else "/work"
        source = f"{home_dir}/item-{index}.txt"
        base = f"item-{index}.txt"
        backend.entries[source] = False
        frame._wx_remote_run_action("refresh", ())
        _pump(wx_app, lambda: base in _rows(active()))
        listing = active()
        _select_only(listing, _rows(listing).index(base))
        before_calls = len(backend.calls)
        mode = index % 5
        if mode == 0:  # F2 rename
            typed["name"] = f"renamed-{index}.txt"
            renamed = f"{home_dir}/renamed-{index}.txt"
            _key(listing, wx.WXK_F2)
            wait_idle()
            if renamed not in backend.entries or source in backend.entries:
                METRICS["wrong_targets"] += 1
                wrong_modes.append(mode)
            backend.entries.pop(renamed, None)
            mutating_calls += 1
        elif mode == 1:  # Delete key
            _key(listing, wx.WXK_DELETE)
            wait_idle()
            if source in backend.entries:
                METRICS["wrong_targets"] += 1
                wrong_modes.append(mode)
            mutating_calls += 1
        elif mode == 2:  # Ctrl+C here, Ctrl+V in the other tab
            _key(listing, ord("C"), ctrl=True)
            select_tab(1 - home)
            _key(active(), ord("V"), ctrl=True)
            wait_idle()
            copied = f"{away_dir}/item-{index}.txt"
            if copied not in backend.entries or source not in backend.entries:
                METRICS["wrong_targets"] += 1
                wrong_modes.append(mode)
            backend.entries.pop(copied, None)
            backend.entries.pop(source, None)
            mutating_calls += 1
        elif mode == 3:  # Ctrl+X, paste in the other tab, then Ctrl+Z undo
            _key(listing, ord("X"), ctrl=True)
            select_tab(1 - home)
            _key(active(), ord("V"), ctrl=True)
            wait_idle()
            moved = f"{away_dir}/item-{index}.txt"
            if moved not in backend.entries or source in backend.entries:
                METRICS["wrong_targets"] += 1
                wrong_modes.append(mode)
            _key(active(), ord("Z"), ctrl=True)
            wait_idle()
            if source not in backend.entries or moved in backend.entries:
                METRICS["wrong_targets"] += 1
                wrong_modes.append(mode)
            backend.entries.pop(source, None)
            mutating_calls += 2
        else:  # background New Folder, then Copy Path on the row
            typed["name"] = f"folder-{index}"
            created = f"{home_dir}/folder-{index}"
            background = listing.ClientToScreen(wx.Point(5, listing.GetSize().height - 4))
            assert _fire_menu_item(
                listing,
                "New Folder",
                lambda: listing.ProcessEvent(_context_event(listing, background)),
            )
            wait_idle()
            if created not in backend.entries or f"{away_dir}/folder-{index}" in backend.entries:
                METRICS["wrong_targets"] += 1
                wrong_modes.append(("new_folder", created, sorted(backend.entries)[:8]))
            mutating_calls += 1
            listing = active()
            _select_only(listing, _rows(listing).index(base))
            calls_before_copy_path = len(backend.calls)
            assert _fire_menu_item(
                listing,
                "Copy path with file name",
                lambda: listing.ProcessEvent(
                    _context_event(listing, _row_position(listing, _rows(listing).index(base)))
                ),
            )
            wait_idle()
            if len(backend.calls) != calls_before_copy_path:
                METRICS["wrong_targets"] += 1
                wrong_modes.append(("copy_path", backend.calls[calls_before_copy_path:]))
            backend.entries.pop(created, None)
            backend.entries.pop(source, None)
        executed += 1
        if len(backend.calls) <= before_calls and mode != 4:
            METRICS["lost_remote_mutations"] += 1
            lost_modes.append(mode)

    move_calls = [call for call in backend.calls if call[0] == "move"]
    assert len(move_calls) == len(set(move_calls)), "duplicate remote move operations"
    METRICS["peak_remote_mutation_concurrency"] = max(
        METRICS["peak_remote_mutation_concurrency"], probe.peak
    )
    _record("remote mutations", executed, 100)
    assert METRICS["lost_remote_mutations"] == 0, sorted(set(lost_modes))
    assert METRICS["wrong_targets"] == 0, wrong_modes[:3]
    assert probe.peak <= 1, probe.peak
    assert mutating_calls >= 100

@pytest.mark.gui
@pytest.mark.semantic
@pytest.mark.regression
@pytest.mark.concurrency
@pytest.mark.slow
def test_stress_d_target_switches(wx_app):
    listed = {"count": 0}

    def loader(path):
        listed["count"] += 1
        sentinel = SENTINELS.get(path)
        if sentinel is None:
            return tuple(RemoteEntry(target, is_dir=True) for target in SENTINELS)
        return (RemoteEntry(path.rstrip("/") + "/" + sentinel, is_dir=False),)

    backend = MockRemoteFilesBackend()
    frame = _remote_frame(wx_app, backend, loader=loader)
    notebook = frame._wx_remote_notebook
    for position, path in enumerate(("/scratch", "/home/test", "/project"), start=2):
        frame._wx_remote_run_action("new_tab", (path,), path)
        _pump(wx_app, lambda: notebook.GetPageCount() == position)
    _settle(wx_app)

    tabs = frame._wx_remote_tabs
    foreign = {path: {name for other, name in SENTINELS.items() if other != path} for path in SENTINELS}

    executed = 0
    for index in range(200):
        # Put a real listing in flight before switching away from it.
        _key(frame._wx_remote_controls["listing"], wx.WXK_F5)
        notebook.SetSelection(index % 4)
        _settle(wx_app)
        _pump(
            wx_app,
            lambda: not frame._wx_remote_state["busy"] and not frame._wx_remote_state["listing_busy"],
        )
        executed += 1
        for tab in tabs:
            visible = set(_rows(tab["listing"]))
            if visible - {SENTINELS[tab["path"]]}:
                METRICS["stale_ui_overwrites"] += 1
            if visible & foreign[tab["path"]]:
                METRICS["wrong_targets"] += 1

    _record("target switches", executed, 200)
    assert listed["count"] > 200
    assert METRICS["stale_ui_overwrites"] == 0
    assert METRICS["wrong_targets"] == 0
