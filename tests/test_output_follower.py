from threading import Event, Thread

from hpc_gui.services.output_follower import OutputFollower, OutputFollowerState


def _follower(path="/work/output.log", max_lines=5):
    return OutputFollower(
        OutputFollowerState(
            tracking_id="follower-test",
            channel_id=None,
            job_id="42",
            generation=1,
            label="output.log",
            path=path,
            origin="manual",
        ),
        max_lines=max_lines,
    )


def test_follower_reads_actual_path_and_bounds_repeated_appends():
    files = {"/work/output.log": "line-0\n"}
    follower = _follower()

    follower.poll(lambda path: files[path])
    for index in range(1, 12):
        files["/work/output.log"] += f"line-{index}\n"
        follower.poll(lambda path: files[path])

    assert "line-0" not in follower.text
    assert "line-11\n" in follower.text
    assert len(follower.text.splitlines()) == 5
    assert follower.state.path == "/work/output.log"


def test_follower_waits_then_resumes_and_handles_truncate():
    files = {}
    follower = _follower()

    def read(path):
        try:
            return files[path]
        except KeyError as error:
            raise FileNotFoundError(path) from error

    _, _, waiting = follower.poll(read, force=True)
    assert waiting is True
    assert follower.state.waiting_state == 1

    files["/work/output.log"] = "old-1\nold-2\n"
    _, retained, waiting = follower.poll(read, force=True)
    assert waiting is False
    assert retained == "old-1\nold-2\n"

    files["/work/output.log"] = "new\n"
    _, retained, waiting = follower.poll(read, force=True)
    assert waiting is False
    assert retained == "new\n"
    assert follower.state.offset == len("new\n")


def test_follower_reassignment_resets_source_and_offset():
    files = {"/work/a.log": "A\n", "/work/b.log": "B\n"}
    follower = _follower("/work/a.log")
    follower.poll(lambda path: files[path])

    follower.assign(
        channel_id=None,
        job_id="42",
        generation=2,
        label="b.log",
        path="/work/b.log",
        origin="manual",
        roles=("manual",),
    )
    _, retained, waiting = follower.poll(lambda path: files[path])

    assert waiting is False
    assert retained == "B\n"
    assert "A" not in retained
    assert follower.state.offset == len("B\n")


def test_follower_reassignment_invalidates_inflight_old_read():
    started = Event()
    release = Event()
    files = {"/work/a.log": "A\n", "/work/b.log": "B\n"}
    follower = _follower("/work/a.log")

    def read(path):
        if path == "/work/a.log":
            started.set()
            release.wait(1)
        return files[path]

    worker = Thread(target=lambda: follower.poll(read), daemon=True)
    worker.start()
    assert started.wait(1)
    follower.assign(
        channel_id=None,
        job_id="42",
        generation=2,
        label="b.log",
        path="/work/b.log",
        origin="manual",
        roles=("manual",),
    )
    release.set()
    worker.join(1)
    _, retained, waiting = follower.poll(read, force=True)

    assert waiting is False
    assert retained == "B\n"
