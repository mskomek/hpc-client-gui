from hpc_gui.services.quota_monitor import (
    QuotaBackend, QuotaBackendRegistry, QuotaMonitor, QuotaResult,
)
from threading import Event


def test_unconfigured_source_never_creates_transport_work():
    calls = []
    monitor = QuotaMonitor(QuotaBackendRegistry(), lambda *args: calls.append(args))
    assert monitor.refresh({"enabled": False, "command_template": ""},
                           connection_id="c", provider_id="p", subject="u") is None
    assert calls == []
    monitor.close()


def test_eligible_fake_backend_coalesces_and_parses():
    calls = []
    started = Event()
    release = Event()
    backend = QuotaBackend("fake", lambda source: "fake --subject " + source["subject_template"],
                           lambda output: QuotaResult("ok", used_bytes=3))
    def transport(command, timeout, limit):
        calls.append((command, timeout, limit))
        started.set()
        release.wait(1)
        return "3"
    monitor = QuotaMonitor(QuotaBackendRegistry([backend]), transport)
    source = {"id": "s", "enabled": True, "consent": True, "backend_id": "fake",
              "command_template": "fake {user}", "subject_template": "u", "scope": "user"}
    first = monitor.refresh(source, connection_id="c", provider_id="p", subject="u")
    assert started.wait(1)
    second = monitor.refresh(source, connection_id="c", provider_id="p", subject="u")
    assert first is second
    release.set()
    assert first.result().used_bytes == 3
    assert len(calls) == 1
    monitor.close()
