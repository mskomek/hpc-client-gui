from hpc_gui.services.remote_directory_controller import RemoteDirectoryController
from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.services.transfer_session_controller import TransferSessionController


def test_transfer_queue_conflict_checksum_and_status():
    session = TransferSessionController([TransferItem("upload", "a", "b")], lambda item, progress: None)
    assert session.status().queued == 1
    session.set_conflict_policy("skip")
    session.set_checksum_enabled(True)
    assert session.conflict_policy == "skip" and session.checksum_enabled


def test_remote_navigation_favorites_and_stale_listing():
    controller = RemoteDirectoryController()
    first = controller.navigate("/one")
    second = controller.navigate("/two")
    assert not controller.is_current(first) and controller.is_current(second)
    assert controller.toggle_favorite("/two")
    assert not controller.toggle_favorite("/two")
    assert controller.back() is not None


def test_controllers_have_no_qt_imports():
    for name in ("hpc_gui.services.transfer_session_controller", "hpc_gui.services.remote_directory_controller"):
        assert "PySide" not in __import__(name, fromlist=["__name"]).__dict__
