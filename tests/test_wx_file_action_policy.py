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
    selection = context_selection(None, None, ("a.txt",), (False,))
    assert selection.effective_paths == ("a.txt",)
    assert "new_folder" not in visible_actions(selection, remote=False)


def test_remote_policy_keeps_edit_single_file_only():
    file_selection = context_selection("/a/job.sh", False, ("/a/job.sh",), (False,))
    directory_selection = context_selection("/a", True, ("/a",), (True,))
    assert "edit" in visible_actions(file_selection, remote=True)
    assert "edit" not in visible_actions(directory_selection, remote=True)
