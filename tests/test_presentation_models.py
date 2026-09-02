import gc

from hpc_gui.services.presentation_models import EventBus, ProgressViewModel, StatusViewModel


def test_boundary_models_and_fake_adapter():
    assert StatusViewModel("connected", "Connected").state == "connected"
    assert ProgressViewModel(2, 4).total == 4
    events = []

    class FakeAdapter:
        def receive(self, event):
            events.append(event)

    adapter = FakeAdapter()
    bus = EventBus()
    bus.subscribe(adapter.receive)
    bus.publish("ready")
    assert events == ["ready"]
    del adapter
    gc.collect()
    bus.publish("discarded")
    assert events == ["ready"]


def test_boundary_source_has_no_toolkit_imports():
    source = open("src/hpc_gui/services/presentation_models.py", encoding="utf-8").read()
    assert "PySide" not in source and "wx" not in source
