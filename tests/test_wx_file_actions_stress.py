from hpc_gui.services.file_context_actions import context_selection, visible_actions
from mock_hpc_files import MockRemoteFilesBackend


def test_file_context_target_stress_has_no_wrong_targets():
    wrong = 0
    for index in range(200):
        path = f"/work/item-{index}"
        clicked = context_selection(path, False, ("/work/other",), (False,))
        if clicked.effective_paths != (path,):
            wrong += 1
    assert wrong == 0


def test_remote_mutation_stress_has_no_lost_operations():
    backend = MockRemoteFilesBackend()
    for index in range(100):
        source = f"/work/item-{index}"
        backend.entries[source] = False
        backend.rename(source, f"/work/renamed-{index}")
        backend.move(f"/work/renamed-{index}", f"/work/moved-{index}")
    assert len([call for call in backend.calls if call[0] == "rename"]) == 100
    assert len([call for call in backend.calls if call[0] == "move"]) == 100
    assert len([name for name in backend.entries if name.startswith("/work/moved-")]) == 100


def test_context_policy_stays_stable_under_rapid_selection():
    for index in range(200):
        selection = context_selection(f"/work/{index}", False, (f"/work/{index}",), (False,))
        assert "edit" in visible_actions(selection, remote=True)
