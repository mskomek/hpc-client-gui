"""Jobs/Outputs target assignment through the GUI-independent follower service."""

from types import SimpleNamespace

from hpc_gui.jobs import manual_output_followers as module
from hpc_gui.jobs.manual_output_followers import ManualOutputFollowers


def _service():
    state = {"tracked_outputs": [], "followers": {}}
    context = SimpleNamespace(job_id="42", generation=3)
    model = SimpleNamespace(selected_job_store=SimpleNamespace(context=context))
    calls = []
    page = object()
    bindings = SimpleNamespace(
        state=state,
        model=model,
        host=object(),
        lifecycle=None,
        files_browser=None,
        remote_reader=lambda _path: "contents",
        remote_statter=None,
        channel_paths={},
        channels={},
        resolve_channels=lambda: ["stdout", "stderr"],
        ensure_tabs=lambda channels: calls.append(("ensure", channels)),
        refresh_single=lambda target: calls.append(("refresh_single", target)),
        refresh_outputs=lambda **kwargs: calls.append(("refresh", kwargs)),
        select_page=lambda selected: calls.append(("select", selected)),
        outputs_page=page,
    )
    return ManualOutputFollowers(bindings), state, calls, page


def test_follow_stderr_then_assign_stdout_to_same_tab_target():
    service, state, calls, page = _service()

    service.follow_file("/tmp/stderr.log")
    tracked = state["tracked_outputs"][0]
    follower = state["followers"][tracked.tracking_id]
    assert tracked.path == "/tmp/stderr.log"
    assert follower.state.roles == ("manual",)

    service.follow_file("/tmp/stdout.log", mode="existing", follower_id=tracked.tracking_id)

    assert state["tracked_outputs"][0].tracking_id == tracked.tracking_id
    assert state["tracked_outputs"][0].path == "/tmp/stdout.log"
    assert follower.state.path == "/tmp/stdout.log"
    assert follower.state.offset == 0
    assert calls == [
        ("ensure", ["stdout", "stderr"]),
        ("refresh_single", tracked.tracking_id),
        ("select", page),
        ("refresh", {"force": True}),
        ("select", page),
    ]


def test_follow_window_close_removes_only_its_target(monkeypatch):
    service, state, calls, _page = _service()
    opened = {}

    def show(_host, _model, tracking_id, *, follower, on_closed, **_kwargs):
        opened.update(tracking_id=tracking_id, follower=follower, on_closed=on_closed)
        return 7

    monkeypatch.setattr(module, "show_job_output", show)
    service.follow_file("/tmp/stdout.log", mode="new_window")
    assert len(state["tracked_outputs"]) == 1
    assert opened["follower"].state.path == "/tmp/stdout.log"

    opened["on_closed"]()

    assert state["tracked_outputs"] == []
    assert state["followers"] == {}
    assert calls == [("refresh", {"force": True})]


def test_follow_without_selected_job_does_not_create_target():
    service, state, calls, _page = _service()
    service.bindings.model.selected_job_store.context.job_id = ""

    service.follow_file("/tmp/output.log")

    assert state["tracked_outputs"] == []
    assert state["followers"] == {}
    assert calls == []
