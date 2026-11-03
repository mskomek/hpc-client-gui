from __future__ import annotations

import time

import pytest

from hpc_gui.wx_logs import LogDisplayEntry, group_repeated_ssh_commands


def _record(second: int, message: str, *, level: str = "INFO") -> str:
    return f"2026-10-21 12:00:{second:02d} | {level} | hpc_gui.ssh.client | {message}\n"


def _query(second: int, command: str, *, output: str = "") -> str:
    result = _record(second, f"SSH$ {command}")
    if output:
        result += _record(second, output)
    return result + _record(second, "[exit=0 duration=0.21s]")


def _groups(text: str) -> list[LogDisplayEntry]:
    return [entry for entry in group_repeated_ssh_commands(text) if entry.is_group]


def test_groups_adjacent_squeue_queries_and_preserves_every_raw_line():
    text = (
        _query(1, 'squeue -h -u alice -o "%A"', output="1001\n1002")
        + _query(2, 'squeue -h -u alice -o "%i|%T"', output="1003")
    )

    entries = group_repeated_ssh_commands(text)

    assert len(entries) == 1
    assert entries[0].is_group
    assert entries[0].command_family == "squeue"
    assert entries[0].command_count == 2
    assert entries[0].first_timestamp == "2026-10-21 12:00:01"
    assert entries[0].last_timestamp == "2026-10-21 12:00:02"
    assert "1001\n1002" in "".join(entries[0].raw_lines)
    assert "1003" in "".join(entries[0].raw_lines)
    assert "squeue -h -u alice -o \"%i|%T\"" in "".join(entries[0].raw_lines)
    assert "".join(line for entry in entries for line in entry.raw_lines) == text


def test_groups_sacct_and_tail_commands_even_when_tail_paths_differ():
    sacct = _query(1, "sacct -n -P -j 1001 -o JobID,State") + _query(
        2, "sacct -n -P -j 1002 -o JobID,State"
    )
    tail = _query(3, "tail -n 200 -- /scratch/run one/slurm.out") + _query(
        4, "tail -n 200 -- /scratch/run two/slurm.out"
    )

    entries = group_repeated_ssh_commands(sacct + tail)

    assert [(entry.command_family, entry.command_count) for entry in entries] == [
        ("sacct", 2),
        ("tail", 2),
    ]
    assert "/scratch/run one/slurm.out" in "".join(entries[1].raw_lines)
    assert "/scratch/run two/slurm.out" in "".join(entries[1].raw_lines)


def test_different_commands_and_intervening_lines_end_groups():
    text = (
        _query(1, "squeue -h")
        + _query(2, "squeue -h")
        + _query(3, "sacct -n -P")
        + _query(4, "sacct -n -P")
        + _record(5, "SSH: reconnecting...")
        + _query(6, "squeue -h")
        + _query(7, "squeue -h")
    )

    entries = group_repeated_ssh_commands(text)

    assert [(entry.command_family, entry.command_count) for entry in _groups(text)] == [
        ("squeue", 2),
        ("sacct", 2),
        ("squeue", 2),
    ]
    rendered = "".join(line for entry in entries for line in entry.raw_lines)
    assert "SSH: reconnecting" in rendered
    assert rendered == text


def test_failure_timeout_stderr_and_errors_are_never_hidden_in_groups():
    samples = (
        _query(1, "squeue -h")
        + _record(2, "SSH$ squeue -h")
        + _record(2, "[exit=2 duration=0.21s]")
        + _record(3, "SSH$ sacct -n -P")
        + _record(3, "[timeout after 1.0s exit=124]")
        + _record(4, "SSH$ tail -n 20 -- out.log")
        + _record(4, "STDERR:\npermission denied")
        + _record(4, "[exit=0 duration=0.21s]")
        + _record(5, "SSH channel open failed", level="ERROR")
        + _record(6, "Traceback (most recent call last):", level="ERROR")
        + _query(7, "squeue -h")
    )

    entries = group_repeated_ssh_commands(samples)

    assert _groups(samples) == []
    rendered = "".join(line for entry in entries for line in entry.raw_lines)
    assert rendered == samples
    for marker in ("exit=2", "timeout after", "STDERR:", "permission denied", "channel open failed", "Traceback"):
        assert marker in rendered


def test_ambiguous_interleaving_and_unsupported_commands_remain_raw():
    text = (
        _record(1, "SSH$ squeue -h")
        + _record(1, "SSH$ sacct -n -P")
        + _record(1, "[exit=0 duration=0.21s]")
        + _record(1, "[exit=0 duration=0.21s]")
        + _query(2, "sbatch job.slurm")
        + _query(3, "scancel 1001")
        + _query(4, "bash -lc 'squeue -h'")
    )

    entries = group_repeated_ssh_commands(text)

    assert _groups(text) == []
    assert "".join(line for entry in entries for line in entry.raw_lines) == text


def test_single_successful_query_is_not_a_group():
    text = _query(1, "squeue -h")

    entries = group_repeated_ssh_commands(text)

    assert not any(entry.is_group for entry in entries)
    assert "".join(line for entry in entries for line in entry.raw_lines) == text


def test_unprefixed_warning_or_connection_error_interrupts_a_run():
    text = (
        _query(1, "squeue -h")
        + "WARNING: scheduler response is incomplete\n"
        + _query(2, "squeue -h")
        + "SSH authentication timeout\n"
        + _query(3, "squeue -h")
    )

    entries = group_repeated_ssh_commands(text)

    assert _groups(text) == []
    assert "".join(line for entry in entries for line in entry.raw_lines) == text


def test_shell_pipelines_are_not_treated_as_direct_automatic_queries():
    text = _query(1, "squeue -h | head -n 10") + _query(2, "squeue -h | head -n 10")

    assert _groups(text) == []


@pytest.fixture
def wx_app():
    import wx

    app = wx.App.Get() or wx.App(False)
    existing_windows = set(wx.GetTopLevelWindows())
    yield app
    for window in set(wx.GetTopLevelWindows()) - existing_windows:
        try:
            window.Destroy()
        except Exception:
            pass
    try:
        app.ProcessPendingEvents()
        wx.SafeYield()
    except Exception:
        pass


def _pump_until(predicate, timeout_s: float = 5.0) -> bool:
    import wx

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        wx.Yield()
        if predicate():
            return True
        time.sleep(0.02)
    return bool(predicate())


def _checkbox_event(wx, checkbox) -> None:
    checkbox.SetValue(not checkbox.GetValue())
    event = wx.CommandEvent(wx.EVT_CHECKBOX.evtType[0], checkbox.GetId())
    checkbox.GetEventHandler().ProcessEvent(event)


@pytest.fixture
def english_i18n():
    from hpc_gui.core.i18n import current_language, load_language

    previous_language = current_language()
    load_language("en")
    yield
    load_language(previous_language)


@pytest.mark.gui
@pytest.mark.wx
def test_wx_tree_group_click_refresh_copy_and_normal_view(tmp_path, wx_app, english_i18n, monkeypatch):
    import wx

    from hpc_gui.core import i18n
    from hpc_gui.wx_logs import WxLogsModel
    from hpc_gui.wx_logs_view import build_logs_panel

    monkeypatch.setattr(i18n, "app_data_dir", lambda: tmp_path)
    log_file = tmp_path / "app.log"
    original = _query(1, "squeue -h -u alice") + _query(2, "squeue -h -u alice")
    log_file.write_text(original, encoding="utf-8")
    parent = wx.Frame(None, title="logs-groups-test", size=(900, 600))
    parent.Show()
    host = build_logs_panel(parent, model=WxLogsModel(log_file))
    host.Show()
    parent.Layout()
    controls = host._wx_logs_controls
    tree = controls["grouped"]

    assert _pump_until(lambda: controls["text"].GetValue() == original)
    _checkbox_event(wx, controls["collapse_repeats"])
    assert tree.IsShown()
    tree_root = tree.GetRootItem()
    item, cookie = tree.GetFirstChild(tree_root)
    assert item.IsOk()
    assert "squeue" in tree.GetItemText(item)
    assert "2" in tree.GetItemText(item)
    assert "2 runs" in tree.GetItemText(item)
    assert tree.GetChildrenCount(item, False) == 4

    i18n.set_language("tr")
    assert "2 çalıştırma" in tree.GetItemText(tree.GetFirstChild(tree.GetRootItem())[0])
    i18n.set_language("en")
    tree_root = tree.GetRootItem()
    item, cookie = tree.GetFirstChild(tree_root)
    tree.Update()
    wx.Yield()

    bounds = tree.GetBoundingRect(item, True)
    rect = bounds[0] if isinstance(bounds, tuple) else bounds
    click = wx.MouseEvent(wx.wxEVT_LEFT_DOWN)
    click.SetId(tree.GetId())
    click.SetEventObject(tree)
    click.SetPosition(wx.Point(rect.x + max(2, rect.width // 2), rect.y + rect.height // 2))
    tree.GetEventHandler().ProcessEvent(click)
    wx.Yield()
    assert tree.IsExpanded(item)

    child, child_cookie = tree.GetFirstChild(item)
    visible_lines = []
    while child.IsOk():
        visible_lines.append(tree.GetItemText(child))
        child, child_cookie = tree.GetNextChild(item, child_cookie)
    assert sum("SSH$ squeue" in line for line in visible_lines) == 2
    assert sum("exit=0 duration" in line for line in visible_lines) == 2

    with open(log_file, "a", encoding="utf-8") as stream:
        stream.write(_query(3, "squeue -h -u alice") + _query(4, "squeue -h -u alice"))
    host._wx_logs_refresh()
    expected = original + _query(3, "squeue -h -u alice") + _query(4, "squeue -h -u alice")
    assert _pump_until(lambda: host._wx_logs_model.text == expected)
    refreshed_root = tree.GetRootItem()
    refreshed_item, refreshed_cookie = tree.GetFirstChild(refreshed_root)
    assert tree.IsExpanded(refreshed_item)
    assert tree.GetChildrenCount(refreshed_item, False) == 8

    copy_event = wx.CommandEvent(wx.EVT_BUTTON.evtType[0], controls["copy"].GetId())
    controls["copy"].GetEventHandler().ProcessEvent(copy_event)
    copied = wx.TextDataObject()
    assert wx.TheClipboard.Open()
    try:
        assert wx.TheClipboard.GetData(copied)
        assert copied.GetText() == host._wx_logs_model.text
    finally:
        wx.TheClipboard.Close()

    _checkbox_event(wx, controls["collapse_repeats"])
    assert controls["text"].IsShown()
    assert controls["text"].GetValue() == host._wx_logs_model.text
    assert not tree.IsShown()
    parent.Destroy()


@pytest.mark.gui
@pytest.mark.wx
def test_wx_large_log_group_view_keeps_all_5000_lines(tmp_path, wx_app, english_i18n):
    import wx

    from hpc_gui.wx_logs import WxLogsModel
    from hpc_gui.wx_logs_view import build_logs_panel

    original = "".join(f"ordinary log line {index}\n" for index in range(5000))
    log_file = tmp_path / "large.log"
    log_file.write_text(original, encoding="utf-8")
    parent = wx.Frame(None, title="logs-large-test", size=(900, 600))
    host = build_logs_panel(parent, model=WxLogsModel(log_file))
    parent.Show()
    host.Show()
    parent.Layout()
    controls = host._wx_logs_controls
    assert _pump_until(lambda: host._wx_logs_model.text == original)

    _checkbox_event(wx, controls["collapse_repeats"])
    tree = controls["grouped"]
    assert tree.IsShown()
    assert tree.GetChildrenCount(tree.GetRootItem(), False) == 5000
    _checkbox_event(wx, controls["collapse_repeats"])
    assert controls["text"].GetValue() == original
    parent.Destroy()
