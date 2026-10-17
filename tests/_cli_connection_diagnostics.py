from __future__ import annotations
from _cli_test_support import (
    json,
    patch,
    pytest,
    run_cli,
    run_connection_diagnostics,
    SSHConnInfo,
)

def _diag_fixture(statuses: dict[str, str]) -> dict:
    return {
        "status": "PASS" if all(value == "PASS" for value in statuses.values()) else "FAIL",
        "profile": "",
        "stages": {
            name: {"status": status, "detail": "detail"}
            for name, status in statuses.items()
        },
    }


@pytest.mark.integration
@pytest.mark.semantic
def test_diagnostics_socket_fail_marks_later_stages_not_attempted() -> None:
    info = SSHConnInfo(host="cluster.example", port=22)
    payload = run_connection_diagnostics(
        info,
        socket_connect=lambda *_args: (_ for _ in ()).throw(OSError("connection refused")),
        ssh_factory=lambda _info: (_ for _ in ()).throw(AssertionError("unused")),
        checksum_probe=lambda _wrapper: 0,
    )
    assert payload["status"] == "FAIL"
    assert payload["stages"]["port"] == {"status": "FAIL", "detail": "port not reachable"}
    for name in ("auth", "sftp", "checksum"):
        assert payload["stages"][name]["status"] == "not_attempted"
        assert "connection refused" not in payload["stages"][name]["detail"]


@pytest.mark.integration
@pytest.mark.semantic
def test_diagnostics_auth_fail_after_port_pass() -> None:
    info = SSHConnInfo(host="cluster.example", port=22)
    payload = run_connection_diagnostics(
        info,
        socket_connect=lambda *_args: True,
        ssh_factory=lambda _info: (_ for _ in ()).throw(RuntimeError("bad credentials")),
        checksum_probe=lambda _wrapper: 0,
    )
    assert payload["stages"]["port"]["status"] == "PASS"
    assert payload["stages"]["auth"] == {"status": "FAIL", "detail": "authentication failed"}
    assert payload["stages"]["sftp"]["status"] == "not_attempted"
    assert payload["stages"]["checksum"]["status"] == "not_attempted"
    assert payload["status"] == "FAIL"


@pytest.mark.integration
@pytest.mark.semantic
def test_diagnostics_sftp_probe_fail_after_auth_pass() -> None:
    class Wrapper:
        def supports_transfer_sftp_channels(self):
            raise OSError("sftp channel broken")

        def close(self):
            pass

    info = SSHConnInfo(host="cluster.example", port=22)
    payload = run_connection_diagnostics(
        info,
        socket_connect=lambda *_args: True,
        ssh_factory=lambda _info: Wrapper(),
        checksum_probe=lambda _wrapper: 0,
    )
    assert payload["stages"]["port"]["status"] == "PASS"
    assert payload["stages"]["auth"]["status"] == "PASS"
    assert payload["stages"]["sftp"] == {"status": "FAIL", "detail": "sftp subsystem unavailable"}
    assert payload["stages"]["checksum"]["status"] == "not_attempted"
    assert payload["status"] == "FAIL"


@pytest.mark.integration
@pytest.mark.semantic
def test_diagnostics_checksum_nonzero_exit_marks_checksum_fail() -> None:
    class Wrapper:
        def supports_transfer_sftp_channels(self):
            return True

        def close(self):
            pass

    info = SSHConnInfo(host="cluster.example", port=22)
    payload = run_connection_diagnostics(
        info,
        socket_connect=lambda *_args: True,
        ssh_factory=lambda _info: Wrapper(),
        checksum_probe=lambda _wrapper: 1,
    )
    for name in ("port", "auth", "sftp"):
        assert payload["stages"][name]["status"] == "PASS"
    assert payload["stages"]["checksum"]["status"] == "FAIL"
    assert payload["stages"]["checksum"]["detail"] == "checksum tool not found"
    assert payload["status"] == "FAIL"


@pytest.mark.integration
@pytest.mark.semantic
def test_diagnostics_all_stages_pass_and_wrapper_closed() -> None:
    closed: list[bool] = []
    connected_socket = object()
    received_sockets: list[object] = []

    class Wrapper:
        def supports_transfer_sftp_channels(self):
            return True

        def close(self):
            closed.append(True)

    def ssh_factory(info):
        received_sockets.append(info.preconnected_socket)
        return Wrapper()

    info = SSHConnInfo(host="cluster.example", port=22)
    payload = run_connection_diagnostics(
        info,
        socket_connect=lambda *_args: connected_socket,
        ssh_factory=ssh_factory,
        checksum_probe=lambda _wrapper: 0,
    )
    assert payload["status"] == "PASS"
    assert payload["stages"]["port"] == {"status": "PASS", "detail": "reachable"}
    assert payload["stages"]["auth"] == {"status": "PASS", "detail": "authenticated"}
    assert payload["stages"]["sftp"] == {"status": "PASS", "detail": "sftp subsystem available"}
    assert payload["stages"]["checksum"] == {"status": "PASS", "detail": "sha256sum available"}
    assert closed == [True]
    assert received_sockets == [connected_socket]


@pytest.mark.contract
@pytest.mark.semantic
def test_doctor_connection_all_pass_exit_zero_json_four_stages(capsys) -> None:
    fixture = _diag_fixture({"port": "PASS", "auth": "PASS", "sftp": "PASS", "checksum": "PASS"})
    with patch("hpc_gui.cli._doctor_commands.run_connection_diagnostics", return_value=fixture):
        assert run_cli(["--format", "json", "--host", "host", "doctor", "connection"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "PASS"
    assert set(payload["stages"]) == {"port", "auth", "sftp", "checksum"}


@pytest.mark.contract
@pytest.mark.semantic
def test_doctor_connection_any_fail_exit_three_json_four_stages(capsys) -> None:
    fixture = _diag_fixture(
        {"port": "PASS", "auth": "FAIL", "sftp": "not_attempted", "checksum": "not_attempted"}
    )
    with patch("hpc_gui.cli._doctor_commands.run_connection_diagnostics", return_value=fixture):
        assert run_cli(["--format", "json", "--host", "host", "doctor", "connection"]) == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "FAIL"
    assert set(payload["stages"]) == {"port", "auth", "sftp", "checksum"}


@pytest.mark.contract
@pytest.mark.semantic
def test_doctor_connection_text_exposes_same_stage_names(capsys) -> None:
    fixture = _diag_fixture(
        {"port": "PASS", "auth": "PASS", "sftp": "PASS", "checksum": "FAIL"}
    )
    with patch("hpc_gui.cli._doctor_commands.run_connection_diagnostics", return_value=fixture):
        assert run_cli(["--host", "host", "doctor", "connection"]) == 3
    out = capsys.readouterr().out
    assert "status: FAIL" in out
    assert "stages:" in out
    for name in ("port", "auth", "sftp", "checksum"):
        assert f'"{name}"' in out


@pytest.mark.integration
@pytest.mark.semantic
def test_doctor_connection_never_leaks_raw_exception_detail(capsys) -> None:
    secret = "TOP-SECRET-CREDENTIAL-9f4a"

    def bad_factory(_info):
        raise RuntimeError(f"auth rejected: {secret}")

    def wrapped(info):
        return run_connection_diagnostics(
            info,
            socket_connect=lambda *_args: True,
            ssh_factory=bad_factory,
            checksum_probe=lambda _wrapper: 0,
        )

    with patch("hpc_gui.cli._doctor_commands.run_connection_diagnostics", wrapped):
        assert run_cli(["--host", "host", "doctor", "connection"]) == 3
    captured = capsys.readouterr()
    assert secret not in captured.out + captured.err
    assert "authentication failed" in captured.out
    assert "TOP-SECRET" not in captured.out + captured.err
