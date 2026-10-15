from __future__ import annotations
from _cli_test_support import (
    hashlib,
    json,
    Path,
    patch,
    pytest,
    ExitCode,
    run_cli,
    SMOKE_STAGES,
    run_sftp_smoke,
)
from _cli_transfer_policies import FakeFiles

class _MkdirFailFiles(FakeFiles):
    def mkdir(self, path):
        raise OSError("mkdir denied")


class _UploadFailFiles(FakeFiles):
    def upload(self, local_path, remote_path, progress_cb=None):
        raise OSError("upload denied")


class _ListOmitFiles(FakeFiles):
    def listdir_entries(self, path):
        return []


class _DownloadFailFiles(FakeFiles):
    def download(self, remote_path, local_path, progress_cb=None):
        raise OSError("download denied")


class _DownloadCorruptFiles(FakeFiles):
    def download(self, remote_path, local_path, progress_cb=None):
        Path(local_path).write_bytes(b"corrupted")


@pytest.mark.unit
@pytest.mark.semantic
def test_smoke_all_stages_pass_fixed_order_and_content_round_trip() -> None:
    files = FakeFiles()
    payload = run_sftp_smoke(files, temp_dir_name=lambda: "smoke_dir")
    assert payload["status"] == "PASS"
    assert payload["temp_dir"] == "smoke_dir"
    assert list(payload["stages"]) == list(SMOKE_STAGES)
    assert set(payload["stages"]) == set(SMOKE_STAGES)
    for name in SMOKE_STAGES:
        assert payload["stages"][name]["status"] == "PASS"
    assert files.remote["smoke_dir/smoke.bin"] == b"truba-sftp-smoke"
    assert files.calls["download"] == ["smoke_dir/smoke.bin"]
    assert files.calls["sha256"] == ["smoke_dir/smoke.bin"]
    assert files.calls["remove"] == ["smoke_dir"]


@pytest.mark.unit
@pytest.mark.semantic
def test_smoke_mkdir_fail_marks_later_stages_not_attempted() -> None:
    payload = run_sftp_smoke(_MkdirFailFiles(), temp_dir_name=lambda: "smoke_dir")
    assert payload["status"] == "FAIL"
    assert set(payload["stages"]) == set(SMOKE_STAGES)
    assert payload["stages"]["temp_dir"]["status"] == "FAIL"
    for name in ("upload", "list", "download", "checksum"):
        assert payload["stages"][name]["status"] == "not_attempted"
    assert payload["stages"]["cleanup"] == {"status": "not_attempted", "detail": "no temp directory"}
    assert "denied" not in payload["stages"]["temp_dir"]["detail"]


@pytest.mark.unit
@pytest.mark.semantic
def test_smoke_upload_fail_marks_list_download_not_attempted() -> None:
    payload = run_sftp_smoke(_UploadFailFiles(), temp_dir_name=lambda: "smoke_dir")
    assert payload["status"] == "FAIL"
    assert set(payload["stages"]) == set(SMOKE_STAGES)
    assert payload["stages"]["temp_dir"]["status"] == "PASS"
    assert payload["stages"]["upload"]["status"] == "FAIL"
    for name in ("list", "download", "checksum"):
        assert payload["stages"][name]["status"] == "not_attempted"
    assert payload["stages"]["cleanup"]["status"] == "PASS"
    assert "denied" not in payload["stages"]["upload"]["detail"]


@pytest.mark.unit
@pytest.mark.semantic
def test_smoke_list_omits_file_marks_download_not_attempted() -> None:
    payload = run_sftp_smoke(_ListOmitFiles(), temp_dir_name=lambda: "smoke_dir")
    assert payload["status"] == "FAIL"
    assert set(payload["stages"]) == set(SMOKE_STAGES)
    for name in ("temp_dir", "upload"):
        assert payload["stages"][name]["status"] == "PASS"
    assert payload["stages"]["list"]["status"] == "FAIL"
    assert payload["stages"]["download"]["status"] == "not_attempted"
    assert payload["stages"]["checksum"]["status"] == "not_attempted"
    assert payload["stages"]["cleanup"]["status"] == "PASS"


@pytest.mark.unit
@pytest.mark.semantic
@pytest.mark.parametrize(
    "backend_cls",
    [_DownloadFailFiles, _DownloadCorruptFiles],
    ids=["download-raises", "download-wrong-bytes"],
)
def test_smoke_download_fail_preserves_completed_passes(backend_cls) -> None:
    payload = run_sftp_smoke(backend_cls(), temp_dir_name=lambda: "smoke_dir")
    assert payload["status"] == "FAIL"
    assert set(payload["stages"]) == set(SMOKE_STAGES)
    for name in ("temp_dir", "upload", "list"):
        assert payload["stages"][name]["status"] == "PASS"
    assert payload["stages"]["download"]["status"] == "FAIL"
    assert payload["stages"]["checksum"]["status"] == "not_attempted"
    assert payload["stages"]["cleanup"]["status"] == "PASS"


@pytest.mark.unit
@pytest.mark.semantic
def test_smoke_checksum_mismatch_fails_but_runs_cleanup() -> None:
    class _ChecksumMismatchFiles(FakeFiles):
        def sha256(self, path):
            return hashlib.sha256(b"different").hexdigest()

    payload = run_sftp_smoke(_ChecksumMismatchFiles(), temp_dir_name=lambda: "smoke_dir")
    assert payload["status"] == "FAIL"
    assert payload["stages"]["download"]["status"] == "PASS"
    assert payload["stages"]["checksum"]["status"] == "FAIL"
    assert payload["stages"]["checksum"]["detail"] == "checksum mismatch"
    assert payload["stages"]["cleanup"]["status"] == "PASS"


class _RemoveFailFiles(FakeFiles):
    def remove(self, path, recursive=False):
        raise OSError("remove denied")


@pytest.mark.unit
@pytest.mark.semantic
@pytest.mark.parametrize(
    ("files", "cleanup_flag", "status", "detail"),
    [
        (FakeFiles(), False, "not_attempted", "skipped"),
        (_RemoveFailFiles(), True, "FAIL", "cleanup failed"),
    ],
)
def test_smoke_cleanup_not_pass_combos(files, cleanup_flag, status, detail) -> None:
    payload = run_sftp_smoke(files, temp_dir_name=lambda: "smoke_dir", cleanup=cleanup_flag)
    assert payload["status"] == "FAIL"
    assert payload["stages"]["cleanup"]["status"] == status
    assert payload["stages"]["cleanup"]["detail"] == detail
    if status == "not_attempted":
        assert files.calls["remove"] == []


def _smoke_fixture(statuses: dict[str, str], temp_dir: str = "/tmp/truba-smoke") -> dict:
    return {
        "status": "PASS" if all(value == "PASS" for value in statuses.values()) else "FAIL",
        "profile": "",
        "temp_dir": temp_dir,
        "stages": {
            name: {"status": status, "detail": "detail"}
            for name, status in statuses.items()
        },
    }


def _smoke_all_pass() -> dict:
    return _smoke_fixture({name: "PASS" for name in SMOKE_STAGES})


_PARTIAL = {"temp_dir": "PASS", "upload": "PASS", "list": "FAIL", "download": "not_attempted", "checksum": "not_attempted", "cleanup": "PASS"}


class _FakeSmokeSession:
    files = object()

    def close(self):
        pass


@pytest.mark.unit
@pytest.mark.semantic
@pytest.mark.parametrize(
    ("extra_args", "expected_cleanup"),
    [([], True), (["--keep"], False)],
)
def test_doctor_smoke_keep_flag_controls_cleanup(extra_args, expected_cleanup, capsys) -> None:
    with patch("hpc_gui.cli.main.run_sftp_smoke", return_value=_smoke_all_pass()) as run_mock, patch(
        "hpc_gui.cli.main.CLISession.open", return_value=_FakeSmokeSession()
    ):
        assert run_cli(["--format", "json", "--host", "host", "doctor", "smoke", *extra_args]) == 0
    assert run_mock.call_args.kwargs["cleanup"] is expected_cleanup
    payload = json.loads(capsys.readouterr().out)
    assert payload["cleanup_requested"] is expected_cleanup


@pytest.mark.parametrize(
    ("fixture", "expected_exit"),
    [(_smoke_all_pass(), 0), (_smoke_fixture(_PARTIAL), 3)],
)
@pytest.mark.integration
@pytest.mark.semantic
@pytest.mark.artifact_dependent
def test_doctor_smoke_artifact_written(tmp_path, capsys, fixture, expected_exit) -> None:
    artifact = tmp_path / "smoke.json"
    with patch("hpc_gui.cli.main.run_sftp_smoke", return_value=fixture), patch(
        "hpc_gui.cli.main.CLISession.open", return_value=_FakeSmokeSession()
    ):
        assert run_cli(
            ["--format", "json", "--host", "host", "doctor", "smoke", "--artifact", str(artifact)]
        ) == expected_exit
    data = json.loads(artifact.read_text(encoding="utf-8"))
    assert data["schema"] == "sftp-smoke/1"
    assert data["status"] == fixture["status"]
    assert list(data["stages"]) == list(SMOKE_STAGES)


@pytest.mark.integration
@pytest.mark.semantic
@pytest.mark.artifact_dependent
def test_doctor_smoke_artifact_write_failure_returns_operation_failed(tmp_path, capsys) -> None:
    with patch("hpc_gui.cli.main.run_sftp_smoke", return_value=_smoke_all_pass()), patch(
        "hpc_gui.cli.main.CLISession.open", return_value=_FakeSmokeSession()
    ):
        result = run_cli(
            ["--host", "host", "doctor", "smoke", "--artifact", str(tmp_path / "missing" / "out.json")]
        )
    assert result == int(ExitCode.OPERATION_FAILED)
    assert "smoke artifact" in capsys.readouterr().err


@pytest.mark.contract
@pytest.mark.semantic
def test_doctor_smoke_text_and_json_expose_identical_stage_set(capsys) -> None:
    fixture = _smoke_fixture(_PARTIAL)
    with patch("hpc_gui.cli.main.run_sftp_smoke", return_value=fixture), patch(
        "hpc_gui.cli.main.CLISession.open", return_value=_FakeSmokeSession()
    ):
        assert run_cli(["--host", "host", "doctor", "smoke"]) == 3
    text_out = capsys.readouterr().out
    with patch("hpc_gui.cli.main.run_sftp_smoke", return_value=fixture), patch(
        "hpc_gui.cli.main.CLISession.open", return_value=_FakeSmokeSession()
    ):
        assert run_cli(["--format", "json", "--host", "host", "doctor", "smoke"]) == 3
    json_payload = json.loads(capsys.readouterr().out)
    assert list(json_payload["stages"]) == list(SMOKE_STAGES)
    for name in SMOKE_STAGES:
        assert f'"{name}"' in text_out


@pytest.mark.unit
@pytest.mark.semantic
def test_doctor_smoke_closes_session(capsys) -> None:
    closed: list[bool] = []

    class FakeSession:
        files = object()

        def close(self):
            closed.append(True)

    with patch("hpc_gui.cli.main.run_sftp_smoke", return_value=_smoke_all_pass()), patch(
        "hpc_gui.cli.main.CLISession.open", return_value=FakeSession()
    ):
        assert run_cli(["--format", "json", "--host", "host", "doctor", "smoke"]) == 0
    assert closed == [True]


@pytest.mark.integration
@pytest.mark.semantic
def test_doctor_smoke_never_leaks_sensitive_detail(capsys) -> None:
    secret = "TOP-SECRET-CREDENTIAL-9f4a"

    class LeakyUploadFiles(FakeFiles):
        def upload(self, local_path, remote_path, progress_cb=None):
            raise RuntimeError(f"upload denied: {secret}")

    class FakeSession:
        files = LeakyUploadFiles()

        def close(self):
            pass

    with patch("hpc_gui.cli.main.CLISession.open", return_value=FakeSession()):
        assert run_cli(["--host", "host", "doctor", "smoke"]) == 3
    captured = capsys.readouterr()
    assert secret not in captured.out + captured.err
    assert "upload failed" in captured.out
    assert "TOP-SECRET" not in captured.out + captured.err
