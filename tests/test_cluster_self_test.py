from __future__ import annotations

from hpc_gui.services.cluster_self_test import FAIL, NOT_CONFIGURED, PASS, WARNING, run_cluster_self_test
from hpc_gui.ssh.client import SSHConnInfo


class _Wrapper:
    def __init__(self, commands: dict[str, int]):
        self.commands = commands
        self.closed = False

    def supports_transfer_sftp_channels(self):
        return True

    def run(self, command, **_kwargs):
        return self.commands.get(command, 0), "", ""

    def close(self):
        self.closed = True


def _run(commands=None, **kwargs):
    wrapper = _Wrapper(commands or {})
    result = run_cluster_self_test(
        SSHConnInfo(host="cluster.example", port=22, username="alice"),
        dns_resolve=kwargs.pop("dns_resolve", lambda *_: None),
        socket_connect=lambda *_: object(),
        ssh_factory=lambda _info: wrapper,
        **kwargs,
    )
    return result


def test_self_test_statuses_and_optional_failures():
    result = _run({"command -v sha256sum": 1, "command -v squeue": 1})
    items = {item.id: item for section in result.sections for item in section.items}
    assert result.status == WARNING
    assert items["ssh"].status == PASS
    assert items["squeue"].status == WARNING
    assert items["checksum"].status == WARNING
    assert items["quota"].status == NOT_CONFIGURED


def test_self_test_critical_failure_and_required_scheduler_tool():
    result = _run({"command -v squeue": 1}, required_scheduler_tools=("squeue",))
    items = {item.id: item for section in result.sections for item in section.items}
    assert items["squeue"].status == FAIL
    assert result.status == FAIL


def test_self_test_connection_failures_are_critical_and_later_probes_not_tested():
    dns = _run(dns_resolve=lambda *_: (_ for _ in ()).throw(OSError()))
    assert dns.status == FAIL
    assert next(item for section in dns.sections for item in section.items if item.id == "dns").status == FAIL
    assert next(item for section in dns.sections for item in section.items if item.id == "squeue").status == "NOT_TESTED"

    sftp = _Wrapper({})
    sftp.supports_transfer_sftp_channels = lambda: False
    result = run_cluster_self_test(
        SSHConnInfo(host="cluster.example", port=22),
        dns_resolve=lambda *_: None,
        socket_connect=lambda *_: object(),
        ssh_factory=lambda _info: sftp,
    )
    items = {item.id: item for section in result.sections for item in section.items}
    assert result.status == FAIL
    assert items["sftp"].status == FAIL
    assert items["checksum"].status == "NOT_TESTED"


def test_self_test_storage_account_and_probe_exception_are_safe():
    result = _run(
        {"command -v squeue": 0},
        provider={"name": "Example", "storage": [{"id": "project", "path_template": "/p/{project}"}]},
    )
    items = {item.id: item for section in result.sections for item in section.items}
    assert items["project"].status == NOT_CONFIGURED

    class Broken(_Wrapper):
        def run(self, command, **kwargs):
            if command == "command -v sha256sum":
                raise RuntimeError("disconnected")
            return super().run(command, **kwargs)

    broken = Broken({})
    result = run_cluster_self_test(
        SSHConnInfo(host="cluster.example", port=22),
        dns_resolve=lambda *_: None,
        socket_connect=lambda *_: object(),
        ssh_factory=lambda _info: broken,
    )
    items = {item.id: item for section in result.sections for item in section.items}
    assert items["checksum"].status == WARNING
