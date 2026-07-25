from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from truba_gui.cli.main import run_cli


def test_version_json(capsys) -> None:
    assert run_cli(["--format", "json", "version"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["name"] == "truba-client-gui"
    assert payload["version"]


def test_profile_list_does_not_print_secrets(capsys) -> None:
    profiles = [
        {
            "name": "test",
            "host": "cluster.example",
            "username": "user",
            "password": "should-not-print",
            "password_dpapi": "encrypted-secret",
        }
    ]
    with patch("truba_gui.cli.main.load_profiles", return_value=profiles):
        assert run_cli(["--format", "json", "profile", "show", "test"]) == 0
    output = capsys.readouterr().out
    assert "cluster.example" in output
    assert "should-not-print" not in output
    assert "encrypted-secret" not in output


def test_doctor_environment_json(capsys, tmp_path: Path) -> None:
    with patch("truba_gui.cli.main.app_data_dir", return_value=tmp_path), patch(
        "truba_gui.cli.main.load_profiles", return_value=[]
    ):
        assert run_cli(["--format", "json", "doctor", "environment"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "PASS"
    assert payload["profiles"] == 0


def test_files_ls_uses_shared_cli_session(capsys) -> None:
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
                )()
            ]

    class FakeSession:
        files = FakeFiles()

        def close(self):
            pass

    with patch("truba_gui.cli.main.CLISession.open", return_value=FakeSession()):
        assert run_cli(["--format", "json", "--host", "host", "files", "ls", "/uzak/klasör"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["name"] == "dosya_ç.txt"
