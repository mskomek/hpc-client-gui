import pytest

from hpc_gui.services.file_context_actions import context_selection, visible_actions


def test_context_click_on_unselected_item_becomes_effective_target():
    selection = context_selection("b.txt", False, ("a.txt",), (False,))
    assert selection.effective_paths == ("b.txt",)
    assert "edit" in visible_actions(selection, remote=False)


def test_context_click_inside_multiselection_preserves_all_targets():
    selection = context_selection("b.txt", False, ("a.txt", "b.txt"), (False, False))
    assert selection.effective_paths == ("a.txt", "b.txt")
    assert "rename" not in visible_actions(selection, remote=False)


def test_background_context_has_no_file_target():
    selection = context_selection(None, None, ("a.txt",), (False,), background=True)
    assert selection.effective_paths == ()
    assert "edit" not in visible_actions(selection, remote=False)
    assert "new_folder" in visible_actions(selection, remote=False)


def test_remote_policy_keeps_edit_single_file_only():
    file_selection = context_selection("/a/job.sh", False, ("/a/job.sh",), (False,))
    directory_selection = context_selection("/a", True, ("/a",), (True,))
    assert "edit" in visible_actions(file_selection, remote=True)
    assert "edit" not in visible_actions(directory_selection, remote=True)
    assert "move" in visible_actions(file_selection, remote=True)
    assert "upload" in visible_actions(directory_selection, remote=True)


@pytest.mark.parametrize(
    ("name", "selection", "expected"),
    [
        ("none", context_selection(None, None), {"paste", "refresh", "upload", "new_folder"}),
        ("one_file", context_selection("a", False, ("a",), (False,)), {"open", "open_with", "edit", "edit_new_window", "upload", "rename", "delete", "copy", "cut", "paste", "copy_path", "refresh"}),
        ("one_dir", context_selection("d", True, ("d",), (True,)), {"open", "upload", "new_folder", "new_tab", "delete", "copy", "cut", "paste", "copy_path", "refresh"}),
        ("multi_files", context_selection("b", False, ("a", "b"), (False, False)), {"upload", "delete", "copy", "cut", "paste", "copy_path", "refresh"}),
        ("multi_dirs", context_selection("b", True, ("a", "b"), (True, True)), {"upload", "delete", "copy", "cut", "paste", "copy_path", "refresh"}),
        ("mixed", context_selection("d", True, ("a", "d"), (False, True)), {"upload", "delete", "copy", "cut", "paste", "copy_path", "refresh"}),
    ],
)
def test_local_policy_exact_matrix(name, selection, expected):
    assert set(visible_actions(selection, remote=False)) == expected, name


@pytest.mark.parametrize(
    ("name", "selection", "expected"),
    [
        ("none", context_selection(None, None), {"paste", "refresh", "upload", "new_folder"}),
        ("one_file", context_selection("/a", False, ("/a",), (False,)), {"open", "edit", "edit_new_window", "download", "upload", "rename", "delete", "copy", "move", "paste", "copy_path", "refresh"}),
        ("one_dir", context_selection("/d", True, ("/d",), (True,)), {"open", "download", "upload", "delete", "copy", "move", "paste", "copy_path", "refresh", "new_folder", "new_tab"}),
        ("multi_files", context_selection("/b", False, ("/a", "/b"), (False, False)), {"download", "upload", "delete", "copy", "move", "paste", "copy_path", "refresh"}),
        ("multi_dirs", context_selection("/a", True, ("/a", "/b"), (True, True)), {"download", "upload", "delete", "copy", "move", "paste", "copy_path", "refresh"}),
        ("mixed", context_selection("/d", True, ("/a", "/d"), (False, True)), {"download", "upload", "delete", "copy", "move", "paste", "copy_path", "refresh"}),
    ],
)
def test_remote_policy_exact_matrix(name, selection, expected):
    assert set(visible_actions(selection, remote=True)) == expected, name
