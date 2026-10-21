from types import SimpleNamespace

from hpc_gui.jobs.job_list_controller import JobListBindings, JobListController
from hpc_gui.jobs.output_request_coordinator import OutputRequestBindings, OutputRequestCoordinator


class _Wx:
    LIST_STATE_SELECTED = 1


class _Table:
    def __init__(self):
        self.rows = []
        self.selected = set()

    def GetItemCount(self):
        return len(self.rows)

    def GetItemText(self, index, column=0):
        return self.rows[index][column]

    def GetItemState(self, index, _mask):
        return int(index in self.selected)

    def DeleteAllItems(self):
        self.rows.clear()
        self.selected.clear()

    def InsertItem(self, _index, value):
        self.rows.append([value] + [""] * 7)
        return len(self.rows) - 1

    def SetItem(self, index, column, value):
        self.rows[index][column] = value

    def Select(self, index):
        self.selected.add(index)

    def SetItemState(self, index, _state, _mask):
        self.selected.add(index)


class _Control:
    def __init__(self, value=False):
        self.value = value
        self.enabled = None
        self.shown = None

    def GetValue(self):
        return self.value

    def Enable(self, value):
        self.enabled = value

    def Show(self, value):
        self.shown = value


class _Sizer:
    def Layout(self):
        pass


def test_job_list_controller_filters_and_renders_selected_active_job():
    table = _Table()
    state = {
        "raw_items": [], "items": [], "filter_query": "", "sort_key": "",
        "sort_reverse": False, "selected_job": "1", "bulk_selected_job_ids": {"1"},
        "rendering_jobs": False,
    }
    controller = JobListController(JobListBindings(
        state=state, table=table, page_sizer=_Sizer(), empty_label=_Control(),
        cancel_button=_Control(), hide_finished=_Control(True),
        filter_field=_Control(), column_keys=("job_id",), wx=_Wx(),
    ))
    controller.render_items([
        {"id": "2", "name": "finished", "state": "COMPLETED"},
        {"id": "1", "name": "active", "state": "RUNNING"},
    ])

    assert [row[0] for row in table.rows] == ["1"]
    assert table.rows[0][1:3] == ["active", "RUNNING"]
    assert table.selected == {0}
    assert state["items"][0]["id"] == "1"
    assert state["bulk_selected_job_ids"] == {"1"}


def test_output_requests_coalesce_force_and_reject_stale_selection():
    state = {
        "closed": False, "selected_job": "123", "selected_generation": 4,
        "provider_generation": 2, "outputs_active_generations": set(),
        "outputs_pending_generations": {}, "outputs_requests": 0,
        "outputs_in_flight": False, "outputs_request_id": 0, "outputs_generation": 0,
    }
    store = SimpleNamespace(generation=7)
    session_generation = [9]
    coordinator = OutputRequestCoordinator(OutputRequestBindings(
        state=state, selected_job_store=store, lock=__import__("threading").Lock(),
        session_generation=lambda: session_generation[0],
    ))
    owner = coordinator.owner("123")

    assert coordinator.begin(owner, False) == (1, 1)
    assert coordinator.begin(owner, True) is None
    assert state["outputs_pending_generations"][owner] is True
    assert coordinator.finish(owner) == (True, True)
    assert state["outputs_in_flight"] is False

    stale = coordinator.owner("123")
    state["selected_job"] = "456"
    session_generation[0] += 1
    assert coordinator.is_current(stale) is False
    assert coordinator.begin(stale, False) == (2, 2)
    assert coordinator.finish(stale) == (False, None)
