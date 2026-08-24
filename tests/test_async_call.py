from types import SimpleNamespace

from hpc_gui.ui.async_call import AsyncCall


class _DeletedSignal:
    def emit(self, *_args):
        raise RuntimeError("Signal source has been deleted")


def test_late_async_result_after_signal_deletion_is_ignored():
    call = AsyncCall("token", lambda: "result")
    call.signals = SimpleNamespace(finished=_DeletedSignal(), failed=_DeletedSignal())

    call.run()
