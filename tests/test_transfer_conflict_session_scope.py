from __future__ import annotations

from hpc_gui.services.transfer_conflict_policy import clear_session_conflict_action
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
