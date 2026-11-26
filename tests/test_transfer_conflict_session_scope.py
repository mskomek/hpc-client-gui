from __future__ import annotations

from pathlib import Path
import pytest

from hpc_gui.services.transfer_conflict_policy import (
    available_rename_destination, clear_session_conflict_action,
    destination_exists, rename_destination,
)
from hpc_gui.services.transfer_controller import TransferItem
from hpc_gui.services.transfer_session_controller import TransferSessionController


def test_always_use_download_scope_is_shared_across_transfer_sessions():
    clear_session_conflict_action()
    resolver_calls = []
    executed = []

    def resolve(item):
        resolver_calls.append(item.op)
        if len(resolver_calls) == 1:
            return {
                "value": "overwrite",
                "always_use": True,
                "downloads_only": True,
            }
        return "overwrite"

    def run_item(item, _progress, *, conflict_decision=None):
        executed.append((item.op, conflict_decision))

    first = TransferSessionController(
        [TransferItem("upload", "u1", "/u1")],
        run_item,
        conflict_check=lambda _item: True,
        conflict_resolver=resolve,
    )
    first.start()
    assert first.engine.wait(2)

    second = TransferSessionController(
        [
            TransferItem("upload", "u2", "/u2"),
            TransferItem("download", "/d1", "d1"),
        ],
        run_item,
        conflict_check=lambda _item: True,
        conflict_resolver=resolve,
    )
    try:
        second.start()
        assert second.engine.wait(2)
        assert resolver_calls == ["upload", "upload"]
        assert executed == [
            ("upload", "overwrite"),
            ("upload", "overwrite"),
            ("download", "overwrite"),
        ]
    finally:
        clear_session_conflict_action()


def test_session_conditional_action_rechecks_metadata_for_each_file():
    clear_session_conflict_action()
    resolver_calls = []
    executed = []

    def resolve(_item):
        resolver_calls.append("ask")
        return {
            "value": "overwrite_if_newer",
            "always_use": True,
        }

    def evaluate(item, action):
        source_time = 5 if item.src == "newer" else 1
        return "overwrite" if source_time > 2 else "skip"

    controller = TransferSessionController(
        [
            TransferItem("upload", "newer", "/newer"),
            TransferItem("upload", "older", "/older"),
        ],
        lambda item, _progress, **_kwargs: executed.append(item.src),
        conflict_check=lambda _item: True,
        conflict_resolver=resolve,
        conflict_evaluator=evaluate,
    )
    try:
        controller.start()
        assert controller.engine.wait(2)
        assert resolver_calls == ["ask"]
        assert executed == ["newer"]
    finally:
        clear_session_conflict_action()


def test_download_rename_uses_local_namespace(tmp_path):
    class Remote:
        def exists(self, _path):
            pytest.fail("download destination must not probe remote server")

    target = tmp_path / "result.dat"
    target.write_text("original")
    (tmp_path / "result (1).dat").write_text("existing")
    candidate = available_rename_destination(Remote(), "download", str(target))
    assert Path(candidate) == tmp_path / "result (2).dat"
    assert destination_exists(Remote(), "download", str(target))
    assert not destination_exists(Remote(), "download", candidate)
    assert rename_destination("download", str(target), "new.dat") == str(tmp_path / "new.dat")


def test_upload_rename_uses_remote_posix_namespace():
    class Remote:
        def exists(self, path):
            assert path.startswith("/remote/")
            return path == "/remote/result (1).dat"

    assert available_rename_destination(Remote(), "upload", "/remote/result.dat") == "/remote/result (2).dat"


@pytest.mark.parametrize("name", ["", ".", "..", "../bad", "bad/name", "bad\\name"])
def test_rename_rejects_non_basename(name):
    with pytest.raises(ValueError):
        rename_destination("upload", "/remote/result.dat", name)


def test_rename_probe_failure_does_not_offer_unverified_destination():
    class Remote:
        def exists(self, _path):
            raise OSError("connection lost")

    with pytest.raises(OSError, match="connection lost"):
        available_rename_destination(Remote(), "upload", "/remote/result.dat")
