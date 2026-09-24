"""W23 delete-confirmation target identity (FILE-035/036).

REQ: HPC-W06-FILE-035 (target path + item name clear),
     HPC-W06-FILE-036 (confirmation refers to actual target).
Real code: services.file_context_actions summarize/delete helpers +
           wx view _delete_confirm_text wiring (mocked wx.MessageBox text).
Mocked boundary: wx layer only for text capture; helper logic is real.
"""

from hpc_gui.services.file_context_actions import (
    delete_confirm_message,
    summarize_delete_targets,
)


def test_w23_delete_summary_names_target():
    count, where, shown = summarize_delete_targets(["a.txt", "b.txt"], "/tmp/work")
    assert count == 2
    assert where == "/tmp/work"
    assert "a.txt" in shown and "b.txt" in shown


def test_w23_delete_message_contains_path_and_names():
    msg = delete_confirm_message(["a.txt", "b.txt"], "/tmp/work")
    assert "/tmp/work" in msg
    assert "a.txt" in msg and "b.txt" in msg


def test_w23_delete_message_truncates_long_selection():
    names = [f"f{i}.txt" for i in range(10)]
    msg = delete_confirm_message(names, "/tmp/work", max_names=3)
    assert "+7 more" in msg
    assert "/tmp/work" in msg


def test_w23_delete_message_empty_falls_back_to_generic():
    assert delete_confirm_message([], "/tmp/work") == "Delete the selected items?"


def test_w23_view_confirm_wiring_mentions_target():
    import pathlib

    for rel in ("src/hpc_gui/wx_local_files.py", "src/hpc_gui/wx_remote_files_view.py"):
        text = pathlib.Path(rel).read_text(encoding="utf-8")
        assert "_delete_confirm_text" in text
        assert "dirs.delete_confirm_detail" in text
