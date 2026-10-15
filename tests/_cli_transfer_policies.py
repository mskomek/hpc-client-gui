from __future__ import annotations
from _cli_test_support import (
    hashlib,
    json,
    Path,
    SimpleNamespace,
    patch,
    pytest,
    run_cli,
    RemoteEntry,
)

class FakeFiles:
    """In-memory transfer backend that records calls for if-exists policy tests."""

    def __init__(self, remote=None) -> None:
        self.remote = dict(remote or {})
        self.calls = {"upload": [], "download": [], "remove": [], "exists": [], "sha256": []}

    def exists(self, path):
        self.calls["exists"].append(path)
        return path in self.remote

    def is_dir(self, path):
        return path in self.remote and self.remote[path] is None

    def mkdir(self, path):
        self.remote.setdefault(path, None)

    def remove(self, path, recursive=False):
        self.calls["remove"].append(path)
        self.remote.pop(path, None)

    def listdir_entries(self, path):
        prefix = "" if path in ("", "/") else path.rstrip("/") + "/"
        return [
            type("Entry", (), {"name": key[len(prefix):], "path": key, "is_dir": value is None})()
            for key, value in self.remote.items()
            if key.startswith(prefix) and "/" not in key[len(prefix):]
        ]

    def sha256(self, path):
        self.calls["sha256"].append(path)
        return hashlib.sha256(self.remote.get(path, b"")).hexdigest()

    def upload(self, local_path, remote_path, progress_cb=None):
        self.calls["upload"].append(remote_path)
        self.remote[remote_path] = Path(local_path).read_bytes()

    def download(self, remote_path, local_path, progress_cb=None):
        self.calls["download"].append(remote_path)
        Path(local_path).write_bytes(self.remote[remote_path])


def _run_files(args, files) -> int:
    def fake_session(*_args):
        return SimpleNamespace(files=files, close=lambda: None)

    with patch("hpc_gui.cli.main.CLISession.open", side_effect=fake_session):
        return run_cli(args)


@pytest.mark.contract
@pytest.mark.semantic
@pytest.mark.regression
def test_files_ls_turkish_directory_json_keeps_type_and_name(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            assert path == "/uzak/klasör"
            return [
                type(
                    "Entry",
                    (),
                    {
                        "name": "klasör_yeni",
                        "path": "/uzak/klasör/klasör_yeni",
                        "is_dir": True,
                        "size": 0,
                        "mtime": 1,
                        "mode": 0o755,
                    },
                )()
            ]

    assert _run_files(["--format", "json", "--host", "host", "files", "ls", "/uzak/klasör"], FakeFiles()) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["type"] == "directory"
    assert payload[0]["name"] == "klasör_yeni"
    assert payload[0]["path"] == "/uzak/klasör/klasör_yeni"


@pytest.mark.contract
@pytest.mark.semantic
@pytest.mark.regression
def test_files_ls_turkish_text_keeps_name_and_type_keys(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            assert path == "/uzak/klasör"
            return [
                type(
                    "Entry",
                    (),
                    {
                        "name": "dosya_ç.txt",
                        "path": "/uzak/klasör/dosya_ç.txt",
                        "is_dir": False,
                        "size": 3,
                        "mtime": 1,
                        "mode": 0o644,
                    },
                )(),
                type(
                    "Entry",
                    (),
                    {
                        "name": "klasör_yeni",
                        "path": "/uzak/klasör/klasör_yeni",
                        "is_dir": True,
                        "size": 0,
                        "mtime": 1,
                        "mode": 0o755,
                    },
                )(),
            ]

    assert _run_files(["--host", "host", "files", "ls", "/uzak/klasör"], FakeFiles()) == 0
    out = capsys.readouterr().out
    assert "dosya_ç.txt" in out
    assert "klasör_yeni" in out
    assert "'type': 'file'" in out
    assert "'type': 'directory'" in out


@pytest.mark.contract
@pytest.mark.semantic
@pytest.mark.regression
def test_files_stat_turkish_json_six_keys_and_name_preserved(capsys) -> None:
    class FakeFiles:
        def stat_entry(self, path):
            assert path == "/uzak/klasör/ş_veri.txt"
            return RemoteEntry(
                name="ş_veri.txt",
                path="/uzak/klasör/ş_veri.txt",
                is_dir=False,
                size=9,
                mtime=5,
                mode=0o644,
            )

    assert _run_files(["--format", "json", "--host", "host", "files", "stat", "/uzak/klasör/ş_veri.txt"], FakeFiles()) == 0
    payload = json.loads(capsys.readouterr().out)
    assert set(payload) == {"name", "path", "type", "size", "mtime", "mode"}
    assert payload["name"] == "ş_veri.txt"
    assert payload["path"] == "/uzak/klasör/ş_veri.txt"
    assert payload["type"] == "file"


@pytest.mark.contract
@pytest.mark.semantic
@pytest.mark.regression
def test_files_stat_turkish_text_keeps_name(capsys) -> None:
    class FakeFiles:
        def stat_entry(self, path):
            return RemoteEntry(
                name="ş_veri.txt",
                path="/uzak/klasör/ş_veri.txt",
                is_dir=False,
                size=9,
                mtime=5,
                mode=0o644,
            )

    assert _run_files(["--host", "host", "files", "stat", "/uzak/klasör/ş_veri.txt"], FakeFiles()) == 0
    out = capsys.readouterr().out
    assert "ş_veri.txt" in out
    assert "/uzak/klasör/ş_veri.txt" in out


@pytest.mark.contract
@pytest.mark.semantic
@pytest.mark.regression
def test_files_json_not_found_turkish_detail_parity(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            raise FileNotFoundError("bulunamadı")

    assert _run_files(["--format", "json", "--host", "host", "files", "ls", "/eksik"], FakeFiles()) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["message"].startswith("Not found: ")
    assert "bulunamadı" in payload["error"]["message"]
    assert payload["error"]["exit_code"] == 1


@pytest.mark.contract
@pytest.mark.semantic
def test_files_json_permission_denied_parity(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            raise PermissionError("erişim engellendi")

    assert _run_files(["--format", "json", "--host", "host", "files", "ls", "/kilitli"], FakeFiles()) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["message"].startswith("Permission denied: ")
    assert "erişim engellendi" in payload["error"]["message"]
    assert payload["error"]["exit_code"] == 1


@pytest.mark.contract
@pytest.mark.semantic
def test_files_json_not_a_directory_parity(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            raise NotADirectoryError(f"{path} bir dizin değil")

    assert _run_files(["--format", "json", "--host", "host", "files", "ls", "/dosya_ç.txt"], FakeFiles()) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["message"].startswith("Not found: ")
    assert "dosya_ç.txt" in payload["error"]["message"]
    assert payload["error"]["exit_code"] == 1


@pytest.mark.contract
@pytest.mark.semantic
def test_files_json_timeout_parity(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            raise TimeoutError("işlem zaman aşımı")

    assert _run_files(["--format", "json", "--host", "host", "files", "ls", "/"], FakeFiles()) == 124
    payload = json.loads(capsys.readouterr().out)
    assert "Operation timed out" in payload["error"]["message"]
    assert payload["error"]["exit_code"] == 124


@pytest.mark.contract
@pytest.mark.semantic
def test_files_ls_empty_directory_text_prints_nothing(capsys) -> None:
    class FakeFiles:
        def listdir_entries(self, path):
            return []

    assert _run_files(["--host", "host", "files", "ls", "/boş"], FakeFiles()) == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


@pytest.mark.integration
@pytest.mark.semantic
def test_upload_skip_existing_remote_is_noop(capsys, tmp_path: Path) -> None:
    source = tmp_path / "data.txt"
    source.write_bytes(b"new")
    files = FakeFiles(remote={"/remote/data.txt": b"old"})
    assert _run_files(["--format", "json", "--host", "host", "files", "upload", "--if-exists", "skip", str(source), "/remote/data.txt"], files) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["policy"] == "skip"
    assert payload["files"] == 0
    assert payload["skipped"] == 1
    assert files.calls["upload"] == []
    assert files.remote["/remote/data.txt"] == b"old"


@pytest.mark.integration
@pytest.mark.semantic
def test_download_skip_existing_local_is_noop(capsys, tmp_path: Path) -> None:
    target = tmp_path / "data.txt"
    target.write_bytes(b"local")
    files = FakeFiles(remote={"/remote/data.txt": b"remote"})
    assert _run_files(["--format", "json", "--host", "host", "files", "download", "--if-exists", "skip", "/remote/data.txt", str(target)], files) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["policy"] == "skip"
    assert payload["files"] == 0
    assert payload["skipped"] == 1
    assert files.calls["download"] == []
    assert target.read_bytes() == b"local"


@pytest.mark.integration
@pytest.mark.semantic
def test_upload_rename_uses_unique_destination(capsys, tmp_path: Path) -> None:
    source = tmp_path / "data.txt"
    source.write_bytes(b"new")
    files = FakeFiles(remote={"/remote/data.txt": b"old"})
    assert _run_files(["--format", "json", "--host", "host", "files", "upload", "--if-exists", "rename", str(source), "/remote/data.txt"], files) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["policy"] == "rename"
    assert payload["files"] == 1
    assert payload["renames"] == [{"from": "/remote/data.txt", "to": "/remote/data (1).txt"}]
    assert files.calls["upload"] == ["/remote/data (1).txt"]
    assert files.remote["/remote/data.txt"] == b"old"
    assert files.remote["/remote/data (1).txt"] == b"new"


@pytest.mark.integration
@pytest.mark.semantic
def test_upload_rename_second_collision_uses_two(capsys, tmp_path: Path) -> None:
    source = tmp_path / "data.txt"
    source.write_bytes(b"new")
    files = FakeFiles(remote={"/remote/data.txt": b"old", "/remote/data (1).txt": b"other"})
    assert _run_files(["--format", "json", "--host", "host", "files", "upload", "--if-exists", "rename", str(source), "/remote/data.txt"], files) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["renames"] == [{"from": "/remote/data.txt", "to": "/remote/data (2).txt"}]
    assert files.calls["upload"] == ["/remote/data (2).txt"]


@pytest.mark.integration
@pytest.mark.semantic
def test_download_rename_never_overwrites_local(capsys, tmp_path: Path) -> None:
    target = tmp_path / "data.txt"
    target.write_bytes(b"local")
    files = FakeFiles(remote={"/remote/data.txt": b"remote"})
    assert _run_files(["--format", "json", "--host", "host", "files", "download", "--if-exists", "rename", "/remote/data.txt", str(target)], files) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["renames"] == [{"from": str(target), "to": str(tmp_path / "data (1).txt")}]
    assert target.read_bytes() == b"local"
    assert (tmp_path / "data (1).txt").read_bytes() == b"remote"
    assert files.calls["download"] == ["/remote/data.txt"]


@pytest.mark.integration
@pytest.mark.semantic
def test_upload_overwrite_removes_then_uploads(capsys, tmp_path: Path) -> None:
    source = tmp_path / "data.txt"
    source.write_bytes(b"new")
    files = FakeFiles(remote={"/remote/data.txt": b"old"})
    assert _run_files(["--format", "json", "--host", "host", "files", "upload", "--if-exists", "overwrite", str(source), "/remote/data.txt"], files) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["policy"] == "overwrite"
    assert payload["files"] == 1
    assert files.calls["remove"] == ["/remote/data.txt"]
    assert files.calls["upload"] == ["/remote/data.txt"]
    assert files.remote["/remote/data.txt"] == b"new"


@pytest.mark.integration
@pytest.mark.semantic
def test_upload_resume_no_exists_check_single_call(capsys, tmp_path: Path) -> None:
    source = tmp_path / "data.txt"
    source.write_bytes(b"new")
    files = FakeFiles(remote={"/remote/data.txt": b"old"})
    assert _run_files(["--format", "json", "--host", "host", "files", "upload", "--if-exists", "resume", str(source), "/remote/data.txt"], files) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["policy"] == "resume"
    assert files.calls["exists"] == []
    assert files.calls["upload"] == ["/remote/data.txt"]
    assert files.remote["/remote/data.txt"] == b"new"


@pytest.mark.integration
@pytest.mark.semantic
def test_upload_skip_with_verify_does_not_verify(capsys, tmp_path: Path) -> None:
    source = tmp_path / "data.txt"
    source.write_bytes(b"new")
    files = FakeFiles(remote={"/remote/data.txt": b"old"})
    assert _run_files(["--format", "json", "--host", "host", "files", "upload", "--if-exists", "skip", "--verify", str(source), "/remote/data.txt"], files) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["skipped"] == 1
    assert files.calls["upload"] == []
    assert files.calls["sha256"] == []


@pytest.mark.integration
@pytest.mark.semantic
def test_upload_rename_verify_checks_effective_destination(capsys, tmp_path: Path) -> None:
    source = tmp_path / "data.txt"
    source.write_bytes(b"payload")
    files = FakeFiles(remote={"/remote/data.txt": b"old"})
    assert _run_files(["--format", "json", "--host", "host", "files", "upload", "--if-exists", "rename", "--verify", str(source), "/remote/data.txt"], files) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["renames"] == [{"from": "/remote/data.txt", "to": "/remote/data (1).txt"}]
    assert files.calls["sha256"] == ["/remote/data (1).txt"]


@pytest.mark.contract
@pytest.mark.semantic
def test_upload_skip_text_matches_json_noop(capsys, tmp_path: Path) -> None:
    source = tmp_path / "data.txt"
    source.write_bytes(b"new")
    assert _run_files(["--host", "host", "files", "upload", "--if-exists", "skip", str(source), "/remote/data.txt"], FakeFiles(remote={"/remote/data.txt": b"old"})) == 0
    text = capsys.readouterr().out
    assert "operation: upload" in text
    assert "policy: skip" in text
    assert "files: 0" in text
    assert "skipped: 1" in text
    assert "verified: False" in text


@pytest.mark.integration
@pytest.mark.semantic
def test_upload_default_if_exists_is_overwrite(capsys, tmp_path: Path) -> None:
    source = tmp_path / "data.txt"
    source.write_bytes(b"new")
    files = FakeFiles(remote={"/remote/data.txt": b"old"})
    assert _run_files(["--format", "json", "--host", "host", "files", "upload", str(source), "/remote/data.txt"], files) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["policy"] == "overwrite"
    assert files.calls["remove"] == ["/remote/data.txt"]
    assert files.calls["upload"] == ["/remote/data.txt"]


@pytest.mark.integration
@pytest.mark.semantic
def test_upload_recursive_skip_applies_per_file(capsys, tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "a.txt").write_bytes(b"a")
    (src_dir / "b.txt").write_bytes(b"b")
    files = FakeFiles(remote={"/remote/src/a.txt": b"old-a"})
    assert _run_files(["--format", "json", "--host", "host", "files", "upload", "--recursive", "--if-exists", "skip", str(src_dir), "/remote"], files) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["files"] == 1
    assert payload["skipped"] == 1
    assert sorted(files.calls["upload"]) == ["/remote/src/b.txt"]
