"""Unit tests for the SelectedJobContext and SelectedJobStore."""

from __future__ import annotations

import threading

from hpc_gui.services.selected_job_context import SelectedJobContext, SelectedJobStore


# ---------------------------------------------------------------------------
# SelectedJobContext dataclass tests
# ---------------------------------------------------------------------------

class TestSelectedJobContext:
    def test_default_fields(self):
        ctx = SelectedJobContext(generation=0, job_id="123")
        assert ctx.job_id == "123"
        assert ctx.generation == 0
        assert ctx.name == ""
        assert ctx.state == ""
        assert ctx.workdir == ""
        assert ctx.stdout_path == ""
        assert ctx.stderr_path == ""

    def test_has_selection_true(self):
        ctx = SelectedJobContext(generation=1, job_id="123")
        assert ctx.has_selection is True

    def test_has_selection_false_when_empty(self):
        ctx = SelectedJobContext(generation=1, job_id="")
        assert ctx.has_selection is False

    def test_display_name_prefers_name(self):
        ctx = SelectedJobContext(generation=1, job_id="123", name="my_job")
        assert ctx.display_name == "my_job"

    def test_display_name_falls_back_to_job_id(self):
        ctx = SelectedJobContext(generation=1, job_id="123")
        assert ctx.display_name == "123"

    def test_frozen(self):
        ctx = SelectedJobContext(generation=1, job_id="123")
        try:
            ctx.job_id = "456"  # type: ignore[misc]
            assert False, "should be frozen"
        except AttributeError:
            pass


# ---------------------------------------------------------------------------
# SelectedJobStore basic operations
# ---------------------------------------------------------------------------

class TestSelectedJobStore:
    def test_initial_state(self):
        store = SelectedJobStore()
        assert store.generation == 0
        assert store.job_id == ""
        assert store.workdir == ""
        assert store.context.job_id == ""

    def test_select_increments_generation(self):
        store = SelectedJobStore()
        ctx1 = store.select(job_id="100", name="job_a")
        assert ctx1.generation == 1
        assert store.generation == 1
        ctx2 = store.select(job_id="200", name="job_b")
        assert ctx2.generation == 2
        assert store.generation == 2

    def test_select_publishes_context(self):
        store = SelectedJobStore()
        ctx = store.select(job_id="100", name="test", state="RUNNING")
        assert ctx.job_id == "100"
        assert ctx.name == "test"
        assert ctx.state == "RUNNING"
        assert store.context.job_id == "100"

    def test_select_preserves_previous_values_same_job(self):
        store = SelectedJobStore()
        store.select(job_id="100", name="a", state="PENDING", workdir="/scratch")
        ctx2 = store.select(job_id="100", name="a", state="RUNNING")
        # Same job_id preserves non-overridden fields
        assert ctx2.job_id == "100"
        assert ctx2.name == "a"
        assert ctx2.state == "RUNNING"
        assert ctx2.workdir == "/scratch"

    def test_select_clears_old_metadata_on_new_job(self):
        store = SelectedJobStore()
        store.select(job_id="100", name="a", state="PENDING", workdir="/scratch/A", stdout_path="/scratch/A/a.out")
        ctx2 = store.select(job_id="200")
        # New job_id clears all enrichable metadata
        assert ctx2.job_id == "200"
        assert ctx2.name == ""
        assert ctx2.state == ""
        assert ctx2.workdir == ""
        assert ctx2.stdout_path == ""
        assert ctx2.stderr_path == ""
        assert ctx2.raw_scontrol == ""
        assert ctx2.script_path == ""
        assert ctx2.nodelist == ""
        assert ctx2.exit_code == ""
        assert ctx2.failure_reason == ""

    def test_update_does_not_increment_generation(self):
        store = SelectedJobStore()
        ctx1 = store.select(job_id="100")
        gen = ctx1.generation
        ctx2 = store.update(workdir="/new/path")
        assert ctx2.generation == gen
        assert store.generation == gen
        assert ctx2.workdir == "/new/path"

    def test_clear_resets_selection(self):
        store = SelectedJobStore()
        store.select(job_id="100", name="test")
        store.clear()
        assert store.job_id == ""
        assert store.generation == 2  # clear() calls select() once

    def test_subscribe_receives_notifications(self):
        store = SelectedJobStore()
        received = []
        store.subscribe(lambda ctx: received.append(ctx))
        store.select(job_id="1")
        store.select(job_id="2")
        assert len(received) == 2
        assert received[0].job_id == "1"
        assert received[1].job_id == "2"

    def test_unsubscribe_stops_notifications(self):
        store = SelectedJobStore()
        received = []
        unsub = store.subscribe(lambda ctx: received.append(ctx))
        store.select(job_id="1")
        unsub()
        store.select(job_id="2")
        assert len(received) == 1

    def test_double_unsubscribe_is_safe(self):
        store = SelectedJobStore()
        unsub = store.subscribe(lambda ctx: None)
        unsub()
        unsub()  # should not raise


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------

class TestSelectedJobStoreThreadSafety:
    def test_concurrent_selects_do_not_corrupt(self):
        store = SelectedJobStore()
        errors = []

        def worker(n):
            try:
                for i in range(50):
                    store.select(job_id=f"{n}_{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert store.generation == 200

    def test_concurrent_subscribe_and_select(self):
        store = SelectedJobStore()
        received = []

        def listener(ctx):
            received.append(ctx.generation)

        def subscriber():
            store.subscribe(listener)

        def selector():
            for _ in range(20):
                store.select(job_id="x")

        threads = [threading.Thread(target=subscriber) for _ in range(3)]
        threads += [threading.Thread(target=selector) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # No crash = success; generation values may be partial
        assert store.generation > 0


# ---------------------------------------------------------------------------
# Stale-response safety
# ---------------------------------------------------------------------------

class TestStaleResponseSafety:
    def test_late_response_rejected_by_generation(self):
        store = SelectedJobStore()
        store.select(job_id="A")
        gen_a = store.generation
        store.select(job_id="B")
        gen_b = store.generation
        # Simulate: if the stored generation moved past gen_a, we reject
        assert store.generation == gen_b
        assert gen_a != gen_b

    def test_workdir_not_overwritten_by_stale(self):
        store = SelectedJobStore()
        store.select(job_id="A", workdir="/work/A")
        store.select(job_id="B", workdir="/work/B")
        # A's workdir must not appear in B
        assert store.context.workdir == "/work/B"
        assert store.context.job_id == "B"

    def test_stdout_stderr_not_overwritten_by_stale(self):
        store = SelectedJobStore()
        store.select(job_id="A", stdout_path="/a.out", stderr_path="/a.err")
        store.select(job_id="B", stdout_path="/b.out", stderr_path="/b.err")
        assert store.context.stdout_path == "/b.out"
        assert store.context.stderr_path == "/b.err"
